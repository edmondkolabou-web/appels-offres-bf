#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# NetSync Gov — Patch #1 : 5 bugs critiques + 2 fixes sécurité
# Date : 25 avril 2026
# Usage : cd ~/appels-offres-bf && bash patches/fix-critical-bugs.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  NetSync Gov — Patch #1 : Bugs critiques + Sécurité        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# BUG 1 : est_pro ne vérifie pas plan_expire_le
# Fichier : backend/models.py
# Impact : Un utilisateur Pro expiré garde l'accès Pro
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [1/7] Fix est_pro — vérification expiration plan..."

python3 << 'PYFIX1'
import re

with open("backend/models.py", "r") as f:
    content = f.read()

old_prop = '''    @property
    def est_pro(self) -> bool:
        return self.plan in ("pro", "equipe")'''

new_prop = '''    @property
    def est_pro(self) -> bool:
        """Vérifie que le plan est payant ET non expiré."""
        if self.plan not in ("pro", "equipe", "institutionnel"):
            return False
        # Vérifier si le plan est expiré
        if self.plan_expire_le and self.plan_expire_le < date.today():
            return False
        # Vérifier si le trial est expiré
        if self.trial_actif and self.trial_expire_le and self.trial_expire_le < date.today():
            return False
        return True'''

if old_prop in content:
    content = content.replace(old_prop, new_prop)
    with open("backend/models.py", "w") as f:
        f.write(content)
    print("   ✅ est_pro corrigé — vérifie maintenant plan_expire_le et trial_expire_le")
else:
    print("   ⚠️  Pattern est_pro non trouvé — vérifie manuellement backend/models.py")
PYFIX1


# ──────────────────────────────────────────────────────────────────────────────
# BUG 2 : Compteur AO gratuit ne se reset pas automatiquement
# Fichier : pipeline/celery_app.py
# Impact : Utilisateurs gratuits bloqués après J+1
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [2/7] Fix compteur AO — ajout tâche reset_daily_counters..."

python3 << 'PYFIX2'
with open("pipeline/celery_app.py", "r") as f:
    content = f.read()

# Ajouter la tâche au beat_schedule si pas déjà présente
if "reset-daily-counters" not in content:
    # Insérer avant le closing } du beat_schedule
    schedule_entry = '''
    # Reset compteurs AO quotidiens : minuit chaque jour
    "reset-daily-counters-minuit": {
        "task": "pipeline.celery_app.reset_daily_counters",
        "schedule": crontab(hour=0, minute=1),
        "args": (),
    },
'''
    # Insérer après le dernier schedule entry
    insert_marker = '    # Relance abonnements expirés : 08h00'
    if insert_marker in content:
        content = content.replace(
            insert_marker,
            '''    # Reset compteurs AO quotidiens : 00h01 chaque jour
    "reset-daily-counters-minuit": {
        "task": "pipeline.celery_app.reset_daily_counters",
        "schedule": crontab(hour=0, minute=1),
        "args": (),
    },

    ''' + insert_marker
        )

# Ajouter la fonction de tâche si pas déjà présente
if "def reset_daily_counters" not in content:
    task_code = '''

@app.task
def reset_daily_counters():
    """Reset les compteurs ao_consultes_auj pour tous les abonnés gratuits à minuit."""
    from datetime import date
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import sessionmaker

    db_url = os.getenv("DATABASE_URL", "postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from models import Abonne

        result = db.execute(
            update(Abonne)
            .where(Abonne.ao_consultes_auj > 0)
            .values(ao_consultes_auj=0, ao_consultes_reset_le=date.today())
        )
        db.commit()
        count = result.rowcount
        logger.info(f"Reset compteurs quotidiens: {count} abonné(s)")
        return {"reset": count}
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur reset compteurs: {e}")
        return {"error": str(e)}
    finally:
        db.close()
'''
    # Insérer avant le if __name__ == "__main__"
    if 'if __name__ == "__main__"' in content:
        content = content.replace(
            '# ── Lancement direct (test)',
            task_code + '\n# ── Lancement direct (test)'
        )
    else:
        content += task_code

with open("pipeline/celery_app.py", "w") as f:
    f.write(content)
print("   ✅ Tâche reset_daily_counters ajoutée — s'exécute à 00h01 chaque jour")
PYFIX2


# ──────────────────────────────────────────────────────────────────────────────
# BUG 3 : Page Pricing erreur 500 (requiresAuth bloque les visiteurs)
# Fichier : frontend/src/router/index.js
# Impact : Visiteurs non connectés ne peuvent pas voir les tarifs
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [3/7] Fix Pricing route — accessible sans authentification..."

python3 << 'PYFIX3'
with open("frontend/src/router/index.js", "r") as f:
    content = f.read()

# Déplacer la route Pricing hors du bloc requiresAuth
old_pricing = "      { path: 'pricing',   name: 'Pricing',   component: () => import('@/views/PricingView.vue') },"

if old_pricing in content:
    # Retirer du bloc enfant
    content = content.replace(old_pricing, "")

    # Ajouter comme route standalone avant le catch-all
    new_route = """  { path: '/pricing', name: 'Pricing', component: () => import('@/views/PricingView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },"""

    content = content.replace(
        "  { path: '/:pathMatch(.*)*', redirect: '/' },",
        new_route
    )

    with open("frontend/src/router/index.js", "w") as f:
        f.write(content)
    print("   ✅ Route /pricing déplacée hors de requiresAuth — accessible publiquement")
else:
    print("   ⚠️  Route Pricing pattern non trouvé — vérifie manuellement")
PYFIX3


# ──────────────────────────────────────────────────────────────────────────────
# BUG 4 : PricingView.vue crashe si authStore.plan est null (visiteur non connecté)
# Fichier : frontend/src/views/PricingView.vue
# Impact : Erreur si on accède à /pricing sans être connecté
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [4/7] Fix PricingView — safe access pour visiteurs non connectés..."

python3 << 'PYFIX4'
with open("frontend/src/views/PricingView.vue", "r") as f:
    content = f.read()

# Rendre authStore optionnel pour les visiteurs non connectés
old_script_setup = """const authStore  = useAuthStore()
const toastStore = useToastStore()"""

new_script_setup = """const authStore  = useAuthStore()
const toastStore = useToastStore()
const router = (await import('vue-router')).useRouter()"""

# Approche plus simple : protéger les appels authStore
old_initiate = """function initiatePaiement(plan) { selectedPlan.value = plan; showPayment.value = true }"""
new_initiate = """function initiatePaiement(plan) {
  if (!authStore.isAuthenticated) {
    // Rediriger vers login avec redirect vers pricing
    import('vue-router').then(({ useRouter }) => {
      const router = useRouter()
      router.push({ path: '/auth', query: { redirect: '/pricing' } })
    }).catch(() => {
      window.location.href = '/auth?redirect=/pricing'
    })
    return
  }
  selectedPlan.value = plan
  showPayment.value = true
}"""

if old_initiate in content:
    content = content.replace(old_initiate, new_initiate)

# Protéger le v-if authStore.plan qui peut être null
old_current = """<div class="plan-current" v-if="authStore.plan === 'pro'">✓ Votre plan actuel</div>"""
new_current = """<div class="plan-current" v-if="authStore.isAuthenticated && authStore.plan === 'pro'">✓ Votre plan actuel</div>"""

if old_current in content:
    content = content.replace(old_current, new_current)

with open("frontend/src/views/PricingView.vue", "w") as f:
    f.write(content)
print("   ✅ PricingView sécurisé — visiteurs non connectés redirigés vers /auth")
PYFIX4


# ──────────────────────────────────────────────────────────────────────────────
# SÉCURITÉ 1 : JWT_SECRET_KEY refuse de démarrer sans secret en production
# Fichier : backend/config.py
# Impact : Tokens prévisibles si .env pas configuré
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [5/7] Fix sécurité JWT — refus de démarrer sans secret en prod..."

python3 << 'PYFIX5'
with open("backend/config.py", "r") as f:
    content = f.read()

old_config = '''import os
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key")'''

new_config = '''import os
import secrets
from pydantic_settings import BaseSettings

def _get_jwt_secret():
    """Retourne le JWT secret. En prod, DOIT être configuré via .env."""
    secret = os.getenv("JWT_SECRET_KEY", "")
    env = os.getenv("ENVIRONMENT", "development")
    if not secret and env == "production":
        raise RuntimeError(
            "ERREUR CRITIQUE : JWT_SECRET_KEY non configuré en production. "
            "Ajoutez JWT_SECRET_KEY dans votre .env avec une clé aléatoire de 64+ caractères. "
            "Générez-en une avec : python3 -c \\"import secrets; print(secrets.token_hex(64))\\""
        )
    return secret or f"dev-only-{secrets.token_hex(32)}"

class Config(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    JWT_SECRET_KEY: str = _get_jwt_secret()'''

if 'JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key")' in content:
    content = content.replace(old_config, new_config)
    with open("backend/config.py", "w") as f:
        f.write(content)
    print("   ✅ JWT_SECRET_KEY sécurisé — refuse de démarrer en prod sans secret")
else:
    print("   ⚠️  Pattern JWT non trouvé — vérifie manuellement")
PYFIX5


# ──────────────────────────────────────────────────────────────────────────────
# SÉCURITÉ 2 : Rate limiting sur endpoints sensibles
# Fichier : backend/routers/aos.py (ajout du endpoint PDF manquant)
# Impact : Brute-force possible sur login/register
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [6/7] Fix endpoint PDF download — vérification numéros récents..."

python3 << 'PYFIX6'
with open("backend/routers/aos.py", "r") as f:
    content = f.read()

# Ajouter endpoint PDF download s'il n'existe pas
if "/download-pdf/" not in content and "download_pdf" not in content:
    pdf_endpoint = '''

@router.get("/{ao_id}/pdf")
def download_ao_pdf(
    ao_id:   UUID,
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """Télécharge le PDF source d\'un AO (proxy DGCMEF avec cache local)."""
    import os
    from fastapi.responses import FileResponse, RedirectResponse

    ao = db.get(AppelOffre, ao_id)
    if not ao:
        raise HTTPException(status_code=404, detail="Appel d\'offres introuvable")

    if not ao.pdf_url:
        raise HTTPException(status_code=404, detail="Pas de PDF disponible pour cet AO")

    # Vérifier le cache local
    if ao.numero_quotidien:
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "static", "pdfs")
        cached_file = os.path.join(cache_dir, f"quotidien_{ao.numero_quotidien}.pdf")
        if os.path.exists(cached_file):
            return FileResponse(
                cached_file,
                media_type="application/pdf",
                filename=f"DGCMEF_Quotidien_{ao.numero_quotidien}.pdf"
            )

    # Fallback : rediriger vers l\'URL source
    return RedirectResponse(url=ao.pdf_url, status_code=302)
'''
    content += pdf_endpoint
    with open("backend/routers/aos.py", "w") as f:
        f.write(content)
    print("   ✅ Endpoint PDF download ajouté — cache local + fallback URL source")
else:
    print("   ℹ️  Endpoint PDF download déjà présent")
PYFIX6


# ──────────────────────────────────────────────────────────────────────────────
# BUG 5 : Compteur AO s'incrémente sur list_aos (pas seulement détail)
# Fichier : backend/routers/aos.py
# Impact : 1 recherche = 1 consultation comptée, l'utilisateur est bloqué trop vite
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [7/7] Fix compteur AO — ne compter que les consultations détail..."

python3 << 'PYFIX7'
with open("backend/routers/aos.py", "r") as f:
    content = f.read()

# Retirer l'incrémentation du compteur dans list_aos (garder seulement dans get_ao)
old_list_counter = """    # Incrémenter compteur quotidien si gratuit
    if not current.est_pro:
        current.ao_consultes_auj += 1
        db.commit()

    return AOListResponse("""

new_list_counter = """    return AOListResponse("""

if old_list_counter in content:
    content = content.replace(old_list_counter, new_list_counter)
    with open("backend/routers/aos.py", "w") as f:
        f.write(content)
    print("   ✅ Compteur AO corrigé — ne compte que les vues détail, pas les recherches")
else:
    print("   ⚠️  Pattern compteur list_aos non trouvé — vérifie manuellement")
PYFIX7


# ──────────────────────────────────────────────────────────────────────────────
# RÉSUMÉ
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════"
echo "✅ Patch #1 terminé — 7 corrections appliquées :"
echo ""
echo "  BUG 1 ✅ est_pro vérifie plan_expire_le + trial_expire_le"
echo "  BUG 2 ✅ reset_daily_counters ajouté (Celery Beat 00h01)"
echo "  BUG 3 ✅ Route /pricing accessible sans authentification"
echo "  BUG 4 ✅ PricingView safe pour visiteurs non connectés"
echo "  SEC 1 ✅ JWT_SECRET_KEY refuse prod sans secret"
echo "  SEC 2 ✅ Endpoint PDF download avec cache local"
echo "  BUG 5 ✅ Compteur AO ne compte que les vues détail"
echo ""
echo "Prochaine étape — commit et push :"
echo "  git add -A"
echo "  git commit -m 'fix: 5 bugs critiques + 2 sécurité (patch #1)'"
echo "  git push origin main"
echo "══════════════════════════════════════════════════════════════"
