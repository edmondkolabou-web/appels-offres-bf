# NetSync Gov Candidature — Spécification technique

## Architecture générale

```
┌─────────────────────────────────────────────────────────┐
│                  NetSync Gov Candidature                 │
├──────────────────┬──────────────────┬───────────────────┤
│  Module Suivi    │  Module Pièces   │  Module Offre IA  │
│  (Kanban AO)     │  (Documents)     │  (Claude API)     │
├──────────────────┴──────────────────┴───────────────────┤
│              API FastAPI existante (étendue)             │
├─────────────────────────────────────────────────────────┤
│              PostgreSQL — nouvelles tables               │
└─────────────────────────────────────────────────────────┘
```

---

## Nouvelles tables PostgreSQL

### Table : candidatures
```sql
CREATE TABLE candidatures (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ao_id           UUID NOT NULL REFERENCES appels_offres(id),
    abonne_id       UUID NOT NULL REFERENCES abonnes(id),
    equipe_id       UUID REFERENCES equipes(id),

    -- Statut du dossier
    statut          VARCHAR(20) NOT NULL DEFAULT 'en_veille'
                    CHECK (statut IN (
                        'en_veille',      -- AO repéré, pas encore décidé
                        'decision',       -- En cours d'analyse go/no-go
                        'en_preparation', -- Dossier en cours de montage
                        'depose',         -- Dossier soumis
                        'gagne',          -- Marché attribué
                        'perdu',          -- Non retenu
                        'abandonne'       -- Décision de ne pas candidater
                    )),

    -- Informations candidature
    responsable_id  UUID REFERENCES abonnes(id),  -- Qui pilote le dossier
    notes           TEXT,
    montant_offre   BIGINT,                        -- Montant de l'offre en FCFA
    score_go_nogo   INTEGER CHECK (score_go_nogo BETWEEN 0 AND 100),

    -- Dates clés
    date_decision   DATE,   -- Date go/no-go interne
    date_depot      DATE,   -- Date de soumission effective
    date_resultat   DATE,   -- Date de publication des résultats

    -- Métadonnées
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_candidatures_ao       ON candidatures(ao_id);
CREATE INDEX idx_candidatures_abonne   ON candidatures(abonne_id);
CREATE INDEX idx_candidatures_statut   ON candidatures(statut);
```

### Table : pieces_administratives
```sql
CREATE TABLE pieces_administratives (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    abonne_id       UUID NOT NULL REFERENCES abonnes(id),

    -- Type de pièce
    type_piece      VARCHAR(50) NOT NULL
                    CHECK (type_piece IN (
                        'asf',        -- Attestation Situation Fiscale
                        'cnss',       -- Attestation CNSS
                        'aje',        -- Attestation Jouissance Existence
                        'ifu',        -- Identifiant Fiscal Unique
                        'rccm',       -- Registre Commerce
                        'statuts',    -- Statuts de la société
                        'attestation_bancaire',
                        'cv',         -- CV dirigeant/expert
                        'reference_marche', -- Référence marché similaire
                        'autre'
                    )),

    -- Fichier
    nom_fichier     VARCHAR(255),
    url_stockage    TEXT,          -- URL S3/Backblaze
    taille_fichier  INTEGER,       -- En octets

    -- Validité
    date_emission   DATE,
    date_expiration DATE,
    est_valide      BOOLEAN GENERATED ALWAYS AS (
                        date_expiration IS NULL
                        OR date_expiration >= CURRENT_DATE
                    ) STORED,

    -- Métadonnées
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_pieces_abonne     ON pieces_administratives(abonne_id);
CREATE INDEX idx_pieces_expiration ON pieces_administratives(date_expiration)
             WHERE date_expiration IS NOT NULL;
```

### Table : taches_candidature
```sql
CREATE TABLE taches_candidature (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidature_id    UUID NOT NULL REFERENCES candidatures(id) ON DELETE CASCADE,
    assignee_id       UUID REFERENCES abonnes(id),

    titre             VARCHAR(255) NOT NULL,
    description       TEXT,
    type_tache        VARCHAR(30) CHECK (type_tache IN (
                          'piece_admin', 'offre_technique',
                          'offre_financiere', 'relecture',
                          'depot', 'autre'
                      )),
    statut            VARCHAR(20) DEFAULT 'todo'
                      CHECK (statut IN ('todo', 'en_cours', 'fait', 'bloque')),
    priorite          VARCHAR(10) DEFAULT 'normale'
                      CHECK (priorite IN ('basse', 'normale', 'haute', 'critique')),
    date_echeance     DATE,
    created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_taches_candidature ON taches_candidature(candidature_id);
CREATE INDEX idx_taches_assignee    ON taches_candidature(assignee_id);
```

### Table : offres_generees
```sql
CREATE TABLE offres_generees (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidature_id    UUID NOT NULL REFERENCES candidatures(id) ON DELETE CASCADE,
    type_offre        VARCHAR(20) CHECK (type_offre IN ('technique', 'financiere', 'complete')),
    contenu_ia        TEXT NOT NULL,  -- Texte généré par Claude
    prompt_utilise    TEXT,           -- Prompt envoyé à Claude
    version           INTEGER DEFAULT 1,
    valide_par_user   BOOLEAN DEFAULT false,
    created_at        TIMESTAMPTZ DEFAULT now()
);
```

---

## Nouveaux endpoints API FastAPI

### Router : /api/v1/candidatures

```
GET    /candidatures              → Liste mes candidatures (avec filtres statut)
POST   /candidatures              → Créer une candidature sur un AO
GET    /candidatures/{id}         → Détail candidature + pièces + tâches
PUT    /candidatures/{id}         → Mettre à jour statut, notes, montant
DELETE /candidatures/{id}         → Supprimer (soft delete)
POST   /candidatures/{id}/checklist → Générer checklist pièces auto par type AO
GET    /candidatures/{id}/avancement → Score de complétude du dossier (0-100%)
```

### Router : /api/v1/pieces
```
GET    /pieces                    → Toutes mes pièces administratives
POST   /pieces                    → Uploader une pièce (multipart/form-data)
PUT    /pieces/{id}               → Mettre à jour dates/notes
DELETE /pieces/{id}               → Supprimer une pièce
GET    /pieces/expiration         → Pièces expirant dans les 30 jours
```

### Router : /api/v1/taches
```
GET    /candidatures/{id}/taches  → Tâches d'une candidature
POST   /candidatures/{id}/taches  → Créer une tâche
PUT    /taches/{id}               → Mettre à jour statut/assignee
DELETE /taches/{id}               → Supprimer
```

### Router : /api/v1/offres-ia
```
POST   /candidatures/{id}/generer-offre  → Générer offre technique via Claude
GET    /candidatures/{id}/offres         → Historique offres générées
PUT    /offres/{id}/valider              → Marquer comme validée par l'utilisateur
```

---

## Logique de génération de checklist automatique

En fonction du type de procédure de l'AO, générer automatiquement
la liste des pièces obligatoires :

```python
PIECES_PAR_TYPE = {
    "ouvert": [
        {"type": "asf",       "obligatoire": True,  "validite_jours": 90},
        {"type": "cnss",      "obligatoire": True,  "validite_jours": 90},
        {"type": "aje",       "obligatoire": True,  "validite_jours": 365},
        {"type": "rccm",      "obligatoire": True,  "validite_jours": None},
        {"type": "ifu",       "obligatoire": True,  "validite_jours": None},
        {"type": "statuts",   "obligatoire": True,  "validite_jours": None},
        {"type": "reference_marche", "obligatoire": True,  "validite_jours": None},
        {"type": "attestation_bancaire", "obligatoire": False, "validite_jours": 30},
    ],
    "restreint": [
        # Même que ouvert + lettre de candidature
    ],
    "dpx": [
        {"type": "asf",  "obligatoire": True,  "validite_jours": 90},
        {"type": "cnss", "obligatoire": True,  "validite_jours": 90},
        {"type": "ifu",  "obligatoire": True,  "validite_jours": None},
        # Simplifié par rapport à l'AO ouvert
    ],
    "ami": [
        {"type": "cv",        "obligatoire": True,  "validite_jours": None},
        {"type": "rccm",      "obligatoire": False, "validite_jours": None},
        {"type": "reference_marche", "obligatoire": True, "validite_jours": None},
    ],
    "rfp": [
        # Similaire à AMI + offre financière détaillée
    ],
}
```

---

## Scoring de complétude du dossier

```python
def calculer_avancement(candidature_id: str, db: Session) -> dict:
    """
    Score de 0 à 100% basé sur :
    - Pièces obligatoires uploadées et valides (50%)
    - Offre technique générée et validée (25%)
    - Offre financière (15%)
    - Tâches complètes (10%)
    """
    ...
    return {
        "score_global": 72,
        "pieces_ok": 6,
        "pieces_total": 8,
        "pieces_expirees": 1,
        "offre_technique": "validee",
        "offre_financiere": "manquante",
        "taches_faites": 4,
        "taches_total": 6,
        "pret_depot": False,
        "blocages": ["ASF expirée", "Offre financière manquante"]
    }
```

---

## Génération d'offre technique — Prompt Claude

```python
PROMPT_OFFRE_TECHNIQUE = """
Tu es un expert en marchés publics burkinabè. Tu aides une entreprise
à rédiger son offre technique pour un appel d'offres.

## Informations sur l'AO
Titre : {ao_titre}
Autorité contractante : {autorite}
Type de procédure : {type_procedure}
Secteur : {secteur}
Description : {description}

## Informations sur l'entreprise soumissionnaire
Nom : {entreprise_nom}
Secteur d'activité : {entreprise_secteur}
Références similaires : {references}
Effectifs : {effectifs}

## Instructions
Rédige une offre technique professionnelle et complète en français,
adaptée au contexte des marchés publics du Burkina Faso, incluant :

1. Compréhension de la mission (1 page)
2. Méthodologie proposée (2-3 pages)
3. Planning d'exécution (tableau)
4. Moyens humains et matériels
5. Expériences similaires (tableau de références)
6. Garanties et service après-vente (si fournitures)

Format : Markdown structuré, prêt à être copié dans un document Word.
Ton : Professionnel, précis, confiant. Éviter le jargon inutile.
Longueur : 4 à 6 pages.
"""
```

---

## Alertes automatiques Celery

```python
# Tâche quotidienne à 08h00
@celery_app.task(name="candidatures.alertes_pieces_expiration")
def alerter_pieces_expirantes():
    """
    Envoie des alertes pour les pièces qui expirent dans 30, 15 ou 7 jours.
    """

# Tâche quotidienne à 07h30 (après le pipeline AO)
@celery_app.task(name="candidatures.rappels_cloture")
def rappels_cloture_candidatures():
    """
    Pour chaque candidature en statut 'en_preparation',
    envoyer un rappel si la clôture de l'AO est dans 7, 3 ou 1 jour.
    """
```

---

## Stockage des fichiers

```
Fichiers uploadés → Backblaze B2 (cold storage, moins cher que S3)
URL signées → expiration 1h pour le téléchargement
Structure :
  /pieces/{abonne_id}/{type_piece}/{filename}_{timestamp}.pdf
```

Taille max par fichier : 10 MB
Formats acceptés : PDF, JPG, PNG, DOCX

---

## Intégration frontend Vue.js

### Nouveau store Pinia : candidatures.js
```javascript
// stores/candidatures.js
export const useCandidaturesStore = defineStore('candidatures', () => {
  const list    = ref([])
  const current = ref(null)

  // Actions
  async function create(aoId)         // Créer depuis la page détail AO
  async function fetchList(statut)    // Filtrer par statut (Kanban)
  async function fetchDetail(id)      // Détail + pièces + tâches
  async function updateStatut(id, s)  // Changer le statut (drag Kanban)
  async function genererOffre(id)     // Appel Claude API
})
```

### Nouvelles vues Vue.js
- `CandidaturesView.vue`   — Kanban par statut
- `CandidatureDetailView.vue` — Détail complet dossier
- `PiecesView.vue`          — Gestionnaire pièces admin
- `OffresView.vue`          — Offres IA générées

