# NetSync Gov — Roadmap Extension (post-lancement)
## Priorisé par impact × effort, ancré sur les retours bêta

---

## Vague 1 — Mois 2-3 : Sources secondaires

### CCI-BF (Chambre de Commerce)
**Impact** : accès à des AOs non publiés sur DGCMEF (PME locales)  
**Effort** : faible (même pipeline, scraping différent)

```python
# Ajouter dans watcher.py
class CCIBFWatcher:
    INDEX_URL = "https://www.cci.bf/?q=fr/opportunites-d-affaires"
    SOURCE    = "cci_bf"
```

### Banque Mondiale STEP
**Impact** : AOs financés BM — haute valeur, souvent ignorés par concurrents  
**Effort** : moyen (API REST STEP disponible)

```python
class WorldBankSTEPWatcher:
    API_URL = "https://step.worldbank.org/api/v1/notices?country=BF"
    SOURCE  = "bm_step"
```

### UNDP Procurement Notices
**Impact** : ONG, projets humanitaires — segment distinct  
**Effort** : faible (flux RSS existant)

---

## Vague 2 — Mois 3-4 : Fonctionnalités Pro

### Export CSV / Excel (plan Équipe)
Permettre l'export des AOs filtrés pour traitement externe.

```python
# Nouveau endpoint API
@router.get("/aos/export")
async def export_aos(format: str = "csv", ...):
    import csv, io
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[...])
    ...
    return StreamingResponse(output, media_type="text/csv")
```

### Suivi candidatures (plan Équipe)
Permettre aux équipes de noter le statut de leurs dossiers.

**Nouvelle table BDD** :
```sql
CREATE TABLE candidatures (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ao_id         uuid REFERENCES appels_offres(id),
    equipe_id     uuid REFERENCES equipes(id),
    statut        varchar(20) CHECK (statut IN ('en_cours','depose','gagne','perdu')),
    responsable   varchar(100),
    notes         text,
    date_depot    date,
    created_at    timestamptz DEFAULT now()
);
```

### Alertes mots-clés avancées (plan Pro)
Actuellement : secteur + mots-clés simples.  
Extension : opérateurs booléens (ET, OU, SAUF).

```python
# Dans preferences_alertes
mots_cles_inclus = Column(ARRAY(String))  # Déjà présent
mots_cles_exclus = Column(ARRAY(String))  # À ajouter
operateur        = Column(String, default="ou")  # "et" | "ou"
```

---

## Vague 3 — Mois 4-6 : Intelligence

### Analyse tendances sectorielles
Graphiques d'évolution du nombre d'AOs par secteur (dashboard).

```python
# Endpoint API existant à étendre
@router.get("/admin/stats/tendances")
def tendances(secteur: str, mois: int = 6):
    return db.execute(text("""
        SELECT DATE_TRUNC('month', date_publication) as mois,
               COUNT(*) as nb_ao,
               AVG(montant_estime) as montant_moyen
        FROM appels_offres
        WHERE secteur = :secteur
          AND date_publication >= NOW() - INTERVAL ':mois months'
        GROUP BY 1 ORDER BY 1
    """), {"secteur": secteur, "mois": mois}).fetchall()
```

### Scoring de pertinence AO (IA)
Utiliser Claude pour scorer la probabilité qu'un abonné soit qualifié pour un AO.

```python
# Dans parser.py — appel Claude après parsing
def score_pertinence(ao: AORaw, profil_abonne: dict) -> float:
    prompt = f"""
    AO : {ao.titre}
    Critères abonné : {profil_abonne}
    Score de pertinence 0-1 (1 = très pertinent) :
    """
    ...
```

### Extension géographique — Côte d'Ivoire
Même modèle, même stack, nouvelle source : ANRMP Côte d'Ivoire.  
**Potentiel** : marché 5× plus grand, même besoin inexistant localement.

---

## Vague 4 — Mois 6+ : Réseau

### API publique NetSync Gov
Permettre aux développeurs tiers d'intégrer les données AO.

```yaml
# Plans API
free:   100 req/jour, données J-7
pro:    10 000 req/jour, données temps réel
```

### Portail partenaires (cabinets comptables, avocats)
Permettre aux intermédiaires de gérer plusieurs clients.

### Application mobile (React Native)
Wrapper de la webapp Vue.js + notifications push natives.

---

## Priorité selon les retours bêta attendus

| Si retour fréquent | Extension prioritaire |
|---|---|
| "Je rate des AOs CCI-BF" | Vague 1 : sources secondaires |
| "J'ai besoin d'exporter pour mon équipe" | Vague 2 : export CSV |
| "Je veux filtrer plus finement" | Vague 2 : mots-clés avancés |
| "On soumet en équipe" | Vague 2 : suivi candidatures |
| "Quel secteur est le plus actif ?" | Vague 3 : tendances |
| "Vous avez ça pour la CI ?" | Vague 4 : expansion géographique |
