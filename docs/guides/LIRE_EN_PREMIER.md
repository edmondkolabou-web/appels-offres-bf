# NetSync Gov — Guide de déploiement pas à pas
## De zéro à gov.netsync.bf en production

---

## Vue d'ensemble des 6 étapes

| Étape | Action | Durée estimée | Bloquant ? |
|-------|--------|---------------|------------|
| 1 | Créer les 4 comptes et récupérer les clés | 2–4h (+ 24-72h KYC CinetPay) | Oui |
| 2 | Commander VPS + configurer DNS | 1h (+ propagation DNS 30 min) | Oui |
| 3 | Mettre le code sur le VPS + remplir .env | 30 min | Oui |
| 4 | Lancer deploy.sh + migrations + SSL | 20 min | Oui |
| 5 | Tests et vérifications | 1h | Oui |
| 6 | Soumettre templates WhatsApp Meta | 30 min (+ 48-72h approbation) | Non bloquant |

**Durée totale : 1 à 3 jours** (selon le KYC CinetPay et l'approbation Meta)

---

## Ordre recommandé

Commencer par CinetPay en PREMIER (KYC = goulot d'étranglement).
En parallèle : Resend + Meta + Anthropic (moins d'1h chacun).
Soumettre les templates WhatsApp dès que le compte Meta est créé.

---

## Fichiers dans ce dossier

- `etape_1_comptes.md` — Les 4 comptes à créer et les clés à récupérer
- `etape_2_vps_dns.md` — Commander le VPS et configurer le DNS
- `etape_3_code_env.md` — Mettre le code sur le VPS et remplir .env.production
- `etape_4_deploiement.md` — Lancer le déploiement Docker + SSL
- `etape_5_tests.md` — Vérifier que tout fonctionne
- `etape_6_whatsapp.md` — Soumettre les templates WhatsApp Meta
- `env_production_template.txt` — Template complet du fichier .env.production
- `commandes_utiles.md` — Référence rapide des commandes fréquentes

