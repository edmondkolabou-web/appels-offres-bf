# NetSync Gov Intelligence — Analyse du besoin

## Le problème

NetSync Gov accumule chaque jour un actif unique : l'historique structuré
de TOUS les appels d'offres publiés au Burkina Faso.

Personne ne transforme ces données en intelligence actionnable.

Aujourd'hui, une PME qui veut répondre à la question :
**"Est-ce que le MAERAH publie souvent des AOs informatique ?
Quel est le montant moyen ? Combien de candidats se positionnent ?"**

...n'a aucune réponse. Elle soumissionne à l'aveugle.

---

## Ce que les données permettent de calculer

Avec 6 mois de pipeline en production, NetSync Gov dispose de :

| Donnée disponible | Usage Intelligence |
|---|---|
| Secteur de chaque AO | Tendances par secteur |
| Autorité contractante | Profil de chaque ministère |
| Montant estimé | Fourchettes moyennes |
| Date publication → clôture | Délais moyens par type |
| Type de procédure | Répartition ouvert / DPX / AMI |
| Source (DGCMEF, UNDP, BM) | Part de marché par bailleur |
| Statut (ouvert / clôturé / attribué) | Taux d'attribution |

---

## Les 5 questions auxquelles Intelligence répond

### 1. "Quel secteur est le plus actif ?"
→ Classement des secteurs par volume d'AOs et montant total

### 2. "Quelle autorité contractante publie le plus ?"
→ Top 10 des ministères et agences les plus actifs

### 3. "Quel est le bon moment pour candidater ?"
→ Courbe de publication par mois/semaine (saisonnalité budgétaire)

### 4. "À quoi ressemble un marché informatique typique au BF ?"
→ Montant médian, délai moyen, type de procédure dominant

### 5. "Est-ce que mon secteur croît ?"
→ Évolution du volume d'AOs sur 6/12/24 mois

---

## Cibles

### Cible 1 — PME soumissionnaires (Plan Pro)
Elles veulent savoir où concentrer leurs efforts.
"Est-ce que ça vaut le coup de candidater aux AOs MAERAH ?"

### Cible 2 — Cabinets et institutions financières
Rapports mensuels sur la commande publique BF.
Valeur : donnée de marché structurée inexistante ailleurs.
Prix : 50 000 FCFA/rapport ou abonnement 35 000 FCFA/mois.

### Cible 3 — Bailleurs et agences de développement
UNDP, GIZ, ambassades qui financent des projets BF ont besoin
de comprendre la commande publique locale.

---

## Périmètre MVP

### Inclus
1. **Dashboard tendances** — graphiques interactifs par secteur/période
2. **Profil autorité contractante** — fiche par ministère/agence
3. **Rapport mensuel automatique** — PDF généré le 1er de chaque mois
4. **API stats** — endpoints publics (rate-limited) pour intégrateurs
5. **Alertes tendances** — "Ton secteur a +30% d'AOs ce mois"

### Hors périmètre
- Données d'attribution (pas encore disponibles en masse)
- Analyse des entreprises attributaires
- Comparaison avec d'autres pays

---

## Modèle économique

| Offre | Prix | Cible |
|---|---|---|
| Dashboard (inclus Plan Pro) | Inclus | PME abonnées |
| Rapport mensuel PDF | 50 000 FCFA/rapport | Cabinets, institutions |
| Abonnement rapports | 35 000 FCFA/mois | Abonnés récurrents |
| API stats Business | 25 000 FCFA/mois | Développeurs, ERP |

**Revenus additionnels estimés M6 : 500 000 à 1 500 000 FCFA/mois**
(10 cabinets × 50 000 FCFA + 5 API × 25 000 FCFA)
