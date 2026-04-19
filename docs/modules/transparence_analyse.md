# NetSync Gov Transparence — Analyse du besoin

## Le problème de fond

La Banque Mondiale dans son rapport MAPS 2022 documente explicitement :
> "Il n'existe pas encore de site d'information unique mettant à la disposition
> du public des informations exhaustives et à jour sur la passation des marchés publics."

Ce vide a une conséquence directe : la commande publique burkinabè
est peu lisible pour les citoyens, la société civile, les journalistes
et les bailleurs de fonds.

**Les informations existent — elles sont publiées dans le Quotidien DGCMEF.**
Mais dispersées dans 714+ PDFs non indexés, illisibles pour le grand public.

---

## Ce que Transparence rend visible

### Données déjà disponibles dans NetSync Gov

Le pipeline indexe depuis le lancement :
- Tous les **AOs publiés** avec autorité, secteur, montant estimé
- Les **résultats provisoires** publiés dans le Quotidien
- Les **attributions définitives** publiées dans le Quotidien

En plus, le Quotidien DGCMEF publie aussi les **résultats d'attribution**
(entreprise attributaire, montant final, date de signature).
Ces données ne sont pas encore parsées par NetSync Gov — c'est l'extension clé.

---

## Les 4 pages publiques de Transparence

### 1. Portail public — accessible sans inscription
Page web publique, sans auth, avec :
- Moteur de recherche AOs (full-text)
- Filtres secteur, autorité, période
- Fiche de chaque AO avec toutes les métadonnées
- Lien vers le PDF source officiel DGCMEF

**Objectif** : que journalistes, ONG, citoyens puissent chercher
un AO précis ou une autorité contractante sans créer de compte.

### 2. Tableau des attributions
**Nouveau** : extraire et afficher les marchés attribués publiés dans le Quotidien.

Colonnes :
- Entreprise attributaire
- Autorité contractante
- Titre du marché
- Montant attribué
- Date de signature
- Source (numéro du Quotidien)

### 3. Carte des marchés
Visualisation cartographique des AOs et marchés attribués par région du BF
(Ouagadougou, Bobo-Dioulasso, Koudougou, Banfora, Dédougou…)

### 4. API ouverte (Open Data)
Endpoints publics documentés, rate-limited, permettant à la société civile
et aux développeurs tiers de consommer les données.

---

## Utilisateurs cibles (tous gratuits)

| Cible | Besoin |
|-------|--------|
| Journalistes d'investigation | Chercher un marché attribué à une entreprise précise |
| ONG et société civile | Surveiller un secteur (santé, éducation) |
| Bailleurs de fonds | Vérifier l'exécution de leurs financements |
| Chercheurs et universités | Données pour études sur la commande publique BF |
| Citoyens | Savoir qui a eu le marché de construction de leur école |
| ARCOP | Données complémentaires pour le contrôle |

---

## Valeur stratégique pour NetSync Gov

**Transparence est entièrement gratuit et public.**

C'est un investissement stratégique, pas un produit payant :

1. **SEO** : chaque fiche AO et attribution est une page indexée par Google
   → trafic organique vers NetSync Gov
2. **Notoriété** : positionnement "référence de la commande publique BF"
3. **Partenariats** : levier pour obtenir des partenariats ARCOP, Banque Mondiale, GIZ
4. **Crédibilité** : légitimité auprès des institutions et des abonnés Pro
5. **Données** : les requêtes du portail public enrichissent les données d'usage

---

## Nouveau parsing nécessaire — Résultats d'attribution

Le Quotidien DGCMEF publie aussi les attributions. Exemple de bloc :

```
RÉSULTATS D'ATTRIBUTION
N° 2026-001/MAERAH/SG/DMP
Objet : Acquisition matériel informatique PRECEL
Attributaire : Société Informatique de l'Ouest (SIO)
Montant : 38 750 000 FCFA TTC
Date signature : 5 mars 2026
```

**À ajouter au pipeline parser.py :**
- Détection des blocs "RÉSULTATS D'ATTRIBUTION"
- Extraction : attributaire, montant final, date signature
- Lien avec l'AO source dans la BDD

---

## Nouvelle table PostgreSQL

```sql
CREATE TABLE attributions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ao_id             UUID REFERENCES appels_offres(id),
    attributaire      VARCHAR(255) NOT NULL,
    montant_final     BIGINT,
    date_signature    DATE,
    source_quotidien  INTEGER,
    notes             TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_attributions_ao          ON attributions(ao_id);
CREATE INDEX idx_attributions_attributaire ON attributions(attributaire);
CREATE INDEX idx_attributions_date        ON attributions(date_signature);
```
