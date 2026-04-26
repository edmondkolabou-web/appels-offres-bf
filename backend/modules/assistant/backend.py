"""
NetSync Gov — Assistant IA
Endpoint proxy vers Claude API avec contexte AOs BF.
3 modes : questions AO, analyse AO, aide rédaction.
"""
import logging
import os
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_db
from backend.models import Abonne
from backend.security import get_current_abonne

logger = logging.getLogger("netsync.assistant")

router = APIRouter(prefix="/api/v1/assistant", tags=["Assistant IA"])


class ChatMessage(BaseModel):
    role: str  # "user" ou "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    mode: str = "general"  # general, analyse, redaction
    ao_id: Optional[str] = None
    history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    reply: str
    mode: str
    tokens_used: int = 0


def _get_ao_context(ao_id: str, db: Session) -> str:
    """Récupère le contexte d'un AO pour enrichir le prompt."""
    ao = db.execute(
        text("""
            SELECT titre, reference, autorite_contractante, secteur,
                   type_procedure, statut, date_publication, date_cloture,
                   montant_estime, description, source
            FROM appels_offres WHERE id = :id
        """),
        {"id": ao_id}
    ).fetchone()
    if not ao:
        return ""
    
    ctx = f"""
## Appel d'offres sélectionné
- **Titre** : {ao.titre}
- **Référence** : {ao.reference or 'Non précisée'}
- **Autorité contractante** : {ao.autorite_contractante or 'Non précisée'}
- **Secteur** : {ao.secteur or 'Non précisé'}
- **Type de procédure** : {ao.type_procedure or 'Non précisé'}
- **Statut** : {ao.statut}
- **Date publication** : {ao.date_publication}
- **Date clôture** : {ao.date_cloture or 'Non précisée'}
- **Montant estimé** : {f'{ao.montant_estime:,} FCFA' if ao.montant_estime else 'Non précisé'}
- **Source** : {ao.source}
- **Description** : {ao.description or 'Voir le dossier officiel'}
"""
    return ctx


def _get_stats_context(db: Session) -> str:
    """Récupère des stats générales pour le contexte."""
    stats = db.execute(text("""
        SELECT 
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE statut = 'ouvert') AS ouverts,
            COUNT(*) FILTER (WHERE date_publication >= CURRENT_DATE - INTERVAL '30 days') AS ce_mois
        FROM appels_offres
    """)).fetchone()
    return f"Base NetSync Gov : {stats.total} AOs indexés, {stats.ouverts} ouverts, {stats.ce_mois} publiés ce mois."


SYSTEM_PROMPT = """Tu es l'Assistant IA de NetSync Gov, la plateforme de veille des appels d'offres publics du Burkina Faso.

## Ton rôle
Tu aides les PME, consultants et bureaux d'études burkinabè à :
1. Comprendre les appels d'offres (procédures, documents requis, délais)
2. Analyser un AO spécifique (pertinence, risques, recommandations)
3. Rédiger des documents (offre technique, lettre de soumission, note méthodologique)

## Ton expertise
- Marchés publics du Burkina Faso (Code des marchés publics, DGCMEF, ARCOP)
- Procédures : AO ouvert, AO restreint, demande de prix (DPX), AMI, RFP
- Pièces administratives : ASF (DGI), CNSS, AJE, RCCM, IFU
- Plateforme SECOP pour les attestations en ligne
- Sources : Quotidien des Marchés Publics DGCMEF, CCI-BF, UNDP, Banque Mondiale

## Règles
- Réponds toujours en français
- Sois précis, concret et actionnable
- Cite les articles du Code des marchés publics quand pertinent
- Si tu ne sais pas, dis-le honnêtement
- Propose toujours une prochaine action concrète
- Utilise le formatage Markdown (gras, listes, titres)
- Reste concis — 200-400 mots maximum sauf pour la rédaction
"""

MODE_PROMPTS = {
    "general": "L'utilisateur pose une question générale sur les marchés publics au Burkina Faso ou sur la plateforme NetSync Gov.",
    "analyse": """L'utilisateur demande une analyse d'un appel d'offres spécifique. Tu dois :
1. Résumer l'AO en 3-4 phrases
2. Évaluer la pertinence (secteur, montant, complexité)
3. Identifier les risques et les points d'attention
4. Lister les pièces administratives requises
5. Recommander une stratégie go/no-go
6. Estimer le temps de préparation du dossier""",
    "redaction": """L'utilisateur demande de l'aide pour rédiger un document de soumission. Tu dois :
1. Demander les informations manquantes si nécessaire
2. Produire un document professionnel et structuré
3. Adapter au contexte burkinabè (formulations, références réglementaires)
4. Inclure des [À COMPLÉTER] pour les données spécifiques
5. Suivre la structure standard des offres BF"""
}


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    abonne: Abonne = Depends(get_current_abonne),
    db: Session = Depends(get_db),
):
    """
    Endpoint principal de l'assistant IA.
    Utilise Claude API avec contexte AOs BF.
    Réservé aux abonnés Pro.
    """
    if not abonne.est_pro:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="L'assistant IA est réservé aux abonnés Pro. Passez au plan Pro pour y accéder."
        )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service IA temporairement indisponible. Veuillez réessayer plus tard."
        )

    # Construire le contexte
    context_parts = [SYSTEM_PROMPT]
    context_parts.append(f"\n## Mode actif : {body.mode}")
    context_parts.append(MODE_PROMPTS.get(body.mode, MODE_PROMPTS["general"]))
    context_parts.append(f"\n## Contexte\n{_get_stats_context(db)}")
    context_parts.append(f"Date du jour : {date.today().isoformat()}")

    if body.ao_id:
        ao_ctx = _get_ao_context(body.ao_id, db)
        if ao_ctx:
            context_parts.append(ao_ctx)

    # Abonné info
    context_parts.append(f"\n## Utilisateur\nNom : {abonne.prenom} {abonne.nom}\nEntreprise : {abonne.entreprise or 'Non précisée'}\nPlan : {abonne.plan}")

    system_prompt = "\n".join(context_parts)

    # Construire les messages
    messages = []
    for msg in body.history[-10:]:  # Garder les 10 derniers messages
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": body.message})

    # Appel Claude API
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        )
        
        reply = response.content[0].text
        tokens = response.usage.output_tokens

        logger.info(f"Assistant IA: {abonne.email} mode={body.mode} tokens={tokens}")

        return ChatResponse(
            reply=reply,
            mode=body.mode,
            tokens_used=tokens,
        )

    except Exception as e:
        logger.error(f"Erreur Claude API: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erreur de communication avec le service IA. Veuillez réessayer."
        )


@router.get("/suggestions")
def get_suggestions(
    abonne: Abonne = Depends(get_current_abonne),
    db: Session = Depends(get_db),
):
    """Retourne des suggestions de questions contextuelles."""
    suggestions = [
        {"icon": "🔍", "text": "Quels AOs correspondent à mon profil ?", "mode": "general"},
        {"icon": "📋", "text": "Quelles pièces administratives dois-je préparer pour un AO ouvert ?", "mode": "general"},
        {"icon": "⏰", "text": "Quels sont les délais typiques pour répondre à un AO au Burkina ?", "mode": "general"},
        {"icon": "💰", "text": "Comment estimer le montant de mon offre financière ?", "mode": "general"},
        {"icon": "📝", "text": "Aide-moi à rédiger une offre technique", "mode": "redaction"},
        {"icon": "🏛️", "text": "Explique-moi la procédure d'AO restreint au Burkina Faso", "mode": "general"},
    ]

    # Ajouter des suggestions contextuelles basées sur les AOs urgents
    urgents = db.execute(text("""
        SELECT id, titre, secteur FROM appels_offres
        WHERE statut = 'ouvert' AND date_cloture <= CURRENT_DATE + INTERVAL '7 days'
        AND date_cloture >= CURRENT_DATE
        ORDER BY date_cloture ASC LIMIT 2
    """)).fetchall()

    for ao in urgents:
        suggestions.insert(0, {
            "icon": "⚡",
            "text": f"Analyse cet AO urgent : {ao.titre[:60]}...",
            "mode": "analyse",
            "ao_id": str(ao.id),
        })

    return {"suggestions": suggestions[:8]}
