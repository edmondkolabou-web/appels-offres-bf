# NetSync Gov Institutions — Analyse du besoin

## Le problème côté acheteur public

Tous les modules précédents servent le soumissionnaire.
Institutions inverse la perspective : **il sert l'acheteur public.**

Aujourd'hui, une autorité contractante burkinabè (ministère, mairie,
établissement public) qui publie un AO fait face à :

| Problème | Conséquence |
|----------|-------------|
| Publication uniquement via DGCMEF (PDF) | Visibilité limitée, peu de soumissionnaires qualifiés |
| Aucune statistique sur ses propres AOs | Impossible de mesurer l'activité marchés |
| Pas de canal direct vers les PME BF | Les marchés attirent peu de candidats compétents |
| Processus de publication lent et papier | Délais, erreurs, double saisie |
| Pas de suivi post-publication | L'AO publié est "oublié" jusqu'au dépouillement |

**Résultat concret :** certains AOs reçoivent 1 ou 2 offres seulement,
faute de visibilité suffisante. L'État ne bénéficie pas de la concurrence.

---

## Ce que NetSync Gov Institutions apporte

### Pour l'autorité contractante
1. **Publication amplifiée** — tout AO publié sur DGCMEF est automatiquement
   relayé sur NetSync Gov avec notifications aux abonnés du secteur concerné
2. **Tableau de bord acheteur** — statistiques sur ses propres AOs :
   nombre de consultations, secteurs actifs, délais moyens
3. **Profil institution public** — page publique de l'institution
   sur gov.netsync.bf avec historique des AOs publiés
4. **Alertes soumissionnaires ciblées** — possibilité de cibler
   manuellement des entreprises qualifiées pour un AO restreint
5. **Rapport d'activité mensuel** — PDF automatique pour la direction

### Pour NetSync Gov
- **Revenus B2G** — abonnement institutionnel mensuel
- **Données enrichies** — les institutions renseignent des métadonnées
  que le parser ne capture pas toujours (montant exact, région, contacts)
- **Légitimité** — des partenariats institutionnels = crédibilité
  auprès des abonnés Pro et des bailleurs
- **Effet réseau** — plus d'institutions → plus de soumissionnaires → plus d'abonnés

---

## Cibles et segmentation

### Segment 1 — Ministères et directions nationales
Exemples : MAERAH, MENA, MSHP, MINEFID, MTDCS
AOs fréquents, budgets importants.
Prix envisagé : **75 000 FCFA/mois** (abonnement institutionnel)

### Segment 2 — Établissements publics et projets
Exemples : PRECEL, PRSA-BF, ACOMOD-B, ARCOP
Projets financés par bailleurs, AOs en anglais parfois.
Prix envisagé : **75 000 FCFA/mois**

### Segment 3 — Collectivités territoriales
Mairies de Ouagadougou, Bobo-Dioulasso, communes rurales.
Budget limité, accompagnement nécessaire.
Prix envisagé : **35 000 FCFA/mois** (tarif collectivité)

### Segment 4 — CCI-BF et chambres professionnelles
Publient leurs propres AOs. Déjà dans nos sources.
Partenariat naturel pour légitimité et données.
Prix : partenariat (échange de données contre visibilité)

---

## Fonctionnalités du MVP

### Inclus
1. **Compte institution** — inscription spécifique avec vérification
2. **Dashboard acheteur** — stats sur ses AOs (vus, secteurs, délais)
3. **Profil public institution** — page gov.netsync.bf/institutions/{slug}
4. **Enrichissement d'AO** — l'institution peut compléter les métadonnées
   d'un AO déjà parsé (contact, DAO disponible, région exacte)
5. **Rapport d'activité** — PDF mensuel auto
6. **Ciblage soumissionnaires** — envoyer une notification à un segment
   d'abonnés qualifiés pour un AO spécifique (payant par notification)

### Hors périmètre MVP
- Publication directe sur NetSync Gov sans passer par DGCMEF
  (complexité juridique — la publication officielle reste DGCMEF)
- Gestion de la procédure de passation (hors scope, c'est SECOP)
- Signature électronique

---

## Modèle économique

| Plan | Prix mensuel | Cible |
|------|-------------|-------|
| Institutionnel standard | 75 000 FCFA | Ministères, EPA, projets |
| Collectivité | 35 000 FCFA | Mairies, communes |
| Partenariat | Échange données | CCI-BF, ARCOP |
| Notification ciblée | 5 000 FCFA/envoi | Toutes institutions |

**Revenus additionnels M6 estimés :**
5 ministères × 75 000 + 3 mairies × 35 000 = 480 000 FCFA/mois

---

## Stratégie d'acquisition institutions

### Approche recommandée
Ne pas prospecter à froid. Utiliser NetSync Gov comme levier :

1. **Montrer les données** — envoyer à chaque institution un rapport
   de ses AOs indexés sur NetSync Gov (données qu'elle n'a pas elle-même)
2. **Proposer le compte gratuit 3 mois** — laisser voir la valeur
3. **Convertir après validation** — une fois le dashboard adopté, proposer l'abonnement

### Canaux
- ARCOP — interlocuteur naturel pour tous les acheteurs publics BF
- DMP (Directions des marchés publics de chaque ministère)
- Bailleurs de fonds (Banque Mondiale, GIZ, PNUD) — ils veulent
  de la transparence sur leurs financements

---

## Nouvelle table PostgreSQL

```sql
CREATE TABLE institutions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom             VARCHAR(255) NOT NULL,
    sigle           VARCHAR(50),
    slug            VARCHAR(100) UNIQUE NOT NULL,
    type_institution VARCHAR(30) CHECK (type_institution IN (
                        'ministere', 'direction', 'etablissement_public',
                        'projet', 'collectivite', 'chambre', 'autre'
                    )),
    secteurs        TEXT[],          -- Secteurs principaux de l'institution
    region          VARCHAR(100),
    email_contact   VARCHAR(255),
    telephone       VARCHAR(30),
    site_web        VARCHAR(255),
    description     TEXT,
    logo_url        TEXT,
    plan            VARCHAR(20) DEFAULT 'gratuit'
                    CHECK (plan IN ('gratuit', 'collectivite', 'institutionnel', 'partenaire')),
    actif           BOOLEAN DEFAULT true,
    verifie         BOOLEAN DEFAULT false,  -- Vérifié par NetSync Gov
    abonne_id       UUID REFERENCES abonnes(id),  -- Compte utilisateur lié
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_institutions_slug  ON institutions(slug);
CREATE INDEX idx_institutions_type  ON institutions(type_institution);
CREATE INDEX idx_institutions_actif ON institutions(actif) WHERE actif = true;

-- Lier les AOs parsés à l'institution
ALTER TABLE appels_offres
    ADD COLUMN IF NOT EXISTS institution_id UUID REFERENCES institutions(id);
```
