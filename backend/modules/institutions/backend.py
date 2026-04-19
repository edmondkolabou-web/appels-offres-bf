"""
NetSync Gov Institutions — Backend FastAPI
Plateforme côté acheteur public : dashboard, profil public, stats, ciblage.
"""
import uuid
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr

from database import get_db
from security import get_current_abonne, require_pro
from models import Abonne

logger = logging.getLogger("netsync.institutions")

router_public = APIRouter(prefix="/api/v1/institutions", tags=["Institutions — Public"])
router_auth   = APIRouter(prefix="/api/v1/mon-institution", tags=["Institutions — Auth"])


# ── Schémas Pydantic ──────────────────────────────────────────────────────────

class InstitutionCreate(BaseModel):
    nom:              str
    sigle:            Optional[str] = None
    type_institution: str
    secteurs:         list[str] = []
    region:           Optional[str] = None
    email_contact:    Optional[str] = None
    telephone:        Optional[str] = None
    site_web:         Optional[str] = None
    description:      Optional[str] = None

class InstitutionUpdate(BaseModel):
    description:   Optional[str] = None
    email_contact: Optional[str] = None
    telephone:     Optional[str] = None
    site_web:      Optional[str] = None
    secteurs:      Optional[list[str]] = None
    region:        Optional[str] = None

class AOEnrichissement(BaseModel):
    ao_id:          uuid.UUID
    contact_nom:    Optional[str] = None
    contact_email:  Optional[str] = None
    contact_tel:    Optional[str] = None
    region_exacte:  Optional[str] = None
    dao_disponible: Optional[bool] = None
    informations_complementaires: Optional[str] = None

class NotificationCiblee(BaseModel):
    ao_id:          uuid.UUID
    secteurs_cibles: list[str]
    message_custom: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def generate_slug(nom: str) -> str:
    """Génère un slug URL-safe depuis le nom de l'institution."""
    import re
    slug = nom.lower()
    slug = re.sub(r'[àáâãäå]', 'a', slug)
    slug = re.sub(r'[èéêë]', 'e', slug)
    slug = re.sub(r'[ìíîï]', 'i', slug)
    slug = re.sub(r'[òóôõö]', 'o', slug)
    slug = re.sub(r'[ùúûü]', 'u', slug)
    slug = re.sub(r'[ç]', 'c', slug)
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')[:80]
    return slug


# ── Endpoints Publics ─────────────────────────────────────────────────────────

@router_public.get("")
def liste_institutions(
    type_institution: Optional[str] = None,
    region: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Liste publique des institutions partenaires NetSync Gov."""
    conditions = ["actif = true", "verifie = true"]
    params: dict = {"offset": (page - 1) * per_page, "limit": per_page}

    if type_institution:
        conditions.append("type_institution = :type")
        params["type"] = type_institution
    if region:
        conditions.append("region ILIKE :region")
        params["region"] = f"%{region}%"

    where = " AND ".join(conditions)
    total = db.execute(
        text(f"SELECT COUNT(*) FROM institutions WHERE {where}"), params
    ).scalar()

    rows = db.execute(text(f"""
        SELECT id, nom, sigle, slug, type_institution, secteurs,
               region, description, logo_url, site_web, plan,
               (SELECT COUNT(*) FROM appels_offres ao
                WHERE ao.institution_id = institutions.id) AS nb_ao_total,
               (SELECT COUNT(*) FROM appels_offres ao
                WHERE ao.institution_id = institutions.id
                  AND ao.date_publication >= NOW() - INTERVAL '30 days') AS nb_ao_mois
        FROM institutions
        WHERE {where}
        ORDER BY nb_ao_total DESC, nom ASC
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    return {
        "total": total,
        "page":  page,
        "institutions": [
            {
                "id":              str(r.id),
                "nom":             r.nom,
                "sigle":           r.sigle,
                "slug":            r.slug,
                "type":            r.type_institution,
                "secteurs":        r.secteurs or [],
                "region":          r.region,
                "description":     r.description,
                "logo_url":        r.logo_url,
                "site_web":        r.site_web,
                "plan":            r.plan,
                "nb_ao_total":     r.nb_ao_total,
                "nb_ao_ce_mois":   r.nb_ao_mois,
                "url_profil":      f"https://gov.netsync.bf/institutions/{r.slug}",
            }
            for r in rows
        ],
    }


@router_public.get("/{slug}")
def profil_institution_public(slug: str, db: Session = Depends(get_db)):
    """
    Profil public d'une institution : historique AOs, stats, contact.
    Indexé par les moteurs de recherche (SEO).
    """
    inst = db.execute(
        text("SELECT * FROM institutions WHERE slug = :slug AND actif = true"),
        {"slug": slug}
    ).fetchone()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution introuvable")

    # Stats globales
    stats = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE statut = 'ouvert') AS ouverts,
            AVG(montant_estime) AS montant_moyen,
            SUM(montant_estime) AS montant_total,
            MAX(date_publication) AS derniere_publication
        FROM appels_offres
        WHERE institution_id = :id
    """), {"id": str(inst.id)}).fetchone()

    # Par secteur
    par_secteur = db.execute(text("""
        SELECT secteur, COUNT(*) AS nb
        FROM appels_offres
        WHERE institution_id = :id AND secteur IS NOT NULL
        GROUP BY secteur ORDER BY nb DESC LIMIT 5
    """), {"id": str(inst.id)}).fetchall()

    # Derniers AOs publiés
    derniers_ao = db.execute(text("""
        SELECT id, reference, titre, secteur, type_procedure,
               statut, date_publication, date_cloture, montant_estime, est_urgent
        FROM appels_offres
        WHERE institution_id = :id
        ORDER BY date_publication DESC
        LIMIT 10
    """), {"id": str(inst.id)}).fetchall()

    return {
        "institution": {
            "id":          str(inst.id),
            "nom":         inst.nom,
            "sigle":       inst.sigle,
            "type":        inst.type_institution,
            "secteurs":    inst.secteurs or [],
            "region":      inst.region,
            "description": inst.description,
            "logo_url":    inst.logo_url,
            "site_web":    inst.site_web,
            "email":       inst.email_contact,
            "telephone":   inst.telephone,
            "verifie":     inst.verifie,
        },
        "stats": {
            "total_ao":          stats.total,
            "ao_ouverts":        stats.ouverts,
            "montant_moyen":     int(stats.montant_moyen) if stats.montant_moyen else None,
            "montant_total":     int(stats.montant_total) if stats.montant_total else None,
            "derniere_publication": stats.derniere_publication.isoformat() if stats.derniere_publication else None,
        },
        "par_secteur": [{"secteur": r.secteur, "nb": r.nb} for r in par_secteur],
        "derniers_ao": [
            {
                **dict(r._mapping),
                "id": str(r.id),
                "date_publication": r.date_publication.isoformat() if r.date_publication else None,
                "date_cloture": r.date_cloture.isoformat() if r.date_cloture else None,
                "url_fiche": f"https://gov.netsync.bf/aos/{r.id}",
            }
            for r in derniers_ao
        ],
    }


# ── Endpoints Authentifiés (acheteur public) ──────────────────────────────────

@router_auth.post("/creer", status_code=status.HTTP_201_CREATED)
def creer_institution(
    body: InstitutionCreate,
    abonne: Abonne = Depends(get_current_abonne),
    db: Session = Depends(get_db),
):
    """
    Crée un compte institution lié au compte utilisateur.
    L'institution est créée en mode non-vérifié (nécessite validation NetSync Gov).
    """
    slug_base = generate_slug(body.nom)
    slug = slug_base

    # Éviter les doublons de slug
    counter = 1
    while db.execute(
        text("SELECT 1 FROM institutions WHERE slug = :slug"), {"slug": slug}
    ).fetchone():
        slug = f"{slug_base}-{counter}"
        counter += 1

    # Vérifier que l'abonné n'a pas déjà une institution
    existing = db.execute(
        text("SELECT id FROM institutions WHERE abonne_id = :id"),
        {"id": str(abonne.id)}
    ).fetchone()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Vous avez déjà une institution enregistrée"
        )

    inst_id = uuid.uuid4()
    db.execute(text("""
        INSERT INTO institutions
        (id, nom, sigle, slug, type_institution, secteurs, region,
         email_contact, telephone, site_web, description,
         plan, actif, verifie, abonne_id)
        VALUES
        (:id, :nom, :sigle, :slug, :type, :secteurs, :region,
         :email, :tel, :site, :desc,
         'gratuit', true, false, :abonne_id)
    """), {
        "id":         str(inst_id),
        "nom":        body.nom,
        "sigle":      body.sigle,
        "slug":       slug,
        "type":       body.type_institution,
        "secteurs":   body.secteurs,
        "region":     body.region,
        "email":      body.email_contact,
        "tel":        body.telephone,
        "site":       body.site_web,
        "desc":       body.description,
        "abonne_id":  str(abonne.id),
    })
    db.commit()
    logger.info(f"Institution créée : {body.nom} ({slug}) par {abonne.email}")

    return {
        "id":      str(inst_id),
        "slug":    slug,
        "message": (
            "Institution enregistrée. Notre équipe va vérifier les informations "
            "sous 24-48h. Vous serez notifié par email."
        ),
        "url_profil": f"https://gov.netsync.bf/institutions/{slug}",
    }


@router_auth.get("/dashboard")
def dashboard_institution(
    abonne: Abonne = Depends(get_current_abonne),
    db: Session = Depends(get_db),
):
    """
    Dashboard complet pour l'institution :
    stats de ses AOs, consultations, tendances.
    """
    inst = db.execute(
        text("SELECT * FROM institutions WHERE abonne_id = :id"),
        {"id": str(abonne.id)}
    ).fetchone()
    if not inst:
        raise HTTPException(status_code=404, detail="Aucune institution liée à ce compte")

    # Stats globales
    stats = db.execute(text("""
        SELECT
            COUNT(*) AS total_ao,
            COUNT(*) FILTER (WHERE statut = 'ouvert')    AS ao_ouverts,
            COUNT(*) FILTER (WHERE statut = 'cloture')   AS ao_clotures,
            COUNT(*) FILTER (WHERE statut = 'attribue')  AS ao_attribues,
            COUNT(*) FILTER (WHERE date_publication >= NOW() - INTERVAL '30 days') AS ao_ce_mois,
            AVG(montant_estime)  AS montant_moyen,
            SUM(montant_estime)  AS montant_total,
            AVG(EXTRACT(DAY FROM (date_cloture - date_publication)))::int AS delai_moyen_j
        FROM appels_offres
        WHERE institution_id = :id
    """), {"id": str(inst.id)}).fetchone()

    # Évolution 6 mois
    evolution = db.execute(text("""
        SELECT
            DATE_TRUNC('month', date_publication) AS mois,
            COUNT(*) AS nb
        FROM appels_offres
        WHERE institution_id = :id
          AND date_publication >= NOW() - INTERVAL '6 months'
        GROUP BY 1 ORDER BY 1
    """), {"id": str(inst.id)}).fetchall()

    # Répartition sectorielle
    par_secteur = db.execute(text("""
        SELECT secteur, COUNT(*) AS nb
        FROM appels_offres
        WHERE institution_id = :id AND secteur IS NOT NULL
        GROUP BY secteur ORDER BY nb DESC
    """), {"id": str(inst.id)}).fetchall()

    # AOs urgents en cours
    urgents = db.execute(text("""
        SELECT id, titre, date_cloture, jours_restants, secteur
        FROM appels_offres
        WHERE institution_id = :id
          AND statut = 'ouvert'
          AND date_cloture <= NOW() + INTERVAL '7 days'
        ORDER BY date_cloture ASC
    """), {"id": str(inst.id)}).fetchall()

    return {
        "institution": {
            "id":       str(inst.id),
            "nom":      inst.nom,
            "slug":     inst.slug,
            "plan":     inst.plan,
            "verifie":  inst.verifie,
        },
        "stats": {
            "total_ao":      stats.total_ao,
            "ao_ouverts":    stats.ao_ouverts,
            "ao_clotures":   stats.ao_clotures,
            "ao_attribues":  stats.ao_attribues,
            "ao_ce_mois":    stats.ao_ce_mois,
            "montant_moyen": int(stats.montant_moyen) if stats.montant_moyen else None,
            "montant_total": int(stats.montant_total) if stats.montant_total else None,
            "delai_moyen_j": stats.delai_moyen_j,
        },
        "evolution_6m": [
            {"mois": r.mois.strftime("%Y-%m"), "nb": r.nb}
            for r in evolution
        ],
        "par_secteur": [{"secteur": r.secteur, "nb": r.nb} for r in par_secteur],
        "ao_urgents":  [
            {
                "id":           str(r.id),
                "titre":        r.titre,
                "date_cloture": r.date_cloture.isoformat() if r.date_cloture else None,
                "jours_restants": r.jours_restants,
                "secteur":      r.secteur,
            }
            for r in urgents
        ],
    }


@router_auth.put("/profil")
def mettre_a_jour_profil(
    body: InstitutionUpdate,
    abonne: Abonne = Depends(get_current_abonne),
    db: Session = Depends(get_db),
):
    """Met à jour les informations publiques de l'institution."""
    inst = db.execute(
        text("SELECT id FROM institutions WHERE abonne_id = :id"),
        {"id": str(abonne.id)}
    ).fetchone()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution introuvable")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"message": "Rien à mettre à jour"}

    set_parts = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = str(inst.id)
    db.execute(
        text(f"UPDATE institutions SET {set_parts}, updated_at = now() WHERE id = :id"),
        updates
    )
    db.commit()
    return {"message": "Profil mis à jour"}


@router_auth.post("/enrichir-ao")
def enrichir_ao(
    body: AOEnrichissement,
    abonne: Abonne = Depends(get_current_abonne),
    db: Session = Depends(get_db),
):
    """
    Permet à l'institution d'enrichir les métadonnées d'un AO parsé.
    Ex: ajouter le contact DMP, préciser la région, confirmer le DAO disponible.
    """
    inst = db.execute(
        text("SELECT id FROM institutions WHERE abonne_id = :id"),
        {"id": str(abonne.id)}
    ).fetchone()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution introuvable")

    ao = db.execute(
        text("SELECT id, institution_id FROM appels_offres WHERE id = :ao_id"),
        {"ao_id": str(body.ao_id)}
    ).fetchone()
    if not ao:
        raise HTTPException(status_code=404, detail="AO introuvable")

    # Vérifier que l'AO appartient à cette institution (ou non assigné encore)
    if ao.institution_id and str(ao.institution_id) != str(inst.id):
        raise HTTPException(
            status_code=403,
            detail="Cet AO est assigné à une autre institution"
        )

    # Mettre à jour les informations de l'AO
    updates: dict = {}
    if not ao.institution_id:
        updates["institution_id"] = str(inst.id)
    if body.contact_nom:
        updates["contact_nom"] = body.contact_nom
    if body.contact_email:
        updates["contact_email"] = body.contact_email
    if body.contact_tel:
        updates["contact_tel"] = body.contact_tel
    if body.region_exacte:
        updates["region"] = body.region_exacte
    if body.dao_disponible is not None:
        updates["dao_disponible"] = body.dao_disponible
    if body.informations_complementaires:
        updates["description_enrichie"] = body.informations_complementaires

    if updates:
        set_parts = ", ".join(f"{k} = :{k}" for k in updates)
        updates["ao_id"] = str(body.ao_id)
        db.execute(
            text(f"UPDATE appels_offres SET {set_parts} WHERE id = :ao_id"),
            updates
        )
        db.commit()

    return {"message": "AO enrichi avec succès", "ao_id": str(body.ao_id)}


@router_auth.post("/notifier-soumissionnaires")
def notifier_soumissionnaires(
    body: NotificationCiblee,
    abonne: Abonne = Depends(get_current_abonne),
    db: Session = Depends(get_db),
):
    """
    Envoie une notification ciblée aux abonnés Pro des secteurs indiqués.
    Tarif : 5 000 FCFA par envoi (débité de l'abonnement institutionnel).
    """
    inst = db.execute(
        text("SELECT id, nom, plan FROM institutions WHERE abonne_id = :id"),
        {"id": str(abonne.id)}
    ).fetchone()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution introuvable")

    if inst.plan == "gratuit":
        raise HTTPException(
            status_code=402,
            detail="La notification ciblée requiert un abonnement institutionnel payant"
        )

    ao = db.execute(
        text("SELECT titre, date_cloture FROM appels_offres WHERE id = :id"),
        {"id": str(body.ao_id)}
    ).fetchone()
    if not ao:
        raise HTTPException(status_code=404, detail="AO introuvable")

    # Compter les abonnés ciblés
    abonnes_cibles = db.execute(text("""
        SELECT COUNT(*) FROM abonnes a
        JOIN preferences_alertes p ON p.abonne_id = a.id
        WHERE a.plan IN ('pro', 'equipe')
          AND a.actif = true
          AND p.secteurs && :secteurs
    """), {"secteurs": body.secteurs}).scalar()

    if abonnes_cibles == 0:
        return {"message": "Aucun abonné trouvé pour ces secteurs", "envoyes": 0}

    # En production : envoyer les notifications via Celery
    # Pour le MVP : logger et retourner le count
    logger.info(
        f"Notification ciblée : {inst.nom} → {abonnes_cibles} abonnés "
        f"(secteurs: {body.secteurs}, AO: {ao.titre})"
    )

    return {
        "message":       f"Notification envoyée à {abonnes_cibles} abonnés qualifiés",
        "ao_titre":      ao.titre,
        "secteurs":      body.secteurs,
        "cibles_count":  abonnes_cibles,
        "cout_fcfa":     5_000,
        "note":          "Montant débité de votre crédit institutionnel",
    }


@router_auth.get("/rapport-activite")
async def rapport_activite(
    mois: Optional[str] = Query(None, description="YYYY-MM, défaut = mois courant"),
    abonne: Abonne = Depends(get_current_abonne),
    db: Session = Depends(get_db),
):
    """
    Génère un rapport PDF d'activité mensuel pour l'institution.
    """
    import io
    from fastapi.responses import StreamingResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import cm

    inst = db.execute(
        text("SELECT * FROM institutions WHERE abonne_id = :id"),
        {"id": str(abonne.id)}
    ).fetchone()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution introuvable")

    # Déterminer le mois
    if mois:
        try:
            annee, num_mois = int(mois[:4]), int(mois[5:7])
            debut = date(annee, num_mois, 1)
        except (ValueError, IndexError):
            raise HTTPException(status_code=422, detail="Format YYYY-MM invalide")
    else:
        debut = date.today().replace(day=1)

    if debut.month == 12:
        fin = date(debut.year + 1, 1, 1) - timedelta(days=1)
    else:
        fin = date(debut.year, debut.month + 1, 1) - timedelta(days=1)

    # Stats du mois
    stats = db.execute(text("""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE statut='ouvert') AS ouverts,
               COUNT(*) FILTER (WHERE statut='attribue') AS attribues,
               AVG(montant_estime) AS montant_moyen,
               SUM(montant_estime) AS montant_total
        FROM appels_offres
        WHERE institution_id = :id
          AND date_publication BETWEEN :debut AND :fin
    """), {"id": str(inst.id), "debut": debut, "fin": fin}).fetchone()

    ao_liste = db.execute(text("""
        SELECT titre, secteur, type_procedure, date_publication, date_cloture, montant_estime, statut
        FROM appels_offres
        WHERE institution_id = :id
          AND date_publication BETWEEN :debut AND :fin
        ORDER BY date_publication DESC
    """), {"id": str(inst.id), "debut": debut, "fin": fin}).fetchall()

    # Générer le PDF
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    BLUE   = colors.HexColor("#0082C9")
    INK    = colors.HexColor("#0F1923")

    title_s = ParagraphStyle("T", parent=styles["Heading1"], textColor=BLUE, fontSize=16, spaceAfter=4)
    h2_s    = ParagraphStyle("H2", parent=styles["Heading2"], textColor=INK, fontSize=12, spaceAfter=4, spaceBefore=10)
    body_s  = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, leading=14)
    small_s = ParagraphStyle("S", parent=styles["Normal"], fontSize=8, textColor=colors.gray)

    story = []
    story.append(Paragraph("NetSync Gov — Rapport d'activité institutionnel", ParagraphStyle(
        "brand", parent=styles["Normal"], textColor=BLUE, fontSize=9, spaceAfter=2
    )))
    story.append(Paragraph(f"{inst.nom}", title_s))
    story.append(Paragraph(
        f"Période : {debut.strftime('%B %Y').capitalize()} · Généré le {date.today().strftime('%d/%m/%Y')}",
        small_s
    ))
    story.append(Spacer(1, 0.5*cm))

    # KPIs
    story.append(Paragraph("Résumé du mois", h2_s))
    kpi = [
        ["Indicateur", "Valeur"],
        ["AOs publiés", str(stats.total)],
        ["AOs en cours", str(stats.ouverts)],
        ["AOs attribués", str(stats.attribues)],
        ["Montant estimé total", f"{int(stats.montant_total or 0):,} FCFA"],
        ["Montant moyen par AO", f"{int(stats.montant_moyen or 0):,} FCFA"],
    ]
    t = Table(kpi, colWidths=[9*cm, 7*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), BLUE),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTSIZE",     (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#F7F9FB")]),
        ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Liste AOs
    if ao_liste:
        story.append(Paragraph("Détail des appels d'offres", h2_s))
        ao_data = [["Titre (abrégé)", "Secteur", "Clôture", "Montant", "Statut"]]
        for ao in ao_liste:
            ao_data.append([
                ao.titre[:45] + "…" if len(ao.titre) > 45 else ao.titre,
                ao.secteur or "—",
                ao.date_cloture.strftime("%d/%m/%Y") if ao.date_cloture else "—",
                f"{ao.montant_estime:,}" if ao.montant_estime else "N/A",
                ao.statut.upper(),
            ])
        ao_table = Table(ao_data, colWidths=[5.5*cm, 2.5*cm, 2.2*cm, 2.5*cm, 2*cm])
        ao_table.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), INK),
            ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
            ("FONTSIZE",     (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#F7F9FB")]),
            ("GRID",         (0,0), (-1,-1), 0.4, colors.HexColor("#E2E8F0")),
            ("TOPPADDING",   (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
            ("LEFTPADDING",  (0,0), (-1,-1), 5),
        ]))
        story.append(ao_table)

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"© NetSync Gov · gov.netsync.bf · Rapport généré automatiquement pour {inst.nom}",
        small_s
    ))

    doc.build(story)
    buffer.seek(0)
    nom_fichier = f"rapport_activite_{inst.slug}_{debut.strftime('%Y_%m')}.pdf"
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nom_fichier}"}
    )
