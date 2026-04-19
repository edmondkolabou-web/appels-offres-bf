"""
NetSync Gov Candidature — Backend FastAPI
Gestion complète des candidatures aux marchés publics.
"""
import os
import uuid
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.security import get_current_abonne, require_pro
from backend.models import Abonne

logger = logging.getLogger("netsync.candidatures")

router_candidatures = APIRouter(prefix="/api/v1/candidatures", tags=["Candidatures"])
router_pieces       = APIRouter(prefix="/api/v1/pieces",       tags=["Pièces"])
router_taches       = APIRouter(prefix="/api/v1/taches",       tags=["Tâches"])
router_offres       = APIRouter(prefix="/api/v1/offres-ia",    tags=["Offres IA"])

# ── Schémas Pydantic ──────────────────────────────────────────────────────────

class CandidatureCreate(BaseModel):
    ao_id: uuid.UUID
    notes: Optional[str] = None

class CandidatureUpdate(BaseModel):
    statut: Optional[str] = None
    notes: Optional[str] = None
    montant_offre: Optional[int] = None
    score_go_nogo: Optional[int] = Field(None, ge=0, le=100)
    responsable_id: Optional[uuid.UUID] = None
    date_depot: Optional[date] = None

class CandidatureOut(BaseModel):
    id: uuid.UUID
    ao_id: uuid.UUID
    statut: str
    notes: Optional[str]
    montant_offre: Optional[int]
    score_go_nogo: Optional[int]
    date_depot: Optional[date]
    avancement: Optional[int] = None
    ao_titre: Optional[str] = None
    ao_date_cloture: Optional[date] = None
    ao_est_urgent: Optional[bool] = None

class PieceCreate(BaseModel):
    type_piece: str
    date_emission: Optional[date] = None
    date_expiration: Optional[date] = None
    notes: Optional[str] = None

class TacheCreate(BaseModel):
    titre: str
    description: Optional[str] = None
    type_tache: Optional[str] = "autre"
    priorite: Optional[str] = "normale"
    date_echeance: Optional[date] = None
    assignee_id: Optional[uuid.UUID] = None

class TacheUpdate(BaseModel):
    statut: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    date_echeance: Optional[date] = None

class OffreGenererRequest(BaseModel):
    type_offre: str = "technique"
    entreprise_nom: Optional[str] = None
    entreprise_secteur: Optional[str] = None
    references: Optional[str] = None
    effectifs: Optional[str] = None
    informations_complementaires: Optional[str] = None

# ── Logique checklist ─────────────────────────────────────────────────────────

PIECES_PAR_TYPE = {
    "ouvert": [
        {"type": "asf",                "obligatoire": True,  "validite_jours": 90,  "label": "Attestation de Situation Fiscale (ASF)"},
        {"type": "cnss",               "obligatoire": True,  "validite_jours": 90,  "label": "Attestation CNSS"},
        {"type": "aje",                "obligatoire": True,  "validite_jours": 365, "label": "Attestation de Jouissance d'Existence"},
        {"type": "rccm",               "obligatoire": True,  "validite_jours": None,"label": "Registre du Commerce (RCCM)"},
        {"type": "ifu",                "obligatoire": True,  "validite_jours": None,"label": "Identifiant Fiscal Unique (IFU)"},
        {"type": "statuts",            "obligatoire": True,  "validite_jours": None,"label": "Statuts de la société"},
        {"type": "reference_marche",   "obligatoire": True,  "validite_jours": None,"label": "Références de marchés similaires"},
        {"type": "attestation_bancaire","obligatoire": False, "validite_jours": 30,  "label": "Attestation bancaire"},
    ],
    "restreint": [
        {"type": "asf",              "obligatoire": True,  "validite_jours": 90,  "label": "Attestation de Situation Fiscale (ASF)"},
        {"type": "cnss",             "obligatoire": True,  "validite_jours": 90,  "label": "Attestation CNSS"},
        {"type": "aje",              "obligatoire": True,  "validite_jours": 365, "label": "Attestation de Jouissance d'Existence"},
        {"type": "rccm",             "obligatoire": True,  "validite_jours": None,"label": "RCCM"},
        {"type": "ifu",              "obligatoire": True,  "validite_jours": None,"label": "IFU"},
        {"type": "statuts",          "obligatoire": True,  "validite_jours": None,"label": "Statuts"},
        {"type": "reference_marche", "obligatoire": True,  "validite_jours": None,"label": "Références marchés"},
    ],
    "dpx": [
        {"type": "asf",  "obligatoire": True,  "validite_jours": 90,  "label": "Attestation de Situation Fiscale (ASF)"},
        {"type": "cnss", "obligatoire": True,  "validite_jours": 90,  "label": "Attestation CNSS"},
        {"type": "ifu",  "obligatoire": True,  "validite_jours": None,"label": "IFU"},
    ],
    "ami": [
        {"type": "cv",               "obligatoire": True,  "validite_jours": None,"label": "CV du consultant principal"},
        {"type": "reference_marche", "obligatoire": True,  "validite_jours": None,"label": "Références similaires"},
        {"type": "rccm",             "obligatoire": False, "validite_jours": None,"label": "RCCM (si structure)"},
    ],
    "rfp": [
        {"type": "cv",               "obligatoire": True,  "validite_jours": None,"label": "CVs des experts clés"},
        {"type": "reference_marche", "obligatoire": True,  "validite_jours": None,"label": "Références similaires"},
        {"type": "rccm",             "obligatoire": True,  "validite_jours": None,"label": "RCCM"},
        {"type": "statuts",          "obligatoire": True,  "validite_jours": None,"label": "Statuts"},
    ],
}


def get_checklist(type_procedure: str) -> list:
    """Retourne la checklist de pièces pour un type de procédure."""
    return PIECES_PAR_TYPE.get(type_procedure.lower(), PIECES_PAR_TYPE["ouvert"])


def calculer_avancement(candidature_id: str, db: Session) -> dict:
    """Calcule le score de complétude d'un dossier de candidature."""
    # Récupérer les infos de la candidature
    cand = db.execute(
        text("""
            SELECT c.*, a.type_procedure
            FROM candidatures c
            JOIN appels_offres a ON a.id = c.ao_id
            WHERE c.id = :id
        """),
        {"id": candidature_id}
    ).fetchone()

    if not cand:
        return {"score_global": 0}

    checklist = get_checklist(cand.type_procedure or "ouvert")
    pieces_obligatoires = [p for p in checklist if p["obligatoire"]]

    # Pièces uploadées et valides
    pieces_valides = db.execute(
        text("""
            SELECT type_piece FROM pieces_administratives
            WHERE abonne_id = :abonne_id
              AND est_valide = true
        """),
        {"abonne_id": str(cand.abonne_id)}
    ).fetchall()
    types_valides = {p.type_piece for p in pieces_valides}

    pieces_ok = sum(1 for p in pieces_obligatoires if p["type"] in types_valides)
    pieces_expirees_count = db.execute(
        text("""
            SELECT COUNT(*) FROM pieces_administratives
            WHERE abonne_id = :abonne_id
              AND date_expiration IS NOT NULL
              AND date_expiration < CURRENT_DATE
        """),
        {"abonne_id": str(cand.abonne_id)}
    ).scalar()

    # Offre technique
    offre_technique = db.execute(
        text("""
            SELECT valide_par_user FROM offres_generees
            WHERE candidature_id = :id AND type_offre = 'technique'
            ORDER BY created_at DESC LIMIT 1
        """),
        {"id": candidature_id}
    ).fetchone()

    # Tâches
    taches = db.execute(
        text("SELECT statut FROM taches_candidature WHERE candidature_id = :id"),
        {"id": candidature_id}
    ).fetchall()
    taches_faites = sum(1 for t in taches if t.statut == "fait")

    # Score pondéré
    score_pieces    = (pieces_ok / max(len(pieces_obligatoires), 1)) * 50
    score_technique = 25 if offre_technique and offre_technique.valide_par_user else (
                       12 if offre_technique else 0)
    score_taches    = (taches_faites / max(len(taches), 1)) * 10 if taches else 0
    score_global    = int(score_pieces + score_technique + score_taches)

    blocages = []
    if pieces_expirees_count:
        blocages.append(f"{pieces_expirees_count} pièce(s) expirée(s)")
    if not offre_technique:
        blocages.append("Offre technique manquante")
    for p in pieces_obligatoires:
        if p["type"] not in types_valides:
            blocages.append(f"{p['label']} manquante")

    return {
        "score_global":     score_global,
        "pieces_ok":        pieces_ok,
        "pieces_total":     len(pieces_obligatoires),
        "pieces_expirees":  pieces_expirees_count,
        "offre_technique":  "validee" if (offre_technique and offre_technique.valide_par_user)
                            else "generee" if offre_technique else "manquante",
        "taches_faites":    taches_faites,
        "taches_total":     len(taches),
        "pret_depot":       score_global >= 80 and not blocages,
        "blocages":         blocages[:5],
    }


# ── Endpoints Candidatures ────────────────────────────────────────────────────

@router_candidatures.get("")
def list_candidatures(
    statut: Optional[str] = None,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Liste toutes les candidatures de l'abonné, avec infos AO."""
    query = """
        SELECT c.id, c.ao_id, c.statut, c.notes, c.montant_offre,
               c.score_go_nogo, c.date_depot, c.created_at,
               a.titre AS ao_titre, a.date_cloture AS ao_date_cloture,
               a.est_urgent AS ao_est_urgent, a.secteur AS ao_secteur
        FROM candidatures c
        JOIN appels_offres a ON a.id = c.ao_id
        WHERE c.abonne_id = :abonne_id
    """
    params: dict = {"abonne_id": str(abonne.id)}
    if statut:
        query += " AND c.statut = :statut"
        params["statut"] = statut
    query += " ORDER BY c.updated_at DESC"

    rows = db.execute(text(query), params).fetchall()
    result = []
    for r in rows:
        item = dict(r._mapping)
        item["avancement"] = calculer_avancement(str(r.id), db)["score_global"]
        result.append(item)
    return result


@router_candidatures.post("", status_code=status.HTTP_201_CREATED)
def create_candidature(
    body: CandidatureCreate,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Crée une candidature sur un AO."""
    # Vérifier que l'AO existe
    ao = db.execute(
        text("SELECT id, type_procedure FROM appels_offres WHERE id = :id"),
        {"id": str(body.ao_id)}
    ).fetchone()
    if not ao:
        raise HTTPException(status_code=404, detail="AO introuvable")

    # Vérifier pas de doublon
    existing = db.execute(
        text("SELECT id FROM candidatures WHERE ao_id = :ao_id AND abonne_id = :abonne_id"),
        {"ao_id": str(body.ao_id), "abonne_id": str(abonne.id)}
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Candidature déjà créée pour cet AO")

    cand_id = uuid.uuid4()
    db.execute(
        text("""
            INSERT INTO candidatures (id, ao_id, abonne_id, statut, notes)
            VALUES (:id, :ao_id, :abonne_id, 'en_veille', :notes)
        """),
        {"id": str(cand_id), "ao_id": str(body.ao_id),
         "abonne_id": str(abonne.id), "notes": body.notes}
    )

    # Générer les tâches par défaut selon type de procédure
    checklist = get_checklist(ao.type_procedure or "ouvert")
    for piece in checklist:
        if piece["obligatoire"]:
            db.execute(
                text("""
                    INSERT INTO taches_candidature
                    (id, candidature_id, titre, type_tache, priorite)
                    VALUES (:id, :cand_id, :titre, 'piece_admin', 'haute')
                """),
                {"id": str(uuid.uuid4()), "cand_id": str(cand_id),
                 "titre": f"Préparer : {piece['label']}"}
            )

    db.commit()
    logger.info(f"Candidature créée : {cand_id} (AO={body.ao_id}, abonné={abonne.id})")
    return {"id": str(cand_id), "statut": "en_veille", "message": "Candidature créée"}


@router_candidatures.get("/{candidature_id}")
def get_candidature(
    candidature_id: str,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Détail complet d'une candidature."""
    cand = db.execute(
        text("""
            SELECT c.*, a.titre AS ao_titre, a.date_cloture, a.type_procedure,
                   a.secteur, a.autorite_contractante, a.est_urgent
            FROM candidatures c
            JOIN appels_offres a ON a.id = c.ao_id
            WHERE c.id = :id AND c.abonne_id = :abonne_id
        """),
        {"id": candidature_id, "abonne_id": str(abonne.id)}
    ).fetchone()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidature introuvable")

    taches = db.execute(
        text("SELECT * FROM taches_candidature WHERE candidature_id = :id ORDER BY priorite"),
        {"id": candidature_id}
    ).fetchall()

    offres = db.execute(
        text("SELECT id, type_offre, version, valide_par_user, created_at FROM offres_generees WHERE candidature_id = :id ORDER BY created_at DESC"),
        {"id": candidature_id}
    ).fetchall()

    avancement = calculer_avancement(candidature_id, db)
    checklist  = get_checklist(cand.type_procedure or "ouvert")

    return {
        "candidature": dict(cand._mapping),
        "avancement":  avancement,
        "checklist":   checklist,
        "taches":      [dict(t._mapping) for t in taches],
        "offres":      [dict(o._mapping) for o in offres],
    }


@router_candidatures.put("/{candidature_id}")
def update_candidature(
    candidature_id: str,
    body: CandidatureUpdate,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Met à jour une candidature."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="Aucune mise à jour fournie")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"]        = candidature_id
    updates["abonne_id"] = str(abonne.id)
    updates["updated_at"] = "now()"

    db.execute(
        text(f"UPDATE candidatures SET {set_clause}, updated_at = now() WHERE id = :id AND abonne_id = :abonne_id"),
        updates
    )
    db.commit()
    return {"message": "Candidature mise à jour"}


@router_candidatures.post("/{candidature_id}/checklist")
def get_checklist_auto(
    candidature_id: str,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Retourne la checklist de pièces adaptée au type de procédure de l'AO."""
    row = db.execute(
        text("""
            SELECT a.type_procedure FROM candidatures c
            JOIN appels_offres a ON a.id = c.ao_id
            WHERE c.id = :id AND c.abonne_id = :abonne_id
        """),
        {"id": candidature_id, "abonne_id": str(abonne.id)}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    return {"checklist": get_checklist(row.type_procedure or "ouvert")}


# ── Endpoints Pièces ──────────────────────────────────────────────────────────

@router_pieces.get("")
def list_pieces(
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Liste toutes les pièces administratives de l'abonné."""
    pieces = db.execute(
        text("""
            SELECT *, (date_expiration IS NOT NULL AND date_expiration < CURRENT_DATE) AS expiree
            FROM pieces_administratives
            WHERE abonne_id = :abonne_id
            ORDER BY type_piece, date_expiration
        """),
        {"abonne_id": str(abonne.id)}
    ).fetchall()
    return [dict(p._mapping) for p in pieces]


@router_pieces.get("/expiration")
def pieces_expirant_bientot(
    jours: int = 30,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Pièces qui expirent dans les N prochains jours."""
    date_limite = date.today() + timedelta(days=jours)
    pieces = db.execute(
        text("""
            SELECT * FROM pieces_administratives
            WHERE abonne_id = :abonne_id
              AND date_expiration IS NOT NULL
              AND date_expiration BETWEEN CURRENT_DATE AND :limite
            ORDER BY date_expiration
        """),
        {"abonne_id": str(abonne.id), "limite": date_limite}
    ).fetchall()
    return [dict(p._mapping) for p in pieces]


@router_pieces.post("", status_code=status.HTTP_201_CREATED)
async def upload_piece(
    type_piece: str = Form(...),
    date_emission: Optional[str] = Form(None),
    date_expiration: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    fichier: Optional[UploadFile] = File(None),
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Upload une pièce administrative."""
    url_stockage = None
    nom_fichier  = None
    taille       = None

    if fichier:
        # Vérification type de fichier
        allowed = {"application/pdf", "image/jpeg", "image/png",
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        if fichier.content_type not in allowed:
            raise HTTPException(status_code=422, detail="Format non supporté (PDF, JPG, PNG, DOCX)")

        # Lecture du fichier
        content = await fichier.read()
        taille = len(content)
        if taille > 10 * 1024 * 1024:  # 10 MB
            raise HTTPException(status_code=422, detail="Fichier trop volumineux (max 10 MB)")

        nom_fichier = fichier.filename
        # En production : upload vers Backblaze B2 ou S3
        # url_stockage = await upload_to_storage(content, nom_fichier, str(abonne.id), type_piece)
        url_stockage = f"/storage/pieces/{abonne.id}/{type_piece}/{nom_fichier}"  # Placeholder

    piece_id = uuid.uuid4()
    db.execute(
        text("""
            INSERT INTO pieces_administratives
            (id, abonne_id, type_piece, nom_fichier, url_stockage, taille_fichier,
             date_emission, date_expiration, notes)
            VALUES (:id, :abonne_id, :type_piece, :nom_fichier, :url_stockage, :taille,
                    :date_emission, :date_expiration, :notes)
        """),
        {
            "id":             str(piece_id),
            "abonne_id":      str(abonne.id),
            "type_piece":     type_piece,
            "nom_fichier":    nom_fichier,
            "url_stockage":   url_stockage,
            "taille":         taille,
            "date_emission":  date_emission,
            "date_expiration": date_expiration,
            "notes":          notes,
        }
    )
    db.commit()
    return {"id": str(piece_id), "message": "Pièce enregistrée"}


@router_pieces.delete("/{piece_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_piece(
    piece_id: str,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    db.execute(
        text("DELETE FROM pieces_administratives WHERE id = :id AND abonne_id = :abonne_id"),
        {"id": piece_id, "abonne_id": str(abonne.id)}
    )
    db.commit()


# ── Endpoints Tâches ──────────────────────────────────────────────────────────

@router_taches.post("/{candidature_id}/taches", status_code=status.HTTP_201_CREATED)
def create_tache(
    candidature_id: str,
    body: TacheCreate,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    tache_id = uuid.uuid4()
    db.execute(
        text("""
            INSERT INTO taches_candidature
            (id, candidature_id, titre, description, type_tache, priorite, date_echeance, assignee_id)
            VALUES (:id, :cand_id, :titre, :description, :type_tache, :priorite, :date_echeance, :assignee_id)
        """),
        {
            "id": str(tache_id), "cand_id": candidature_id,
            "titre": body.titre, "description": body.description,
            "type_tache": body.type_tache, "priorite": body.priorite,
            "date_echeance": body.date_echeance,
            "assignee_id": str(body.assignee_id) if body.assignee_id else None,
        }
    )
    db.commit()
    return {"id": str(tache_id)}


@router_taches.put("/{tache_id}")
def update_tache(
    tache_id: str,
    body: TacheUpdate,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"message": "Rien à mettre à jour"}
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = tache_id
    db.execute(text(f"UPDATE taches_candidature SET {set_clause} WHERE id = :id"), updates)
    db.commit()
    return {"message": "Tâche mise à jour"}


# ── Endpoints Offres IA ───────────────────────────────────────────────────────

@router_offres.post("/{candidature_id}/generer")
async def generer_offre(
    candidature_id: str,
    body: OffreGenererRequest,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Génère une offre technique via Claude API."""
    import anthropic

    # Récupérer les infos de l'AO
    row = db.execute(
        text("""
            SELECT a.titre, a.autorite_contractante, a.type_procedure,
                   a.secteur, a.description
            FROM candidatures c
            JOIN appels_offres a ON a.id = c.ao_id
            WHERE c.id = :id AND c.abonne_id = :abonne_id
        """),
        {"id": candidature_id, "abonne_id": str(abonne.id)}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Candidature introuvable")

    # Nom entreprise depuis le profil
    entreprise = body.entreprise_nom or abonne.entreprise or abonne.prenom + " " + abonne.nom

    prompt = f"""Tu es un expert en marchés publics burkinabè avec 15 ans d'expérience.
Tu aides une entreprise à rédiger son offre technique pour un appel d'offres.

## L'appel d'offres
Titre : {row.titre}
Autorité contractante : {row.autorite_contractante or 'Non précisée'}
Type de procédure : {row.type_procedure or 'ouvert'}
Secteur : {row.secteur}
Description : {row.description or 'Voir le dossier officiel'}

## L'entreprise soumissionnaire
Nom : {entreprise}
Secteur d'activité : {body.entreprise_secteur or row.secteur}
Références similaires : {body.references or 'À compléter par le soumissionnaire'}
Effectifs : {body.effectifs or 'À préciser'}
{f"Informations complémentaires : {body.informations_complementaires}" if body.informations_complementaires else ""}

## Ta mission
Rédige une offre technique professionnelle et complète en français,
adaptée au contexte des marchés publics du Burkina Faso.

Structure obligatoire :
1. Compréhension de la mission et des enjeux
2. Méthodologie proposée et approche technique
3. Planning d'exécution (tableau avec phases et délais)
4. Moyens humains (profils et compétences)
5. Moyens matériels et logistiques
6. Références de marchés similaires exécutés (tableau)
7. Garanties et service après-vente (si fournitures)

Directives de style :
- Ton professionnel, précis et confiant
- Phrases claires, paragraphes courts
- Utiliser des tableaux pour les plannings et références
- 4 à 6 pages (ne pas dépasser)
- Format Markdown structuré

IMPORTANT : Laisser des espaces réservés [À COMPLÉTER] pour les données
spécifiques que seule l'entreprise connaît (montants, dates exactes, noms propres).
"""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        contenu = message.content[0].text
    except Exception as e:
        logger.error(f"Erreur Claude API : {e}")
        raise HTTPException(status_code=503, detail="Service de génération IA temporairement indisponible")

    # Enregistrer l'offre générée
    offre_id = uuid.uuid4()
    db.execute(
        text("""
            INSERT INTO offres_generees
            (id, candidature_id, type_offre, contenu_ia, prompt_utilise, version)
            VALUES (:id, :cand_id, :type_offre, :contenu, :prompt, 1)
        """),
        {
            "id": str(offre_id), "cand_id": candidature_id,
            "type_offre": body.type_offre, "contenu": contenu,
            "prompt": prompt[:500],  # Tronquer pour la BDD
        }
    )
    db.commit()

    return {
        "offre_id": str(offre_id),
        "contenu": contenu,
        "type_offre": body.type_offre,
        "tokens_utilises": message.usage.output_tokens,
    }


@router_offres.put("/{offre_id}/valider")
def valider_offre(
    offre_id: str,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Marque une offre comme validée par l'utilisateur."""
    db.execute(
        text("UPDATE offres_generees SET valide_par_user = true WHERE id = :id"),
        {"id": offre_id}
    )
    db.commit()
    return {"message": "Offre validée"}
