# NetSync Gov — Business Model Canvas

## 1. Proposition de valeur

### Problème résolu
Les PME, consultants et bureaux d'études burkinabè ratent des marchés publics
faute d'une veille structurée. Le Quotidien DGCMEF existe mais personne ne
l'agrège, ne le filtre, ni ne l'alerte automatiquement.

### Valeur délivrée
| Pour qui | Valeur |
|---------|--------|
| PME (BTP, IT, Santé) | Ne plus rater aucun AO dans son secteur. Alerte WhatsApp à 07h00. |
| Consultants indépendants | Veille passive → temps libéré pour les dossiers |
| Bureaux d'études | Dashboard équipe + suivi candidatures (plan Équipe) |
| Institutions financières | Données commande publique pour analyse de marché |

### Différenciateurs
1. **Seule plateforme burkinabè** avec alertes WhatsApp automatiques
2. **Historique complet** des AOs (actif inimitable)
3. **Multi-sources** : DGCMEF + UNDP + BM STEP (roadmap)
4. **Paiement Mobile Money** (Orange Money, Moov) — friction zéro

---

## 2. Segments de clientèle

### Segment 1 — PME sectorielles (cœur de cible)
- **Profil** : entreprises de 5 à 50 salariés, BTP, IT, santé, agriculture
- **Taille de marché** : ~8 000 PME formelles à Ouagadougou (source CCI-BF)
- **Adoption réaliste** : 2% → 160 PME abonnées Pro (objectif 12 mois)
- **Plan** : Pro mensuel (15 000 FCFA/mois)
- **Douleur principale** : "Je le découvre trop tard pour préparer un bon dossier"

### Segment 2 — Consultants et indépendants
- **Profil** : experts-comptables, ingénieurs, juristes, formateurs
- **Taille de marché** : ~3 000 consultants actifs BF
- **Adoption réaliste** : 3% → 90 consultants Pro
- **Plan** : Pro mensuel ou annuel
- **Douleur principale** : "Je passe des heures à lire les PDFs moi-même"

### Segment 3 — Bureaux d'études et cabinets
- **Profil** : structures de 3 à 20 personnes, pluridisciplinaires
- **Taille de marché** : ~500 bureaux d'études BF
- **Adoption réaliste** : 5% → 25 équipes
- **Plan** : Équipe (45 000 FCFA/mois)
- **Douleur principale** : "On ne sait jamais qui dans l'équipe a vu quel AO"

### Segment 4 — Expansion (M6+)
- Institutions financières (banques, assurances)
- Agences de développement et ONG internationales
- Grandes entreprises avec département marchés publics
- API clients (ERP, logiciels de gestion)

---

## 3. Canaux d'acquisition

| Canal | Coût | Délai | Potentiel |
|-------|------|-------|-----------|
| WhatsApp groupes professionnels | Gratuit | Immédiat | Élevé (conversion directe) |
| Bouche-à-oreille abonnés satisfaits | Gratuit | 1-3 mois | Très élevé |
| Facebook / LinkedIn | Faible (boosts) | 2-4 semaines | Moyen |
| Partenariats CCI-BF, associations PME | Temps | 3-6 mois | Très élevé (volume) |
| SEO ("appels d'offres Burkina Faso") | Temps | 6-12 mois | Élevé (long terme) |
| Programme partenaires revendeurs | Commission | 3-6 mois | Élevé |

**Règle d'or lancement** : vendre l'alerte concrète, pas la plateforme.
Montrer une vraie notification WhatsApp d'un vrai AO → taux de conversion 3-5x supérieur.

---

## 4. Structure de revenus

### Revenus récurrents (MRR)

| Plan | Prix mensuel | Prix annuel | Cible M12 | MRR M12 |
|------|-------------|-------------|-----------|---------|
| Gratuit | 0 FCFA | — | 500 comptes | 0 |
| Pro | 15 000 FCFA | 144 000 FCFA | 150 abonnés | 2 250 000 FCFA |
| Équipe | 45 000 FCFA | 432 000 FCFA | 25 équipes | 1 125 000 FCFA |

**MRR total cible M12 : 3 375 000 FCFA (~5 150 €)**

### Revenus non récurrents (M6+)

| Source | Prix | Volume annuel | Revenus |
|--------|------|---------------|---------|
| API Business | 25 000 FCFA/mois | 10 clients | 3 000 000 FCFA/an |
| Rapports sectoriels | 50 000 FCFA/rapport | 24 rapports/an | 1 200 000 FCFA/an |
| Licence partenaires | Commission 20% | variable | ~500 000 FCFA/an |

---

## 5. Structure de coûts

### Coûts fixes mensuels (production)

| Poste | Coût mensuel | Notes |
|-------|-------------|-------|
| VPS Hostinger KVM 2 | ~30 000 FCFA | 45$/mois |
| Resend (email) | 0–15 000 FCFA | Gratuit jusqu'à 3 000 emails |
| WhatsApp Business API | ~13 000 FCFA | ~20$/1000 msgs (Meta) |
| Anthropic API (Claude) | ~6 500 FCFA | ~10$/mois fallback parsing |
| Nom de domaine | ~1 000 FCFA | Prorata mensuel |
| **Total charges tech** | **~65 000 FCFA** | |

### Coûts variables

| Poste | Déclencheur | Coût |
|-------|-------------|------|
| WhatsApp messages | +1 abonné Pro WA | ~13 FCFA/message |
| Resend emails | >3 000 emails/mois | ~1 FCFA/email |
| Stockage PDF | +1 quotidien/jour | Négligeable (cold storage) |

### Break-even

```
Break-even = Coûts fixes / Marge unitaire
           = 65 000 / 15 000
           = 4,3 abonnés Pro

→ Break-even réel : 5 abonnés Pro payants
```

**Avec 5 abonnés Pro, NetSync Gov est rentable dès le premier mois.**

---

## 6. Ressources et activités clés

### Ressources clés
- **Pipeline PDF** (code + dataset) — actif technique défensif
- **Base de données historique** — actif inimitable
- **Marque NetSync Gov** — notoriété et confiance
- **Relations institutionnelles** (CCI-BF, DGCMEF) — barrière relationnelle

### Activités clés
- Maintenance quotidienne du pipeline (monitoring + corrections)
- Développement produit (nouvelles fonctionnalités, nouvelles sources)
- Acquisition et rétention abonnés
- Relations institutionnelles et partenariats

### Partenaires clés
- **DGCMEF** — source principale (relation à formaliser)
- **CCI-BF** — canal distribution et légitimité
- **CinetPay** — paiement Mobile Money
- **Meta** — WhatsApp Business API
- **Anthropic** — parsing LLM fallback

