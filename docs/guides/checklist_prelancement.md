# NetSync Gov — Checklist Pré-Lancement

## 1. Infrastructure

### VPS Hostinger
- [ ] VPS commandé (plan KVM 2 minimum : 2 vCPU / 8 GB RAM / 100 GB SSD)
- [ ] Ubuntu 22.04 LTS installé
- [ ] Accès SSH configuré (clé publique uniquement, pas de mot de passe)
- [ ] Ports 22, 80, 443 ouverts dans le panneau Hostinger
- [ ] UFW activé et configuré

### DNS
- [ ] Domaine `gov.netsync.bf` enregistré
- [ ] Enregistrement A : `gov.netsync.bf` → IP VPS
- [ ] Enregistrement A : `api.gov.netsync.bf` → IP VPS
- [ ] Propagation DNS vérifiée (`dig gov.netsync.bf`)

### SSL
- [ ] Certificat Let's Encrypt obtenu via Certbot
- [ ] Renouvellement automatique configuré (cron ou certbot container)
- [ ] HTTPS vérifié sur `gov.netsync.bf` et `api.gov.netsync.bf`

---

## 2. Base de données

- [ ] PostgreSQL 15 démarré et healthcheck vert
- [ ] Extensions créées : `uuid-ossp`, `unaccent`, `pg_trgm`
- [ ] Migrations Alembic exécutées (`alembic upgrade head`)
- [ ] Index GIN créé sur `search_vector` (appels_offres)
- [ ] Index GIN créé sur `secteurs` (preferences_alertes)
- [ ] Trigger `update_ao_search_vector` actif
- [ ] Backup automatique configuré (cron `pg_dump` quotidien)

---

## 3. Variables d'environnement

### Obligatoires avant lancement
- [ ] `DB_PASSWORD` — mot de passe fort (min 32 chars)
- [ ] `REDIS_PASSWORD` — mot de passe fort
- [ ] `JWT_SECRET_KEY` — chaîne aléatoire (min 64 chars)
- [ ] `RESEND_API_KEY` — clé API Resend obtenue sur resend.com
- [ ] `RESEND_FROM_EMAIL` — `alertes@gov.netsync.bf` (domaine vérifié dans Resend)
- [ ] `CINETPAY_SITE_ID` — obtenu sur le dashboard CinetPay
- [ ] `CINETPAY_API_KEY` — obtenu sur le dashboard CinetPay
- [ ] `CINETPAY_SECRET_KEY` — clé secrète pour la validation webhook
- [ ] `ADMIN_EMAIL` — email admin pour les alertes monitoring
- [ ] `ADMIN_EMAILS` — liste des emails admin (séparés par virgule)

### WhatsApp (après approbation Meta)
- [ ] `WHATSAPP_API_TOKEN` — token Meta Cloud API
- [ ] `WHATSAPP_PHONE_ID` — ID du numéro WhatsApp Business
- [ ] `WHATSAPP_WABA_ID` — ID du compte WhatsApp Business

### Optionnel (avec dégradation gracieuse si absent)
- [ ] `ANTHROPIC_API_KEY` — Claude API pour le fallback parsing
- [ ] `SENTRY_DSN` — monitoring des erreurs Sentry

---

## 4. Services Docker

```bash
# Vérifier que tous les services sont UP
docker compose -f deploy/docker-compose.prod.yml ps
```

- [ ] `netsync_db` — status: healthy
- [ ] `netsync_redis` — status: healthy
- [ ] `netsync_api` — status: healthy
- [ ] `netsync_worker` — status: running
- [ ] `netsync_beat` — status: running
- [ ] `netsync_frontend` — status: running
- [ ] `netsync_nginx` — status: running

---

## 5. Pipeline PDF DGCMEF

- [ ] Premier run manuel réussi : `python pipeline.py`
- [ ] Au moins un Quotidien DGCMEF indexé en base
- [ ] AOs visibles dans l'interface (`/api/v1/aos`)
- [ ] Search vector fonctionnel (test requête full-text)
- [ ] Log pipeline visible dans `pipeline_logs`
- [ ] Celery beat actif (vérifier `0 7 * * 1-5`)

```bash
# Test manuel pipeline
docker compose exec api python -c "
from pipeline import run_pipeline
result = run_pipeline.delay()
print('Task:', result.id)
"
```

---

## 6. Alertes email

- [ ] Domaine `gov.netsync.bf` vérifié dans Resend (enregistrement SPF/DKIM/DMARC)
- [ ] Email de test envoyé depuis `alertes@gov.netsync.bf`
- [ ] Email de bienvenue testé sur une adresse réelle
- [ ] Template "Nouvel AO" testé
- [ ] Template "Rappel J-3" testé
- [ ] Email non reçu dans les spams (vérifier score SpamAssassin)

```bash
# Test email manuel
docker compose exec api python -c "
from alertes_netsync_gov.email_sender import ResendClient
from alertes_netsync_gov.email_templates import render_bienvenue
client = ResendClient()
subject, html = render_bienvenue('Test', 'pro', ['informatique'])
result = client.send('ton_email@test.com', subject, html)
print(result)
"
```

---

## 7. Paiement CinetPay

- [ ] Compte CinetPay actif et vérifié (KYC)
- [ ] Test paiement en sandbox réussi (Orange Money test)
- [ ] Webhook configuré dans le dashboard CinetPay : `https://api.gov.netsync.bf/api/v1/paiements/webhook`
- [ ] Webhook testé avec l'outil de test CinetPay
- [ ] Activation plan Pro vérifiée en sandbox

---

## 8. WhatsApp (si templates approuvés)

- [ ] Les 3 templates approuvés par Meta
- [ ] Test envoi `netsync_bienvenue` sur numéro réel
- [ ] Test envoi `netsync_nouvel_ao` sur numéro réel
- [ ] Test envoi `netsync_rappel_cloture` sur numéro réel
- [ ] Numéro sender vérifié dans les "Trusted Businesses" Meta

---

## 9. Sécurité finale

```bash
# Lancer l'audit de sécurité
python consolidation_netsync_gov/security_audit.py
```

- [ ] `security_audit.py` — 0 FAILED
- [ ] `.env.production` non commité (vérifier `git status`)
- [ ] `.gitignore` contient `.env*`
- [ ] Accès SSH par clé uniquement (mot de passe désactivé)
- [ ] `fail2ban` installé et configuré pour SSH
- [ ] Logs accessibles : `docker compose logs -f`

---

## 10. Tests avant ouverture

- [ ] `pytest consolidation_netsync_gov/test_integration_api.py` — 0 erreur
- [ ] `pytest alertes_netsync_gov/test_alertes.py` — 0 erreur
- [ ] `pytest paiement_netsync_gov/test_paiement.py` — 0 erreur
- [ ] Test parcours complet : inscription → configuration alerte → réception alerte
- [ ] Test freemium : vérifier la limite à 3 AO/jour pour un compte gratuit
- [ ] Test paiement : inscription Pro → alerte WhatsApp → accès illimité

---

## 11. Monitoring actif

- [ ] `healthcheck.py` en cron : `*/5 * * * * python /opt/netsync_gov/deploy/monitoring/healthcheck.py`
- [ ] Email admin configuré pour recevoir les alertes monitoring
- [ ] Uptime Kuma ou Statuspage configuré (optionnel)

---

## 12. Go / No-Go

| Critère | Poids | Statut |
|---------|-------|--------|
| Pipeline tourne et indexe les AOs | Bloquant | ⬜ |
| Email fonctionne (template AO) | Bloquant | ⬜ |
| Paiement CinetPay en sandbox OK | Bloquant | ⬜ |
| SSL valide sur les 2 domaines | Bloquant | ⬜ |
| 0 erreur tests intégration | Bloquant | ⬜ |
| WhatsApp templates approuvés | Non bloquant | ⬜ |
| Monitoring actif | Non bloquant | ⬜ |

**Règle Go** : tous les critères "Bloquant" cochés → lancement autorisé.
