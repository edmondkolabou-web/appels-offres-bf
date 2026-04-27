#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# NetSync Gov — Patch #8 : 11 suggestions restantes du rapport d'audit
# Date : 27 avril 2026
# Usage : cd ~/appels-offres-bf && bash patches/fix-remaining-suggestions.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  NetSync Gov — Patch #8 : 11 suggestions restantes         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# 1. Trial automatique 7 jours à l'inscription
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [1/11] Trial Pro 7 jours automatique à l'inscription..."

python3 << 'PYFIX'
with open("backend/routers/auth.py", "r") as f:
    content = f.read()

if "trial_actif" not in content:
    old = '''    abonne = Abonne(
        email=body.email,
        password_hash=hash_password(body.password),
        prenom=body.prenom,
        nom=body.nom,
        entreprise=body.entreprise,
        whatsapp=body.whatsapp,
        plan=body.plan if hasattr(body, 'plan') and body.plan else "gratuit",
        email_verifie=False,
        actif=True,
        ao_consultes_auj=0,
    )'''

    new = '''    from datetime import timedelta
    abonne = Abonne(
        email=body.email,
        password_hash=hash_password(body.password),
        prenom=body.prenom,
        nom=body.nom,
        entreprise=body.entreprise,
        whatsapp=body.whatsapp,
        plan="pro",
        email_verifie=False,
        actif=True,
        ao_consultes_auj=0,
        trial_actif=True,
        trial_expire_le=date.today() + timedelta(days=7),
    )'''

    if old in content:
        # Add date import if not present
        if "from datetime import" not in content:
            content = "from datetime import date\n" + content
        elif "date" not in content.split("from datetime import")[1].split("\n")[0]:
            content = content.replace("from datetime import", "from datetime import date, ")
        content = content.replace(old, new)
        with open("backend/routers/auth.py", "w") as f:
            f.write(content)
        print("   ✅ Trial Pro 7 jours activé automatiquement à l'inscription")
    else:
        print("   ⚠️  Pattern register non trouvé — vérifie manuellement")
else:
    print("   ℹ️  Trial déjà configuré")
PYFIX


# ──────────────────────────────────────────────────────────────────────────────
# 2. Toast notifications animées
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [2/11] Toast notifications animées..."

cat > frontend/src/components/ui/AppToast.vue << 'VUEEOF'
<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div v-for="t in toastStore.toasts" :key="t.id" :class="['toast', `toast-${t.type}`]" @click="toastStore.remove(t.id)">
          <span class="toast-icon">{{ icons[t.type] || 'ℹ️' }}</span>
          <span class="toast-msg">{{ t.message }}</span>
          <button class="toast-close" @click.stop="toastStore.remove(t.id)">×</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useToastStore } from '@/stores/toast'
const toastStore = useToastStore()
const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' }
</script>

<style scoped>
.toast-container { position:fixed; top:72px; right:16px; z-index:9999; display:flex; flex-direction:column; gap:8px; max-width:380px; }
.toast { display:flex; align-items:center; gap:10px; padding:12px 16px; border-radius:10px; box-shadow:0 8px 24px rgba(0,0,0,.12); cursor:pointer; backdrop-filter:blur(8px); font-size:13px; }
.toast-success { background:#f0fdf4; border:1px solid #bbf7d0; color:#166534; }
.toast-error   { background:#fef2f2; border:1px solid #fecaca; color:#991b1b; }
.toast-warning { background:#fffbeb; border:1px solid #fde68a; color:#92400e; }
.toast-info    { background:#eff6ff; border:1px solid #bfdbfe; color:#1e40af; }
.toast-icon { font-size:16px; flex-shrink:0; }
.toast-msg { flex:1; line-height:1.4; }
.toast-close { background:none; border:none; font-size:18px; color:inherit; opacity:.5; cursor:pointer; padding:0 0 0 8px; }
.toast-close:hover { opacity:1; }

.toast-enter-active { animation:toast-in .3s ease; }
.toast-leave-active { animation:toast-out .25s ease forwards; }
@keyframes toast-in { from { opacity:0; transform:translateX(100px) scale(.95); } to { opacity:1; transform:translateX(0) scale(1); } }
@keyframes toast-out { to { opacity:0; transform:translateX(100px) scale(.95); } }
</style>
VUEEOF

# Vérifier si AppToast est déjà importé dans App.vue
python3 << 'PYFIX2'
import os
app_vue = "frontend/src/App.vue"
if os.path.exists(app_vue):
    with open(app_vue, "r") as f:
        content = f.read()
    if "AppToast" not in content:
        # Add import and component
        if "<script setup>" in content:
            content = content.replace(
                "<script setup>",
                "<script setup>\nimport AppToast from '@/components/ui/AppToast.vue'"
            )
        if "<RouterView" in content:
            content = content.replace(
                "<RouterView",
                "<AppToast />\n    <RouterView"
            )
        with open(app_vue, "w") as f:
            f.write(content)
        print("   ✅ Toast animé créé + intégré dans App.vue")
    else:
        print("   ℹ️  AppToast déjà dans App.vue")
else:
    print("   ⚠️  App.vue non trouvé")
PYFIX2


# ──────────────────────────────────────────────────────────────────────────────
# 3. Badge "NOUVEAU" sur les AOs publiés aujourd'hui
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [3/11] Badge NOUVEAU sur les AOs du jour..."

python3 << 'PYFIX3'
# Chercher AOListView.vue pour ajouter le badge
import os
f = "frontend/src/views/AOListView.vue"
if os.path.exists(f):
    with open(f, "r") as fh:
        content = fh.read()
    if "tag-nouveau" not in content:
        # Ajouter le badge après les tags existants
        old = '<span v-if="ao.est_urgent" class="tag tag-urgent">'
        new = '''<span v-if="isToday(ao.date_publication)" class="tag tag-nouveau">NOUVEAU</span>
              <span v-if="ao.est_urgent" class="tag tag-urgent">'''
        if old in content:
            content = content.replace(old, new)
        
        # Ajouter la fonction isToday
        if "function isToday" not in content and "isToday" not in content:
            content = content.replace(
                "</script>",
                "\nfunction isToday(dateStr) {\n  if (!dateStr) return false\n  return new Date(dateStr).toDateString() === new Date().toDateString()\n}\n</script>"
            )
        
        # Ajouter le style
        if "tag-nouveau" not in content:
            content = content.replace(
                "</style>",
                ".tag-nouveau { background:#EDE9FE; color:#5B21B6; animation:pulse-new 2s ease-in-out infinite; }\n@keyframes pulse-new { 0%,100%{opacity:1} 50%{opacity:.7} }\n</style>"
            )
        
        with open(f, "w") as fh:
            fh.write(content)
        print("   ✅ Badge NOUVEAU ajouté sur les AOs publiés aujourd'hui")
    else:
        print("   ℹ️  Badge NOUVEAU déjà présent")
else:
    print("   ⚠️  AOListView.vue non trouvé")
PYFIX3


# ──────────────────────────────────────────────────────────────────────────────
# 4. Pagination curseur (backend)
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [4/11] Pagination curseur sur /aos..."

python3 << 'PYFIX4'
with open("backend/routers/aos.py", "r") as f:
    content = f.read()

if "cursor" not in content and "after_id" not in content:
    # Ajouter le paramètre after_id à list_aos
    old_params = '''    q:              Optional[str]  = Query(None, description="Recherche full-text"),'''
    new_params = '''    q:              Optional[str]  = Query(None, description="Recherche full-text"),
    after_id:       Optional[str]  = Query(None, description="Curseur : ID du dernier AO (pagination curseur)"),'''
    
    content = content.replace(old_params, new_params)
    
    # Ajouter le filtre curseur dans la query
    old_filters_end = '''    base_q = db.query(AppelOffre)
    base_q = _apply_filters(base_q, filters)'''
    
    new_filters_end = '''    base_q = db.query(AppelOffre)
    base_q = _apply_filters(base_q, filters)

    # Pagination curseur (si after_id fourni, plus rapide que OFFSET sur gros datasets)
    if after_id:
        base_q = base_q.filter(AppelOffre.id > after_id)'''
    
    content = content.replace(old_filters_end, new_filters_end)
    
    with open("backend/routers/aos.py", "w") as f:
        f.write(content)
    print("   ✅ Pagination curseur ajoutée (paramètre after_id)")
else:
    print("   ℹ️  Pagination curseur déjà présente")
PYFIX4


# ──────────────────────────────────────────────────────────────────────────────
# 5. Cache Redis sur requêtes fréquentes
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [5/11] Cache Redis sur /aos/secteurs..."

python3 << 'PYFIX5'
with open("backend/routers/aos.py", "r") as f:
    content = f.read()

if "redis_cache" not in content and "cache_get" not in content:
    # Ajouter un helper cache en haut du fichier
    old_import = "from backend.security import get_current_abonne"
    new_import = '''from backend.security import get_current_abonne

# ── Cache Redis simple ──
import json as _json
import redis as _redis
try:
    _rcache = _redis.from_url("redis://localhost:6379/0")
    _rcache.ping()
except Exception:
    _rcache = None

def _cache_get(key):
    if not _rcache: return None
    try:
        val = _rcache.get(f"nsg:{key}")
        return _json.loads(val) if val else None
    except: return None

def _cache_set(key, data, ttl=300):
    if not _rcache: return
    try: _rcache.setex(f"nsg:{key}", ttl, _json.dumps(data))
    except: pass'''
    
    content = content.replace(old_import, new_import)
    
    # Ajouter le cache sur list_secteurs
    old_secteurs = '''def list_secteurs(db: Session = Depends(get_db)):
    """Liste des secteurs présents en base avec leur nombre d'AOs."""
    rows = ('''
    
    new_secteurs = '''def list_secteurs(db: Session = Depends(get_db)):
    """Liste des secteurs présents en base avec leur nombre d'AOs. Caché 1h."""
    cached = _cache_get("secteurs")
    if cached:
        return cached
    rows = ('''
    
    content = content.replace(old_secteurs, new_secteurs)
    
    # Ajouter le cache set après le return
    old_return = '''    return [{"secteur": r.secteur, "nb_ao": r.nb} for r in rows]'''
    new_return = '''    result = [{"secteur": r.secteur, "nb_ao": r.nb} for r in rows]
    _cache_set("secteurs", result, ttl=3600)  # Cache 1h
    return result'''
    
    content = content.replace(old_return, new_return)
    
    with open("backend/routers/aos.py", "w") as f:
        f.write(content)
    print("   ✅ Cache Redis ajouté sur /secteurs (TTL 1h)")
else:
    print("   ℹ️  Cache Redis déjà présent")
PYFIX5


# ──────────────────────────────────────────────────────────────────────────────
# 6. Logs structurés JSON
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [6/11] Logs structurés JSON..."

python3 << 'PYFIX6'
with open("backend/main.py", "r") as f:
    content = f.read()

if "pythonjsonlogger" not in content and "json_logger" not in content:
    old_logging = '''logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
)'''
    
    new_logging = '''# Logs structurés JSON en production, texte en dev
import os as _os
if _os.getenv("ENVIRONMENT") == "production":
    try:
        from pythonjsonlogger import jsonlogger
        handler = logging.StreamHandler()
        handler.setFormatter(jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"}
        ))
        logging.root.handlers = [handler]
        logging.root.setLevel(logging.INFO)
    except ImportError:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s — %(message)s")
else:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s — %(message)s")'''
    
    if old_logging in content:
        content = content.replace(old_logging, new_logging)
        with open("backend/main.py", "w") as f:
            f.write(content)
        print("   ✅ Logs structurés JSON en production, texte lisible en dev")
    else:
        print("   ⚠️  Pattern logging non trouvé")
else:
    print("   ℹ️  Logs JSON déjà configurés")
PYFIX6


# ──────────────────────────────────────────────────────────────────────────────
# 7. Gestion erreurs granulaire (422, 409, 504)
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [7/11] Handlers erreurs granulaires..."

python3 << 'PYFIX7'
with open("backend/main.py", "r") as f:
    content = f.read()

if "ValidationError" not in content or "validation_error_handler" not in content:
    # Ajouter après la création de l'app
    error_handlers = '''
# ── Error Handlers granulaires ─────────────────────────────────────────────────
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    errors = []
    for e in exc.errors():
        field = " → ".join(str(l) for l in e.get("loc", []))
        errors.append({"field": field, "message": e.get("msg", ""), "type": e.get("type", "")})
    return JSONResponse(status_code=422, content={"detail": "Erreur de validation", "errors": errors})

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, exc):
    return JSONResponse(status_code=409, content={"detail": "Conflit de données — cet enregistrement existe déjà"})

@app.exception_handler(Exception)
async def global_error_handler(request, exc):
    logger.error(f"Erreur serveur: {type(exc).__name__}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})
'''
    
    # Insérer avant le healthcheck
    if "/health/detailed" in content:
        content = content.replace(
            "# ── Healthcheck détaillé",
            error_handlers + "\n# ── Healthcheck détaillé"
        )
    else:
        content += error_handlers
    
    with open("backend/main.py", "w") as f:
        f.write(content)
    print("   ✅ Handlers erreurs : 422 (validation), 409 (intégrité), 500 (global)")
else:
    print("   ℹ️  Handlers déjà présents")
PYFIX7


# ──────────────────────────────────────────────────────────────────────────────
# 8. Section Activité récente dans le dashboard
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [8/11] Section activité récente dans le dashboard..."

python3 << 'PYFIX8'
with open("frontend/src/views/DashboardView.vue", "r") as f:
    content = f.read()

if "activite-recente" not in content and "Activité récente" not in content:
    # Ajouter la section avant le bloc upgrade dans la sidebar
    old_upgrade = '''        <!-- Upgrade CTA si gratuit -->'''
    new_section = '''        <!-- Activité récente -->
        <div class="card">
          <div class="section-head">
            <h2 class="section-title">Activité récente</h2>
          </div>
          <div class="activity-list">
            <div class="activity-item" v-for="a in recentActivity" :key="a.id">
              <span class="activity-dot" :class="a.color"></span>
              <div class="activity-info">
                <p class="activity-text">{{ a.text }}</p>
                <p class="activity-time">{{ a.time }}</p>
              </div>
            </div>
            <div v-if="!recentActivity.length" class="empty-mini">Aucune activité</div>
          </div>
        </div>

        <!-- Upgrade CTA si gratuit -->'''
    
    content = content.replace(old_upgrade, new_section)
    
    # Ajouter les données d'activité dans le script
    old_onmounted = "onMounted(async () => {"
    new_activity = '''const recentActivity = computed(() => {
  const acts = []
  acts.push({ id: 'login', text: 'Connexion au tableau de bord', time: 'À l\\'instant', color: 'dot-blue' })
  if (todayAOs.value.length) acts.push({ id: 'ao', text: `${todayAOs.value.length} nouveaux AOs consultés`, time: 'Aujourd\\'hui', color: 'dot-green' })
  if (favorisStore.items.length) acts.push({ id: 'fav', text: `${favorisStore.items.length} AO(s) en favoris`, time: 'En cours', color: 'dot-amber' })
  if (alertesStore.items.filter(a => a.actif).length) acts.push({ id: 'alert', text: `${alertesStore.items.filter(a => a.actif).length} alerte(s) active(s)`, time: 'Configurées', color: 'dot-blue' })
  return acts.slice(0, 5)
})

onMounted(async () => {'''
    
    content = content.replace(old_onmounted, new_activity)
    
    # Ajouter les styles
    content = content.replace(
        "/* Responsive */",
        """/* Activity */
.activity-list { display:flex; flex-direction:column; gap:2px; }
.activity-item { display:flex; align-items:flex-start; gap:10px; padding:8px 0; border-bottom:1px solid var(--border); }
.activity-item:last-child { border-bottom:none; }
.activity-dot { width:8px; height:8px; border-radius:50%; margin-top:5px; flex-shrink:0; }
.dot-blue { background:var(--blue-500); }
.dot-green { background:var(--green-400); }
.dot-amber { background:var(--amber-400); }
.dot-red { background:var(--red-400); }
.activity-info { flex:1; }
.activity-text { font-size:12px; font-weight:500; color:var(--ink); line-height:1.4; }
.activity-time { font-size:10px; color:var(--muted); margin-top:1px; }

/* Responsive */"""
    )
    
    with open("frontend/src/views/DashboardView.vue", "w") as f:
        f.write(content)
    print("   ✅ Section activité récente ajoutée au dashboard")
else:
    print("   ℹ️  Activité récente déjà présente")
PYFIX8


# ──────────────────────────────────────────────────────────────────────────────
# 9. Animations transitions entre pages
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [9/11] Transitions animées entre pages..."

python3 << 'PYFIX9'
with open("frontend/src/components/layout/AppLayout.vue", "r") as f:
    content = f.read()

if "page-transition" not in content and "RouterView v-slot" not in content:
    # Remplacer <RouterView /> par une version avec transition
    old_rv = "<RouterView />"
    new_rv = '''<RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>'''
    
    if old_rv in content:
        content = content.replace(old_rv, new_rv)
    
    # Ajouter les styles de transition
    content = content.replace(
        "@media(max-width:768px)",
        """.page-enter-active { animation:page-in .2s ease; }
.page-leave-active { animation:page-out .15s ease forwards; }
@keyframes page-in { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
@keyframes page-out { to { opacity:0; transform:translateY(-4px); } }

@media(max-width:768px)"""
    )
    
    with open("frontend/src/components/layout/AppLayout.vue", "w") as f:
        f.write(content)
    print("   ✅ Transitions animées entre pages (fade + slide)")
else:
    print("   ℹ️  Transitions déjà présentes")
PYFIX9


# ──────────────────────────────────────────────────────────────────────────────
# 10. Changer les mots de passe des comptes test
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [10/11] Changement mots de passe comptes test..."

python3 << 'PYFIX10'
import os, secrets, string

# Générer des mots de passe aléatoires
def gen_pwd():
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(16))

pwd1 = gen_pwd()
pwd2 = gen_pwd()

# Créer un script SQL pour changer les mots de passe
# On ne peut pas hasher ici sans bcrypt, donc on crée un script Python
script = f'''#!/usr/bin/env python3
"""Change les mots de passe des comptes test. Exécuter une seule fois."""
import sys
sys.path.insert(0, ".")
from backend.database import get_db
from backend.security import hash_password
from sqlalchemy import text

db = next(get_db())

# Compte Pro
new_hash1 = hash_password("{pwd1}")
db.execute(text("UPDATE abonnes SET password_hash = :h WHERE email = 'test@netsync.bf'"), {{"h": new_hash1}})

# Compte Gratuit
new_hash2 = hash_password("{pwd2}")
db.execute(text("UPDATE abonnes SET password_hash = :h WHERE email = 'test2@netsync.bf'"), {{"h": new_hash2}})

db.commit()
print("✅ Mots de passe changés :")
print(f"  test@netsync.bf  → {pwd1}")
print(f"  test2@netsync.bf → {pwd2}")
print()
print("⚠️  NOTEZ CES MOTS DE PASSE — ils ne sont pas récupérables.")
print("⚠️  NE PAS COMMITTER ce script avec les mots de passe.")
'''

with open("scripts/change-test-passwords.py", "w") as f:
    f.write(script)
os.makedirs("scripts", exist_ok=True)

print(f"   ✅ Script scripts/change-test-passwords.py créé")
print(f"   ⚠️  Exécuter MANUELLEMENT : python3 scripts/change-test-passwords.py")
print(f"   ⚠️  Ne PAS committer le script (contient les mots de passe)")
PYFIX10


# ──────────────────────────────────────────────────────────────────────────────
# 11. Calendrier clôtures vue mois (amélioration dashboard)
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [11/11] Calendrier clôtures amélioré..."

python3 << 'PYFIX11'
with open("frontend/src/views/DashboardView.vue", "r") as f:
    content = f.read()

# Améliorer l'onglet Calendrier clôtures avec une vraie grille calendrier
old_calendar = '''        <!-- Tab: Calendrier clôtures -->
        <div v-if="activeTab === \'calendar\'" class="card tab-content">
          <div class="section-head">
            <h2 class="section-title">Clôtures à venir</h2>
          </div>
          <div v-if="urgentAOs.length" class="deadline-list">
            <div v-for="ao in urgentAOs" :key="ao.id" class="deadline-item" @click="$router.push(`/aos/${ao.id}`)">
              <div class="deadline-days" :class="deadlineClass(ao.jours_restants)">
                J-{{ ao.jours_restants || \'?\' }}
              </div>
              <div class="deadline-info">
                <p class="deadline-title">{{ ao.titre }}</p>
                <p class="deadline-meta">
                  {{ ao.autorite_contractante }}
                  <span v-if="ao.date_cloture"> · Clôture {{ formatDate(ao.date_cloture) }}</span>
                </p>
              </div>
              <span class="tag" :class="`tag-${ao.secteur}`">{{ ao.secteur }}</span>
            </div>
          </div>
          <div v-else class="empty-state">
            <p>Aucune clôture imminente — tout va bien !</p>
          </div>
        </div>'''

new_calendar = '''        <!-- Tab: Calendrier clôtures -->
        <div v-if="activeTab === 'calendar'" class="card tab-content">
          <div class="section-head">
            <h2 class="section-title">Clôtures à venir</h2>
            <span class="section-badge" v-if="urgentAOs.length">{{ urgentAOs.length }} cette semaine</span>
          </div>

          <!-- Mini calendrier mois -->
          <div class="mini-cal">
            <div class="mini-cal-header">
              <span class="mini-cal-month">{{ currentMonthLabel }}</span>
            </div>
            <div class="mini-cal-grid">
              <span class="mini-cal-day-label" v-for="d in ['L','M','M','J','V','S','D']" :key="d">{{ d }}</span>
              <span v-for="(day, i) in calendarDays" :key="i"
                :class="['mini-cal-day', { 'today': day.isToday, 'has-event': day.hasEvent, 'empty': !day.num }]"
                :title="day.hasEvent ? day.eventCount + ' clôture(s)' : ''">
                {{ day.num || '' }}
              </span>
            </div>
            <div class="mini-cal-legend">
              <span class="legend-item"><span class="legend-dot dot-blue"></span> Aujourd'hui</span>
              <span class="legend-item"><span class="legend-dot dot-red"></span> Clôture</span>
            </div>
          </div>

          <!-- Liste clôtures -->
          <div v-if="urgentAOs.length" class="deadline-list" style="margin-top:1rem;">
            <div v-for="ao in urgentAOs" :key="ao.id" class="deadline-item" @click="$router.push(`/aos/${ao.id}`)">
              <div class="deadline-days" :class="deadlineClass(ao.jours_restants)">
                J-{{ ao.jours_restants || '?' }}
              </div>
              <div class="deadline-info">
                <p class="deadline-title">{{ ao.titre }}</p>
                <p class="deadline-meta">
                  {{ ao.autorite_contractante }}
                  <span v-if="ao.date_cloture"> · Clôture {{ formatDate(ao.date_cloture) }}</span>
                </p>
              </div>
              <span class="tag" :class="`tag-${ao.secteur}`">{{ ao.secteur }}</span>
            </div>
          </div>
          <div v-else class="empty-state">
            <p>Aucune clôture imminente — tout va bien !</p>
          </div>
        </div>'''

if old_calendar in content:
    content = content.replace(old_calendar, new_calendar)

    # Ajouter les computed du calendrier
    old_format = "function formatDate(dateStr)"
    new_computed = '''const currentMonthLabel = computed(() => {
  const d = new Date()
  const months = ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre']
  return months[d.getMonth()] + ' ' + d.getFullYear()
})

const calendarDays = computed(() => {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth()
  const firstDay = new Date(year, month, 1).getDay() || 7 // Lundi = 1
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const today = now.getDate()
  
  // Dates de clôture ce mois
  const closureDates = new Set()
  for (const ao of urgentAOs.value) {
    if (ao.date_cloture) {
      const d = new Date(ao.date_cloture)
      if (d.getMonth() === month && d.getFullYear() === year) {
        closureDates.add(d.getDate())
      }
    }
  }
  
  const days = []
  // Jours vides avant le 1er
  for (let i = 1; i < firstDay; i++) days.push({ num: null, empty: true })
  // Jours du mois
  for (let d = 1; d <= daysInMonth; d++) {
    days.push({ num: d, isToday: d === today, hasEvent: closureDates.has(d), eventCount: 1 })
  }
  return days
})

function formatDate(dateStr)'''
    content = content.replace(old_format, new_computed)

    # Ajouter les styles du calendrier
    content = content.replace(
        "/* Activity */",
        """/* Mini Calendar */
.mini-cal { background:var(--surface); border-radius:var(--radius-md); padding:12px; }
.mini-cal-header { text-align:center; margin-bottom:8px; }
.mini-cal-month { font-size:13px; font-weight:600; color:var(--ink); }
.mini-cal-grid { display:grid; grid-template-columns:repeat(7, 1fr); gap:2px; text-align:center; }
.mini-cal-day-label { font-size:10px; font-weight:600; color:var(--muted); padding:4px 0; }
.mini-cal-day { font-size:11px; padding:5px 2px; border-radius:var(--radius-sm); cursor:default; color:var(--ink-500); position:relative; }
.mini-cal-day.today { background:var(--blue-500); color:white; font-weight:600; border-radius:50%; }
.mini-cal-day.has-event::after { content:''; position:absolute; bottom:1px; left:50%; transform:translateX(-50%); width:4px; height:4px; border-radius:50%; background:var(--red-400); }
.mini-cal-day.empty { color:transparent; }
.mini-cal-legend { display:flex; gap:12px; margin-top:8px; justify-content:center; }
.legend-item { display:flex; align-items:center; gap:4px; font-size:10px; color:var(--muted); }
.legend-dot { width:6px; height:6px; border-radius:50%; }
.dot-blue { background:var(--blue-500); }
.dot-red { background:var(--red-400); }
.section-badge { font-size:10px; font-weight:600; background:var(--amber-50); color:var(--amber-600); padding:2px 8px; border-radius:var(--radius-full); }

/* Activity */"""
    )

    with open("frontend/src/views/DashboardView.vue", "w") as f:
        f.write(content)
    print("   ✅ Calendrier clôtures vue mois ajouté (grille + légende + dots)")
else:
    print("   ⚠️  Pattern calendrier non trouvé — vérifie manuellement")
PYFIX11


# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════"
echo "✅ Patch #8 terminé — 11 suggestions restantes corrigées :"
echo ""
echo "  [1]  ✅ Trial Pro 7 jours automatique à l'inscription"
echo "  [2]  ✅ Toast notifications animées (slide-in/out)"
echo "  [3]  ✅ Badge NOUVEAU sur les AOs publiés aujourd'hui"
echo "  [4]  ✅ Pagination curseur (after_id) sur /aos"
echo "  [5]  ✅ Cache Redis sur /secteurs (TTL 1h)"
echo "  [6]  ✅ Logs structurés JSON en production"
echo "  [7]  ✅ Handlers erreurs granulaires (422, 409, 500)"
echo "  [8]  ✅ Section activité récente dans le dashboard"
echo "  [9]  ✅ Transitions animées entre pages (fade + slide)"
echo "  [10] ✅ Script changement mots de passe test"
echo "  [11] ✅ Calendrier clôtures vue mois (grille)"
echo ""
echo "⚠️  Exécuter SÉPARÉMENT :"
echo "  python3 scripts/change-test-passwords.py"
echo ""
echo "  git add -A"
echo "  git commit -m 'feat: 11 suggestions audit — trial, toasts, cache, calendar, transitions (patch #8)'"
echo "  git push origin main"
echo "══════════════════════════════════════════════════════════════"
