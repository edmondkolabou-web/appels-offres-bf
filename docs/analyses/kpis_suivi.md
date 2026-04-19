# NetSync Gov — KPIs et tableau de bord lancement

## Métriques hebdomadaires (J0 → J90)

### Acquisition
| KPI | Semaine 1 | Semaine 4 | Semaine 12 |
|-----|-----------|-----------|------------|
| Inscrits cumulés | 10 (bêta) | 50 | 200 |
| Inscrits Pro | 0 | 5 | 30 |
| MRR (FCFA) | 0 | 75 000 | 450 000 |
| CAC moyen | — | gratuit (WhatsApp) | < 5 000 FCFA |

### Engagement
| KPI | Cible |
|-----|-------|
| Taux ouverture email | > 45% |
| Taux clic email → plateforme | > 15% |
| Taux lecture alerte WhatsApp | > 70% (lu dans les 2h) |
| DAU / MAU (rétention) | > 40% |
| NPS (enquête J30) | > 50 |

### Pipeline
| KPI | Cible quotidienne |
|-----|-------------------|
| AOs indexés | ≥ 10 (jours ouvrable) |
| Délai publication → alerte | < 90 minutes |
| Taux succès pipeline | > 95% |
| Alertes envoyées / AO | variable selon abonnés |

### Paiement
| KPI | Cible mois 1 | Cible mois 3 |
|-----|-------------|-------------|
| Taux conversion gratuit → Pro | > 10% | > 15% |
| Taux de churn mensuel | < 5% | < 3% |
| LTV estimé (Pro 12 mois) | 180 000 FCFA | — |
| Revenus mois 1 | 150 000 FCFA | 600 000 FCFA |

## Requêtes SQL de suivi (à exécuter hebdomadairement)

```sql
-- Abonnés par plan
SELECT plan, COUNT(*) as nb, DATE_TRUNC('week', created_at) as semaine
FROM abonnes
GROUP BY plan, semaine
ORDER BY semaine DESC;

-- Alertes envoyées cette semaine
SELECT canal, statut, COUNT(*) as nb
FROM envois_alertes
WHERE envoye_le >= NOW() - INTERVAL '7 days'
GROUP BY canal, statut;

-- AOs publiés et indexés
SELECT secteur, COUNT(*) as nb_ao
FROM appels_offres
WHERE date_publication >= NOW() - INTERVAL '7 days'
GROUP BY secteur
ORDER BY nb_ao DESC;

-- MRR actuel
SELECT
  SUM(CASE WHEN plan = 'pro' THEN 15000 ELSE 0 END) +
  SUM(CASE WHEN plan = 'equipe' THEN 45000 ELSE 0 END) AS mrr_fcfa
FROM abonnes
WHERE plan != 'gratuit'
  AND (plan_expire_le IS NULL OR plan_expire_le >= CURRENT_DATE);

-- Taux conversion
SELECT
  COUNT(*) FILTER (WHERE plan = 'gratuit') AS gratuits,
  COUNT(*) FILTER (WHERE plan != 'gratuit') AS payants,
  ROUND(
    COUNT(*) FILTER (WHERE plan != 'gratuit') * 100.0 / NULLIF(COUNT(*), 0),
    1
  ) AS taux_conversion_pct
FROM abonnes WHERE actif = true;
```

## Seuil de viabilité

- **Break-even** : 34 abonnés Pro (34 × 15 000 = 510 000 FCFA/mois)
  - Coûts estimés : VPS 50$/mois + Resend 0$ (gratuit jusqu'à 3 000 emails) + WhatsApp API ~20$/mois
  - Total charges : ~70 000 FCFA/mois
  - **Break-even réel : ~5 abonnés Pro**
- **Objectif mois 3** : 40 Pro → 600 000 FCFA MRR → rentable
