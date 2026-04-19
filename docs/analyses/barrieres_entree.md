# NetSync Gov — Barrières à l'entrée et avantages compétitifs durables

## 1. Barrières techniques (moat technologique)

### 1.1 Pipeline de parsing PDF — le cœur défensif
Le pipeline de traitement du Quotidien DGCMEF est la barrière la plus solide.
Un concurrent qui voudrait répliquer NetSync Gov doit :

- Reverse-engineer la structure variable des PDFs DGCMEF (format change sans préavis)
- Construire un extracteur fiable sur 700+ numéros passés avec des mises en page hétérogènes
- Gérer les cas dégradés : PDFs scannés, tableaux mal alignés, caractères spéciaux wolof/mooré
- Calibrer le fallback LLM (coût + latence + précision) sans historique d'erreurs

**NetSync Gov dispose déjà de ce pipeline opérationnel + les corrections issues des vrais PDFs.**
Chaque jour de production = données d'entraînement supplémentaires que le concurrent n'a pas.

**Actions pour renforcer cette barrière :**
- Versionner chaque numéro DGCMEF indexé avec le hash du PDF source (audit trail)
- Constituer un dataset labelisé d'au moins 500 AOs parsés manuellement (gold standard)
- Entraîner un modèle de classification sectorielle spécifique au contexte burkinabè (pas générique)
- Breveter ou protéger par secret industriel la logique de scoring de confiance

### 1.2 Base de données historique
Chaque jour, NetSync Gov accumule un actif qu'un entrant ne peut pas avoir :
l'historique complet des AOs burkinabè depuis le lancement.

- Recherche tendancielle (secteur X a publié N AOs en 12 mois)
- Profil des autorités contractantes (MAERAH publie 3x/mois, montant moyen 40M FCFA)
- Données de clôture et d'attribution (qui gagne quoi)

**Cet historique est un actif inimitable** — un concurrent qui lance aujourd'hui part de zéro.

**Actions :**
- Archiver systématiquement tous les PDFs sources (stockage cold, ex. Backblaze B2)
- Exposer l'historique comme feature Pro exclusive (accès 12 mois → 24 mois → tout l'historique)
- Construire un moteur de tendances sectorielle basé sur cet historique (rapport mensuel automatisé)

### 1.3 Intégrations multi-sources exclusives
Chaque source ajoutée augmente la valeur et le coût de réplication :

| Source | Statut | Difficulté réplication |
|--------|--------|----------------------|
| DGCMEF Quotidien | ✓ Opérationnel | Moyenne (PDF public) |
| CCI-BF | Roadmap M2 | Faible (scraping HTML) |
| Banque Mondiale STEP | Roadmap M2 | Faible (API REST) |
| UNDP Procurement | Roadmap M2 | Faible (flux RSS) |
| UEMOA / BCEAO | Roadmap M6 | Élevée (accès restreint) |
| Marchés attribués (DGCMEF) | Roadmap M6 | Très élevée (données non structurées) |

**Objectif : être la seule plateforme qui agrège toutes les sources.
Un concurrent qui couvre une source ne peut pas proposer la même couverture.**

---

## 2. Barrières relationnelles (réseau et données)

### 2.1 Effets de réseau (faibles mais réels)
NetSync Gov n'est pas un réseau social, mais des effets de réseau existent :

- **Recommandations** : un abonné Pro satisfait recommande à 2-3 contacts dans son secteur
- **Groupes WhatsApp** : les alertes partagées dans les groupes professionnels créent de la visibilité organique
- **Réputation** : être "la plateforme des marchés publics BF" est une position de marque défendable

### 2.2 Données comportementales exclusives
Chaque interaction abonné génère des données qu'un concurrent n'a pas :

- Quels secteurs sont les plus recherchés
- Quels AOs génèrent le plus de clics (signal de qualité de parsing)
- Quel type d'alerte convertit le mieux (email vs WhatsApp, timing)
- Quels abonnés ouvrent leurs emails vs lisent leurs WA

**Ces données alimentent l'amélioration continue du produit et du scoring.**

### 2.3 Partenariats institutionnels (barrière long terme)
**Objectif M6-M12 :** nouer des partenariats avec :

- **CCI-BF** : accord de diffusion officielle, logo "Partenaire CCI-BF"
- **ARCOP** (Autorité de Régulation de la Commande Publique) : validation officielle
- **Cabinets comptables et juridiques** : revente de licences Équipe à leurs clients PME
- **Banques et institutions financières** : abonnements pour suivi de la commande publique

**Un accord institutionnel est une barrière à l'entrée quasi-infranchissable
pour un concurrent sans réseau local.**

---

## 3. Option d'intégration continue (API et écosystème)

### 3.1 API publique NetSync Gov (M6+)
Ouvrir une API permet de transformer NetSync Gov en infrastructure plutôt qu'en simple produit.

```yaml
# Plans API
developer:
  prix: gratuit
  quotas: 100 req/jour
  données: AOs des 7 derniers jours
  usage: test, intégration initiale

business:
  prix: 25 000 FCFA/mois
  quotas: 10 000 req/jour
  données: temps réel + historique complet
  usage: ERP, logiciels métier, intégration comptable

enterprise:
  prix: sur devis
  quotas: illimité
  données: webhook temps réel + données attributions
  usage: grandes entreprises, institutions financières
```

**Chaque intégration API crée un coût de migration élevé pour l'abonné.**

### 3.2 Intégrations tierces prioritaires

**ERP et logiciels de gestion burkinabè :**
- Sage (utilisé par de nombreuses PME BF)
- Saari Comptabilité (logiciel local dominant)
- Intégration simple : webhook → email vers le logiciel

**Outils de productivité :**
- Google Sheets (export automatique des AOs du jour)
- Notion (base de données synchronisée)
- WhatsApp Business API (alertes pour cabinets avec plusieurs clients)

### 3.3 Programme partenaires (revendeurs)
Permettre à des tiers de revendre des abonnements NetSync Gov :

```
Partenaire (cabinet, association)
    ↓ revend abonnements au prix public
    ↓ reçoit 20% de commission
    ↓ gère ses clients depuis un dashboard dédié
```

**Cibles :** cabinets comptables, associations de PME, CCI régionales.

### 3.4 Innovation continue — roadmap produit

**Cadence d'innovation recommandée :**

| Fréquence | Type | Exemple |
|-----------|------|---------|
| Hebdomadaire | Amélioration parsing | Meilleure détection montants |
| Mensuel | Nouvelle fonctionnalité | Export CSV, nouvelles sources |
| Trimestriel | Fonctionnalité majeure | Dashboard équipe, scoring IA |
| Semestriel | Expansion géographique | Côte d'Ivoire, Mali, Sénégal |

**Principe : publier les nouveautés.** Chaque mise à jour est une opportunité
de communication vers les abonnés et les prospects.

---

## 4. Gouvernance de la plateforme

### 4.1 Cadre juridique — Burkina Faso

#### Structure légale recommandée
**Créer une SARL (Société à Responsabilité Limitée) au Burkina Faso :**

- Dénomination : **NetSync Labs SARL** ou **NetSync Africa SARL**
- Capital minimum : 1 000 000 FCFA
- Siège social : Ouagadougou
- Objet : édition de logiciels et services numériques, veille économique

**Pourquoi une structure locale ?**
- Crédibilité auprès des institutions burkinabè (ARCOP, CCI-BF, DGCMEF)
- Eligibilité aux marchés publics (ironie bienveillante)
- Conformité fiscale (TVA, IS, patente)
- Protection des actifs intellectuels (dépôt OAPI)

#### Protection de la propriété intellectuelle
- **Marque "NetSync Gov"** : dépôt OAPI (Organisation Africaine de la Propriété Intellectuelle)
  - Coût : ~150 000 FCFA pour 10 ans, couvrant les 17 pays membres dont le BF
  - Classes : 35 (services informatiques), 38 (télécommunications), 42 (logiciels)
- **Nom de domaine** : gov.netsync.bf déjà identifié
- **Code source** : licence propriétaire (pas open source), accès restreint

#### Conformité fiscale
- TVA applicable sur les abonnements (18% au BF)
- Déclaration mensuelle, télépaiement DGI
- Facturation électronique avec numéro de contribuable

### 4.2 Politique de données et vie privée

#### Ce que NetSync Gov collecte
| Donnée | Usage | Durée de conservation |
|--------|-------|----------------------|
| Email, prénom, nom | Authentification, alertes | Durée de l'abonnement + 1 an |
| Numéro WhatsApp | Alertes | Durée de l'abonnement |
| Comportement plateforme | Amélioration produit (anonymisé) | 24 mois glissants |
| Historique de paiement | Conformité fiscale | 10 ans (obligation légale) |

#### Politique de suppression
- Droit à l'effacement : suppression dans les 30 jours sur demande
- Export des données : disponible dans les paramètres du compte
- Pas de revente à des tiers (jamais, voir position Anthropic sur les pubs)

#### Hébergement des données
- Données hébergées en Europe (VPS Hostinger EU) ou en Afrique si disponible
- Chiffrement at rest (PostgreSQL) et in transit (TLS 1.3)
- Accès administrateur logué et auditable

### 4.3 Politique éditoriale et responsabilité

#### Ce que NetSync Gov publie
NetSync Gov est un agrégateur, pas un éditeur.
Il ne crée pas le contenu, il indexe des sources officielles publiques.

**Règles éditoriales :**
- Seules les sources officielles (DGCMEF, UNDP, BM STEP, CCI-BF) sont indexées
- Aucun AO n'est modifié, seulement structuré
- En cas d'erreur de parsing, l'AO est marqué "à vérifier" et le PDF source est accessible
- Un bouton "Signaler une erreur" permet aux abonnés de corriger les données

#### Limites de responsabilité
Inclure dans les CGU :
- NetSync Gov ne garantit pas l'exhaustivité des AOs publiés
- Les données affichées sont celles des sources officielles ; NetSync Gov décline toute responsabilité en cas d'erreur à la source
- L'abonné doit vérifier les informations sur le site officiel avant toute candidature

### 4.4 Impact social et positionnement éthique

#### Pourquoi c'est important au Burkina Faso
La commande publique burkinabè souffre d'un déficit d'accès à l'information :
- Les grandes entreprises ont des agents de veille dédiés
- Les PME et indépendants n'ont pas les moyens de cette veille
- Résultat : les marchés publics sont capturés par un petit nombre d'acteurs bien connectés

**NetSync Gov démocratise l'accès à l'information de la commande publique.**
C'est à la fois un argument commercial et un argument éthique fort.

#### Positionnement RSE
- **Prix accessible** : 15 000 FCFA/mois = délibérément bas pour inclure les PME
- **Plan gratuit** : 3 AOs/jour pour les très petites structures
- **Transparence** : rapport mensuel public sur le nombre d'AOs indexés par source
- **Partenariat associations** : tarif préférentiel pour les associations de PME (−30%)

#### Risques sociaux à anticiper
| Risque | Probabilité | Mitigation |
|--------|-------------|------------|
| Accusation de favoritisme envers certains AOs | Faible | Algorithme de tri transparent (date), pas de mise en avant payante |
| Utilisation par des acteurs corrompus | Faible | NetSync Gov n'intervient pas dans l'attribution |
| Dépendance excessive à DGCMEF | Moyenne | Diversification des sources (objectif M2) |
| Blocage d'accès par DGCMEF | Très faible | Données publiques + accord institutionnel en cours |

