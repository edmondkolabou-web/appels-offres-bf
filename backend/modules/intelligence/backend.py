"""
NetSync Gov Intelligence — Backend FastAPI
Endpoints d'analyse et de tendances sur la commande publique BF.
Toutes les requêtes sont basées sur la table appels_offres existante.
"""
import io
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_db
from backend.security import get_current_abonne, require_pro
from backend.models import Abonne

logger = logging.getLogger("netsync.intelligence")

router = APIRouter(prefix="/api/v1/intelligence", tags=["Intelligence"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def periode_to_dates(periode: str) -> tuple[date, date]:
    """Convertit une période en (date_debut, date_fin)."""
    today = date.today()
    if periode == "7j":
        return today - timedelta(days=7), today
    if periode == "30j":
        return today - timedelta(days=30), today
    if periode == "3m":
        return today - timedelta(days=90), today
    if periode == "6m":
        return today - timedelta(days=180), today
    if periode == "12m":
        return today - timedelta(days=365), today
    if periode == "24m":
        return today - timedelta(days=730), today
    return today - timedelta(days=365), today


# ── Endpoints Tendances ───────────────────────────────────────────────────────

@router.get("/tendances/secteurs")
def tendances_par_secteur(
    periode: str = Query("12m", description="7j|30j|3m|6m|12m|24m"),
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """
    Volume et montant moyen des AOs par secteur sur la période.
    Utilisé pour le graphique barres du dashboard Intelligence.
    """
    debut, fin = periode_to_dates(periode)
    rows = db.execute(text("""
        SELECT
            secteur,
            COUNT(*)                            AS nb_ao,
            AVG(montant_estime)                 AS montant_moyen,
            SUM(montant_estime)                 AS montant_total,
            COUNT(*) FILTER (WHERE statut = 'ouvert') AS nb_ouverts,
            MAX(date_publication)               AS derniere_publication
        FROM appels_offres
        WHERE date_publication BETWEEN :debut AND :fin
          AND secteur IS NOT NULL
        GROUP BY secteur
        ORDER BY nb_ao DESC
    """), {"debut": debut, "fin": fin}).fetchall()

    return {
        "periode": periode,
        "date_debut": debut.isoformat(),
        "date_fin": fin.isoformat(),
        "secteurs": [
            {
                "secteur":              r.secteur,
                "nb_ao":                r.nb_ao,
                "nb_ouverts":           r.nb_ouverts,
                "montant_moyen":        int(r.montant_moyen) if r.montant_moyen else None,
                "montant_total":        int(r.montant_total) if r.montant_total else None,
                "derniere_publication": r.derniere_publication.isoformat() if r.derniere_publication else None,
            }
            for r in rows
        ],
    }


@router.get("/tendances/evolution")
def evolution_mensuelle(
    secteur: Optional[str] = Query(None, description="Filtrer par secteur"),
    periode: str = Query("12m"),
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """
    Évolution mensuelle du nombre d'AOs.
    Utilisé pour le graphique courbe du dashboard Intelligence.
    """
    debut, fin = periode_to_dates(periode)
    query = """
        SELECT
            DATE_TRUNC('month', date_publication) AS mois,
            COUNT(*)                              AS nb_ao,
            AVG(montant_estime)                   AS montant_moyen,
            SUM(montant_estime)                   AS montant_total
        FROM appels_offres
        WHERE date_publication BETWEEN :debut AND :fin
    """
    params: dict = {"debut": debut, "fin": fin}
    if secteur:
        query += " AND secteur = :secteur"
        params["secteur"] = secteur
    query += " GROUP BY 1 ORDER BY 1"

    rows = db.execute(text(query), params).fetchall()
    return {
        "periode": periode,
        "secteur": secteur,
        "evolution": [
            {
                "mois":           r.mois.strftime("%Y-%m"),
                "mois_label":     r.mois.strftime("%b %Y"),
                "nb_ao":          r.nb_ao,
                "montant_moyen":  int(r.montant_moyen) if r.montant_moyen else None,
                "montant_total":  int(r.montant_total) if r.montant_total else None,
            }
            for r in rows
        ],
    }


@router.get("/tendances/saisonnalite")
def saisonnalite(
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """
    Distribution des AOs par jour de la semaine et mois de l'année.
    Révèle les patterns de publication budgétaire BF.
    """
    # Par mois de l'année (agrégé sur toutes les années)
    par_mois = db.execute(text("""
        SELECT
            EXTRACT(MONTH FROM date_publication)::int AS num_mois,
            TO_CHAR(date_publication, 'Mon')           AS label_mois,
            COUNT(*)                                   AS nb_ao
        FROM appels_offres
        WHERE date_publication IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1
    """)).fetchall()

    # Par jour de la semaine
    par_jour = db.execute(text("""
        SELECT
            EXTRACT(DOW FROM date_publication)::int AS num_jour,
            TO_CHAR(date_publication, 'Day')        AS label_jour,
            COUNT(*)                                AS nb_ao
        FROM appels_offres
        WHERE date_publication IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1
    """)).fetchall()

    return {
        "par_mois": [{"mois": r.num_mois, "label": r.label_mois, "nb_ao": r.nb_ao} for r in par_mois],
        "par_jour": [{"jour": r.num_jour, "label": r.label_jour.strip(), "nb_ao": r.nb_ao} for r in par_jour],
        "insight": (
            "La commande publique burkinabè suit le cycle budgétaire : "
            "pic de publications en mars-avril (début d'exercice) "
            "et septembre-octobre (avant clôture budgétaire)."
        ),
    }


@router.get("/tendances/types-procedures")
def repartition_procedures(
    periode: str = Query("12m"),
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Répartition des AOs par type de procédure (camembert)."""
    debut, fin = periode_to_dates(periode)
    rows = db.execute(text("""
        SELECT
            COALESCE(type_procedure, 'non_precise') AS type_procedure,
            COUNT(*)                                 AS nb_ao,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
        FROM appels_offres
        WHERE date_publication BETWEEN :debut AND :fin
        GROUP BY 1
        ORDER BY 2 DESC
    """), {"debut": debut, "fin": fin}).fetchall()

    return {
        "periode": periode,
        "procedures": [
            {"type": r.type_procedure, "nb_ao": r.nb_ao, "pct": float(r.pct)}
            for r in rows
        ],
    }


# ── Endpoints Autorités contractantes ────────────────────────────────────────

@router.get("/autorites")
def top_autorites(
    limite: int = Query(10, ge=1, le=50),
    periode: str = Query("12m"),
    secteur: Optional[str] = None,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Top N des autorités contractantes les plus actives."""
    debut, fin = periode_to_dates(periode)
    query = """
        SELECT
            autorite_contractante,
            COUNT(*)                 AS nb_ao,
            AVG(montant_estime)      AS montant_moyen,
            SUM(montant_estime)      AS montant_total,
            MAX(date_publication)    AS derniere_publication,
            COUNT(DISTINCT secteur)  AS nb_secteurs
        FROM appels_offres
        WHERE date_publication BETWEEN :debut AND :fin
          AND autorite_contractante IS NOT NULL
    """
    params: dict = {"debut": debut, "fin": fin}
    if secteur:
        query += " AND secteur = :secteur"
        params["secteur"] = secteur
    query += " GROUP BY 1 ORDER BY nb_ao DESC LIMIT :limite"
    params["limite"] = limite

    rows = db.execute(text(query), params).fetchall()
    return {
        "periode": periode,
        "autorites": [
            {
                "nom":                  r.autorite_contractante,
                "nb_ao":               r.nb_ao,
                "montant_moyen":       int(r.montant_moyen) if r.montant_moyen else None,
                "montant_total":       int(r.montant_total) if r.montant_total else None,
                "derniere_publication": r.derniere_publication.isoformat(),
                "nb_secteurs":         r.nb_secteurs,
            }
            for r in rows
        ],
    }


@router.get("/autorites/{nom_autorite}")
def profil_autorite(
    nom_autorite: str,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """
    Fiche complète d'une autorité contractante :
    historique, secteurs, montants, délais moyens, saisonnalité.
    """
    # Vérifier que l'autorité existe
    exists = db.execute(
        text("SELECT COUNT(*) FROM appels_offres WHERE autorite_contractante ILIKE :nom"),
        {"nom": f"%{nom_autorite}%"}
    ).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Autorité contractante introuvable")

    # Stats globales
    stats = db.execute(text("""
        SELECT
            COUNT(*)                 AS nb_ao_total,
            AVG(montant_estime)      AS montant_moyen,
            SUM(montant_estime)      AS montant_total,
            MIN(date_publication)    AS premier_ao,
            MAX(date_publication)    AS dernier_ao,
            AVG(
                EXTRACT(DAY FROM (date_cloture - date_publication))
            )::int                   AS delai_moyen_jours
        FROM appels_offres
        WHERE autorite_contractante ILIKE :nom
    """), {"nom": f"%{nom_autorite}%"}).fetchone()

    # Par secteur
    par_secteur = db.execute(text("""
        SELECT secteur, COUNT(*) AS nb
        FROM appels_offres
        WHERE autorite_contractante ILIKE :nom AND secteur IS NOT NULL
        GROUP BY secteur ORDER BY nb DESC LIMIT 5
    """), {"nom": f"%{nom_autorite}%"}).fetchall()

    # Évolution 12 mois
    evolution = db.execute(text("""
        SELECT DATE_TRUNC('month', date_publication) AS mois, COUNT(*) AS nb
        FROM appels_offres
        WHERE autorite_contractante ILIKE :nom
          AND date_publication >= NOW() - INTERVAL '12 months'
        GROUP BY 1 ORDER BY 1
    """), {"nom": f"%{nom_autorite}%"}).fetchall()

    # Derniers AOs
    derniers = db.execute(text("""
        SELECT id, titre, secteur, date_publication, date_cloture, statut
        FROM appels_offres
        WHERE autorite_contractante ILIKE :nom
        ORDER BY date_publication DESC LIMIT 5
    """), {"nom": f"%{nom_autorite}%"}).fetchall()

    return {
        "autorite": nom_autorite,
        "stats": {
            "nb_ao_total":      stats.nb_ao_total,
            "montant_moyen":    int(stats.montant_moyen) if stats.montant_moyen else None,
            "montant_total":    int(stats.montant_total) if stats.montant_total else None,
            "premier_ao":       stats.premier_ao.isoformat() if stats.premier_ao else None,
            "dernier_ao":       stats.dernier_ao.isoformat() if stats.dernier_ao else None,
            "delai_moyen_jours": stats.delai_moyen_jours,
        },
        "par_secteur": [{"secteur": r.secteur, "nb": r.nb} for r in par_secteur],
        "evolution_12m": [
            {"mois": r.mois.strftime("%Y-%m"), "nb": r.nb} for r in evolution
        ],
        "derniers_ao": [dict(r._mapping) for r in derniers],
    }


# ── Endpoint Résumé global ────────────────────────────────────────────────────

@router.get("/resume")
def resume_commande_publique(
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """
    Résumé global de la commande publique BF indexée par NetSync Gov.
    Affiché en haut du dashboard Intelligence.
    """
    today = date.today()

    # Stats globales
    total = db.execute(text("SELECT COUNT(*) FROM appels_offres")).scalar()
    ce_mois = db.execute(text("""
        SELECT COUNT(*) FROM appels_offres
        WHERE date_publication >= DATE_TRUNC('month', NOW())
    """)).scalar()
    hier = db.execute(text("""
        SELECT COUNT(*) FROM appels_offres
        WHERE date_publication = CURRENT_DATE - 1
    """)).scalar()
    montant_total = db.execute(text("""
        SELECT SUM(montant_estime) FROM appels_offres
        WHERE montant_estime IS NOT NULL
    """)).scalar()

    # Secteur le plus actif ce mois
    top_secteur = db.execute(text("""
        SELECT secteur, COUNT(*) AS nb
        FROM appels_offres
        WHERE date_publication >= DATE_TRUNC('month', NOW())
          AND secteur IS NOT NULL
        GROUP BY secteur ORDER BY nb DESC LIMIT 1
    """)).fetchone()

    # Tendance : ce mois vs mois dernier
    mois_dernier = db.execute(text("""
        SELECT COUNT(*) FROM appels_offres
        WHERE date_publication >= DATE_TRUNC('month', NOW()) - INTERVAL '1 month'
          AND date_publication < DATE_TRUNC('month', NOW())
    """)).scalar()
    tendance = None
    if mois_dernier and mois_dernier > 0:
        tendance = round((ce_mois - mois_dernier) / mois_dernier * 100, 1)

    return {
        "total_ao_indexes":      total,
        "ao_ce_mois":            ce_mois,
        "ao_hier":               hier,
        "montant_total_fcfa":    int(montant_total) if montant_total else None,
        "top_secteur_ce_mois":   top_secteur.secteur if top_secteur else None,
        "tendance_vs_mois_pct":  tendance,
        "derniere_mise_a_jour":  today.isoformat(),
    }


# ── Génération rapport PDF mensuel ────────────────────────────────────────────

@router.get("/rapport/mensuel")
async def generer_rapport_mensuel(
    mois: Optional[str] = Query(None, description="Format YYYY-MM, défaut = mois courant"),
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """
    Génère un rapport PDF mensuel sur la commande publique BF.
    Utilise Claude pour rédiger les analyses textuelles.
    """
    import anthropic
    import os
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import cm

    # Déterminer le mois cible
    if mois:
        try:
            annee, num_mois = int(mois[:4]), int(mois[5:7])
            debut_mois = date(annee, num_mois, 1)
        except (ValueError, IndexError):
            raise HTTPException(status_code=422, detail="Format de mois invalide (attendu: YYYY-MM)")
    else:
        today = date.today()
        debut_mois = today.replace(day=1) - timedelta(days=1)
        debut_mois = debut_mois.replace(day=1)

    if debut_mois.month == 12:
        fin_mois = date(debut_mois.year + 1, 1, 1) - timedelta(days=1)
    else:
        fin_mois = date(debut_mois.year, debut_mois.month + 1, 1) - timedelta(days=1)

    # Récupérer les données du mois
    stats_mois = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE secteur = 'btp') AS btp,
            COUNT(*) FILTER (WHERE secteur = 'informatique') AS it,
            COUNT(*) FILTER (WHERE secteur = 'sante') AS sante,
            COUNT(*) FILTER (WHERE secteur = 'agriculture') AS agriculture,
            COUNT(*) FILTER (WHERE secteur = 'conseil') AS conseil,
            AVG(montant_estime) AS montant_moyen,
            SUM(montant_estime) AS montant_total,
            COUNT(*) FILTER (WHERE type_procedure = 'ouvert') AS ao_ouverts,
            COUNT(*) FILTER (WHERE type_procedure = 'dpx') AS dpx
        FROM appels_offres
        WHERE date_publication BETWEEN :debut AND :fin
    """), {"debut": debut_mois, "fin": fin_mois}).fetchone()

    top_autorites = db.execute(text("""
        SELECT autorite_contractante, COUNT(*) AS nb
        FROM appels_offres
        WHERE date_publication BETWEEN :debut AND :fin
          AND autorite_contractante IS NOT NULL
        GROUP BY 1 ORDER BY nb DESC LIMIT 5
    """), {"debut": debut_mois, "fin": fin_mois}).fetchall()

    # Générer l'analyse textuelle avec Claude
    prompt = f"""Tu es un analyste expert en commande publique burkinabè.
Rédige une analyse professionnelle et concise (300 mots max) du marché
des appels d'offres publics du Burkina Faso pour le mois de
{debut_mois.strftime('%B %Y')}.

Données disponibles :
- Total AOs publiés : {stats_mois.total}
- BTP : {stats_mois.btp} | Informatique : {stats_mois.it} | Santé : {stats_mois.sante}
- Agriculture : {stats_mois.agriculture} | Conseil : {stats_mois.conseil}
- Montant total estimé : {int(stats_mois.montant_total or 0):,} FCFA
- AOs ouverts : {stats_mois.ao_ouverts} | Demandes de prix : {stats_mois.dpx}
- Top autorités : {', '.join(r.autorite_contractante for r in top_autorites[:3])}

Structure :
1. Faits saillants du mois (2-3 points clés)
2. Tendances sectorielles
3. Points d'attention pour les soumissionnaires

Style : professionnel, factuel, en français. Pas de bullet points excessifs."""

    analyse_texte = "Analyse non disponible (clé API manquante)"
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        analyse_texte = msg.content[0].text
    except Exception as e:
        logger.warning(f"Claude non disponible pour le rapport : {e}")

    # Générer le PDF avec ReportLab
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    BLUE   = colors.HexColor("#0082C9")
    INK    = colors.HexColor("#0F1923")

    title_style = ParagraphStyle("Title", parent=styles["Heading1"],
                                  textColor=BLUE, fontSize=18, spaceAfter=6)
    h2_style    = ParagraphStyle("H2", parent=styles["Heading2"],
                                  textColor=INK, fontSize=13, spaceAfter=4, spaceBefore=12)
    body_style  = ParagraphStyle("Body", parent=styles["Normal"],
                                  fontSize=10, leading=14, spaceAfter=6)
    small_style = ParagraphStyle("Small", parent=styles["Normal"],
                                  fontSize=8, textColor=colors.gray)

    story = []

    # En-tête
    story.append(Paragraph("NetSync Gov", ParagraphStyle("Brand", parent=styles["Normal"],
                              textColor=BLUE, fontSize=10, spaceAfter=2)))
    story.append(Paragraph(
        f"Rapport mensuel — Commande publique Burkina Faso",
        title_style
    ))
    story.append(Paragraph(
        f"{debut_mois.strftime('%B %Y').capitalize()} · Généré le {date.today().strftime('%d/%m/%Y')}",
        small_style
    ))
    story.append(Spacer(1, 0.5*cm))

    # Stats clés
    story.append(Paragraph("Chiffres clés du mois", h2_style))
    kpi_data = [
        ["Indicateur", "Valeur"],
        ["AOs publiés", str(stats_mois.total)],
        ["Montant total estimé", f"{int(stats_mois.montant_total or 0):,} FCFA"],
        ["Montant moyen", f"{int(stats_mois.montant_moyen or 0):,} FCFA"],
        ["AOs ouverts", str(stats_mois.ao_ouverts)],
        ["Demandes de prix", str(stats_mois.dpx)],
    ]
    kpi_table = Table(kpi_data, colWidths=[9*cm, 7*cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5*cm))

    # Répartition sectorielle
    story.append(Paragraph("Répartition sectorielle", h2_style))
    sect_data = [
        ["Secteur", "Nombre d'AOs"],
        ["BTP",          str(stats_mois.btp)],
        ["Informatique", str(stats_mois.it)],
        ["Santé",        str(stats_mois.sante)],
        ["Agriculture",  str(stats_mois.agriculture)],
        ["Conseil",      str(stats_mois.conseil)],
    ]
    sect_table = Table(sect_data, colWidths=[9*cm, 7*cm])
    sect_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#0F1923")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(sect_table)
    story.append(Spacer(1, 0.5*cm))

    # Top autorités
    story.append(Paragraph("Top 5 autorités contractantes", h2_style))
    auth_data = [["Autorité contractante", "AOs"]] + [
        [r.autorite_contractante[:55], str(r.nb)] for r in top_autorites
    ]
    auth_table = Table(auth_data, colWidths=[13*cm, 3*cm])
    auth_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#0F1923")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(auth_table)
    story.append(Spacer(1, 0.5*cm))

    # Analyse IA
    story.append(Paragraph("Analyse du marché", h2_style))
    story.append(Paragraph(analyse_texte.replace("\n", "<br/>"), body_style))
    story.append(Spacer(1, 0.5*cm))

    # Pied de page
    story.append(Paragraph(
        "© NetSync Gov · gov.netsync.bf · Données : DGCMEF, UNDP, Banque Mondiale · "
        "Ce rapport est généré automatiquement à partir des données indexées.",
        small_style
    ))

    doc.build(story)
    buffer.seek(0)

    nom_fichier = f"netsync_gov_rapport_{debut_mois.strftime('%Y_%m')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nom_fichier}"},
    )


# ── API stats publique (rate-limited) ────────────────────────────────────────

@router.get("/stats/publiques")
def stats_publiques(db: Session = Depends(get_db)):
    """
    Statistiques agrégées publiques (sans authentification).
    Rate-limited : 10 req/min via Nginx.
    Utilisable par des tiers, ERP, journalistes.
    """
    total = db.execute(text("SELECT COUNT(*) FROM appels_offres")).scalar()
    ouverts = db.execute(text(
        "SELECT COUNT(*) FROM appels_offres WHERE statut = 'ouvert'"
    )).scalar()
    ce_mois = db.execute(text("""
        SELECT COUNT(*) FROM appels_offres
        WHERE date_publication >= DATE_TRUNC('month', NOW())
    """)).scalar()

    return {
        "source":       "NetSync Gov — gov.netsync.bf",
        "total_indexes": total,
        "ao_ouverts":   ouverts,
        "ao_ce_mois":   ce_mois,
        "mis_a_jour":   date.today().isoformat(),
        "note":         "Données DGCMEF Burkina Faso. Usage commercial via plan API Business.",
    }
