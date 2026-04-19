# Étape 5 — Tests et vérifications avant le lancement

> Prérequis : étape 4 terminée, tous les containers en healthy/running.
> Durée : 30 à 60 minutes.
> Ne pas passer au lancement bêta avant que tous les tests critiques soient verts.

---

## Test 1 — API Health Check
```bash
curl https://api.gov.netsync.bf/health
# Résultat attendu :
# {"status": "ok", "service": "netsync-gov-api", "version": "1.0.0"}
```
✅ Vert si status = "ok"

---

## Test 2 — Frontend accessible
```bash
curl -I https://gov.netsync.bf
# Résultat attendu : HTTP/2 200
```
Ouvrir https://gov.netsync.bf dans un navigateur → la page doit s'afficher.
✅ Vert si la page de connexion s'affiche

---

## Test 3 — Inscription et connexion
1. Aller sur https://gov.netsync.bf
2. Créer un compte de test (utiliser ton vrai email)
3. Vérifier que l'email de bienvenue est reçu
4. Se connecter → accéder au dashboard
✅ Vert si connexion réussie et email reçu

---

## Test 4 — Pipeline PDF (premier run manuel)
```bash
# Sur le VPS
cd /opt/netsync_gov

# Déclencher le pipeline manuellement
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec api python3 -c "
from pipeline.pipeline import run_pipeline
result = run_pipeline()
print('Résultat:', result)
"

# Vérifier que des AOs ont été indexés
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec db psql -U netsync -d netsync_gov \
  -c "SELECT COUNT(*) FROM appels_offres;"
# Doit afficher un nombre > 0
```
✅ Vert si COUNT > 0

---

## Test 5 — Email d'alerte
```bash
# Envoyer un email de test
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec api python3 -c "
from alertes_netsync_gov.email_sender import ResendClient
from alertes_netsync_gov.email_templates import render_bienvenue
client = ResendClient()
subject, html = render_bienvenue('Test', 'pro', ['informatique'])
result = client.send('TON_EMAIL@gmail.com', subject, html)
print('Résultat:', result)
"
```
✅ Vert si email reçu dans la boite mail (vérifier les spams)

---

## Test 6 — Paiement CinetPay sandbox
1. Se connecter sur https://gov.netsync.bf avec ton compte de test
2. Aller sur /pricing → cliquer "Choisir Pro"
3. Sélectionner Orange Money
4. Utiliser le numéro de test CinetPay : `07000000`
5. Vérifier que le plan passe à "Pro" dans le dashboard

✅ Vert si plan Pro activé après paiement sandbox

---

## Test 7 — Webhook CinetPay
```bash
# Simuler un webhook depuis le dashboard CinetPay
# Dashboard CinetPay → Paramètres → Webhook → "Tester le webhook"
# Ou manuellement :

curl -X POST https://api.gov.netsync.bf/api/v1/paiements/webhook \
  -H "Content-Type: application/json" \
  -d '{"cpm_trans_id": "TEST-001", "cpm_result": "00"}'

# Résultat attendu :
# {"status": "ignored", "transaction_id": "TEST-001"}
# (ignored car transaction inconnue — c'est normal pour ce test)
```
✅ Vert si réponse HTTP 200 reçue

---

## Test 8 — Celery et tâches planifiées
```bash
# Vérifier que Celery worker fonctionne
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec worker celery -A pipeline.celery_app inspect active

# Vérifier que Celery beat fonctionne
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml logs beat | tail -20
# Doit afficher des lignes "Scheduler: Sending due task..."
```
✅ Vert si les deux répondent sans erreur

---

## Test 9 — Monitoring healthcheck
```bash
# Lancer le script de monitoring
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec api python3 13_Deploiement_Docker_VPS/monitoring/healthcheck.py

# Résultat attendu :
# [OK] API FastAPI — {"status": "ok"}
# [OK] PostgreSQL — X AOs en base
# [OK] Redis — PONG
# [OK] Pipeline PDF — Dernier run : JJ/MM HH:MM (success)
# [OK] SSL Certificate — Expire dans X jours
```
✅ Vert si 0 FAILED dans le rapport

---

## Test 10 — SSL et sécurité
```bash
# Vérifier le score SSL (depuis ton navigateur)
# Aller sur : https://www.ssllabs.com/ssltest/analyze.html?d=gov.netsync.bf
# Score attendu : A ou A+

# Vérifier HSTS
curl -I https://gov.netsync.bf | grep "Strict-Transport"
# Doit afficher : strict-transport-security: max-age=31536000; includeSubDomains
```
✅ Vert si score SSL A minimum

---

## Tableau de bord GO / NO-GO

| Test | Critique | Statut |
|------|---------|--------|
| API Health Check | BLOQUANT | ⬜ |
| Frontend accessible | BLOQUANT | ⬜ |
| Inscription + email bienvenue | BLOQUANT | ⬜ |
| Pipeline indexe des AOs | BLOQUANT | ⬜ |
| Email alerte reçu | BLOQUANT | ⬜ |
| Paiement CinetPay sandbox | BLOQUANT | ⬜ |
| Webhook CinetPay répond 200 | BLOQUANT | ⬜ |
| Celery worker + beat actifs | BLOQUANT | ⬜ |
| Monitoring healthcheck 0 FAILED | BLOQUANT | ⬜ |
| SSL score A minimum | BLOQUANT | ⬜ |
| WhatsApp templates approuvés | NON BLOQUANT | ⬜ |

**Règle GO : tous les 10 tests BLOQUANTS cochés → lancement bêta autorisé.**

**Si tout est vert → passer à l'étape 6 (WhatsApp) et commencer le recrutement des bêta-testeurs.**
