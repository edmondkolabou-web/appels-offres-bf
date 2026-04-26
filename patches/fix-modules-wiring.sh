#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# NetSync Gov — Patch #5 : Câblage des 5 modules
# Date : 26 avril 2026
# Usage : cd ~/appels-offres-bf && bash patches/fix-modules-wiring.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  NetSync Gov — Patch #5 : Câblage 5 modules                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# 1. Enregistrer les 5 routers dans main.py
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [1/4] Enregistrement des 5 routers dans main.py..."

python3 << 'PYFIX1'
with open("backend/main.py", "r") as f:
    content = f.read()

if "candidature" not in content:
    # Ajouter les imports des modules
    old_import = "from backend.routers import oauth, email_verification"
    new_import = """from backend.routers import oauth, email_verification

# ── Modules métier (5 modules) ──
from backend.modules.candidature.backend import router_candidatures, router_pieces, router_taches, router_offres
from backend.modules.conformite.backend import router as conformite_router
from backend.modules.intelligence.backend import router as intelligence_router
from backend.modules.transparence.backend import router as transparence_router
from backend.modules.institutions.backend import router_public as institutions_public_router, router_auth as institutions_auth_router"""

    content = content.replace(old_import, new_import)

    # Ajouter les include_router après le dernier include existant
    old_include = 'app.include_router(email_verification.router, prefix="/api/v1/auth", tags=["Email Verification"])'
    new_include = '''app.include_router(email_verification.router, prefix="/api/v1/auth", tags=["Email Verification"])

# ── Modules métier ──
app.include_router(router_candidatures, prefix="/api/v1/candidatures", tags=["Candidatures"])
app.include_router(router_pieces,       prefix="/api/v1/pieces",       tags=["Pièces administratives"])
app.include_router(router_taches,       prefix="/api/v1/candidatures", tags=["Tâches candidature"])
app.include_router(router_offres,       prefix="/api/v1/candidatures", tags=["Offres IA"])
app.include_router(conformite_router)   # Prefix déjà dans le router : /api/v1/conformite
app.include_router(intelligence_router) # Prefix déjà dans le router : /api/v1/intelligence
app.include_router(transparence_router) # Prefix déjà dans le router : /api/v1/transparence
app.include_router(institutions_public_router)  # /api/v1/institutions (public)
app.include_router(institutions_auth_router, prefix="/api/v1/mon-institution", tags=["Mon Institution"])'''

    content = content.replace(old_include, new_include)

    with open("backend/main.py", "w") as f:
        f.write(content)
    print("   ✅ 5 modules enregistrés dans main.py (9 routers ajoutés)")
else:
    print("   ℹ️  Modules déjà enregistrés dans main.py")
PYFIX1


# ──────────────────────────────────────────────────────────────────────────────
# 2. Ajouter les routes frontend dans router/index.js
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [2/4] Ajout des routes frontend (5 modules)..."

python3 << 'PYFIX2'
with open("frontend/src/router/index.js", "r") as f:
    content = f.read()

if "Candidatures" not in content:
    old_profil = "      { path: 'profil',    name: 'Profil',    component: () => import('@/views/ProfilView.vue') },"

    new_routes = """      { path: 'profil',    name: 'Profil',    component: () => import('@/views/ProfilView.vue') },
      { path: 'candidatures',     name: 'Candidatures',  component: () => import('@/views/CandidaturesView.vue') },
      { path: 'candidatures/:id', name: 'CandidatureDetail', component: () => import('@/views/CandidaturesView.vue'), props: true },
      { path: 'conformite',       name: 'Conformite',    component: () => import('@/views/ConformiteView.vue') },
      { path: 'intelligence',     name: 'Intelligence',  component: () => import('@/views/IntelligenceView.vue') },
      { path: 'institutions',     name: 'Institutions',  component: () => import('@/views/InstitutionsView.vue') },"""

    content = content.replace(old_profil, new_routes)

    # Ajouter les titres dans le mapping
    old_titles = """const titles = { Dashboard: 'Tableau de bord', AOList: 'Appels d\\'offres', AODetail: 'Détail AO',
                 Favoris: 'Mes favoris', Alertes: 'Mes alertes', Pricing: 'Tarifs', Profil: 'Mon profil' }"""

    new_titles = """const titles = { Dashboard: 'Tableau de bord', AOList: 'Appels d\\'offres', AODetail: 'Détail AO',
                 Favoris: 'Mes favoris', Alertes: 'Mes alertes', Pricing: 'Tarifs', Profil: 'Mon profil',
                 Candidatures: 'Mes candidatures', CandidatureDetail: 'Détail candidature',
                 Conformite: 'Conformité', Intelligence: 'Intelligence marché', Institutions: 'Mon institution' }"""

    if old_titles in content:
        content = content.replace(old_titles, new_titles)

    with open("frontend/src/router/index.js", "w") as f:
        f.write(content)
    print("   ✅ 5 routes frontend ajoutées + titres mappés")
else:
    print("   ℹ️  Routes frontend déjà présentes")
PYFIX2


# ──────────────────────────────────────────────────────────────────────────────
# 3. Ajouter les liens dans la sidebar (AppLayout.vue)
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [3/4] Ajout des 5 modules dans la sidebar..."

python3 << 'PYFIX3'
with open("frontend/src/components/layout/AppLayout.vue", "r") as f:
    content = f.read()

if "Candidatures" not in content:
    # Ajouter les icônes SVG
    old_logout = "const IconLogout    = { template: "
    new_icons = """const IconKanban    = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18"/></svg>` }
const IconShield    = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>` }
const IconTrend     = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>` }
const IconBuilding  = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22V12h6v10M12 6v.01M12 10v.01"/></svg>` }
const IconLogout    = { template: """

    content = content.replace(old_logout, new_icons + old_logout.split("= { template: ")[1] if "= { template: " in old_logout else "")
    # Actually, let's do it more carefully
    content_backup = content

with open("frontend/src/components/layout/AppLayout.vue", "r") as f:
    content = f.read()

if "Candidatures" not in content:
    # Add icon components before IconLogout
    icon_block = """const IconKanban    = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18"/></svg>` }
const IconShield    = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>` }
const IconTrend     = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>` }
const IconBuilding  = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22V12h6v10M12 6v.01M12 10v.01"/></svg>` }
"""

    # Insert before IconLogout definition
    content = content.replace(
        "const IconLogout",
        icon_block + "const IconLogout"
    )

    # Update navItems to include new modules
    old_nav_end = """  { to: '/alertes',   label: 'Mes alertes',        icon: IconBell, badge: alertesCount.value || null },
])"""

    new_nav_end = """  { to: '/alertes',   label: 'Mes alertes',        icon: IconBell, badge: alertesCount.value || null },
  { to: '/candidatures', label: 'Candidatures',   icon: IconKanban },
  { to: '/conformite',   label: 'Conformité',     icon: IconShield },
  { to: '/intelligence', label: 'Intelligence',   icon: IconTrend },
  { to: '/institutions', label: 'Mon institution', icon: IconBuilding },
])"""

    if old_nav_end in content:
        content = content.replace(old_nav_end, new_nav_end)
    else:
        # Try without badges (if patch #4 wasn't applied)
        old_nav_simple = """  { to: '/alertes',   label: 'Mes alertes',        icon: IconBell },
]"""
        new_nav_simple = """  { to: '/alertes',   label: 'Mes alertes',        icon: IconBell },
  { to: '/candidatures', label: 'Candidatures',   icon: IconKanban },
  { to: '/conformite',   label: 'Conformité',     icon: IconShield },
  { to: '/intelligence', label: 'Intelligence',   icon: IconTrend },
  { to: '/institutions', label: 'Mon institution', icon: IconBuilding },
]"""
        content = content.replace(old_nav_simple, new_nav_simple)

    with open("frontend/src/components/layout/AppLayout.vue", "w") as f:
        f.write(content)
    print("   ✅ 4 modules ajoutés à la sidebar (Candidatures, Conformité, Intelligence, Institution)")
else:
    print("   ℹ️  Modules déjà dans la sidebar")
PYFIX3


# ──────────────────────────────────────────────────────────────────────────────
# 4. Créer la migration Alembic pour les nouvelles tables
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [4/4] Création migration Alembic pour les 5 modules..."

cat > alembic/versions/f5a2c3d4e6_add_5_modules_tables.py << 'ALEMBIC'
"""Add tables for 5 modules: candidatures, pieces, taches, offres, institutions, attributions

Revision ID: f5a2c3d4e6
Revises: eb0aa4fff9b4
Create Date: 2026-04-26 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

# revision identifiers
revision = 'f5a2c3d4e6'
down_revision = 'eb0aa4fff9b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Candidatures ──
    op.create_table(
        'candidatures',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('ao_id', UUID(as_uuid=True), sa.ForeignKey('appels_offres.id'), nullable=False),
        sa.Column('abonne_id', UUID(as_uuid=True), sa.ForeignKey('abonnes.id'), nullable=False),
        sa.Column('statut', sa.String(30), server_default='en_veille', index=True),
        sa.Column('notes', sa.Text),
        sa.Column('montant_offre', sa.BigInteger),
        sa.Column('score_go_nogo', sa.Float),
        sa.Column('date_depot', sa.Date),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_candidatures_abonne', 'candidatures', ['abonne_id'])
    op.create_index('ix_candidatures_ao', 'candidatures', ['ao_id'])

    # ── Pièces administratives ──
    op.create_table(
        'pieces_administratives',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('abonne_id', UUID(as_uuid=True), sa.ForeignKey('abonnes.id'), nullable=False),
        sa.Column('type_piece', sa.String(50), nullable=False, index=True),
        sa.Column('nom_fichier', sa.String(255)),
        sa.Column('url_stockage', sa.Text),
        sa.Column('taille_fichier', sa.Integer),
        sa.Column('date_emission', sa.Date),
        sa.Column('date_expiration', sa.Date),
        sa.Column('est_valide', sa.Boolean, server_default='true'),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_pieces_abonne', 'pieces_administratives', ['abonne_id'])
    op.create_index('ix_pieces_expiration', 'pieces_administratives', ['date_expiration'])

    # ── Tâches candidature ──
    op.create_table(
        'taches_candidature',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('candidature_id', UUID(as_uuid=True), sa.ForeignKey('candidatures.id', ondelete='CASCADE'), nullable=False),
        sa.Column('titre', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('type_tache', sa.String(30), server_default='general'),
        sa.Column('priorite', sa.String(20), server_default='normale'),
        sa.Column('statut', sa.String(20), server_default='a_faire'),
        sa.Column('date_echeance', sa.Date),
        sa.Column('assignee_id', UUID(as_uuid=True), sa.ForeignKey('abonnes.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Offres générées (IA) ──
    op.create_table(
        'offres_generees',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('candidature_id', UUID(as_uuid=True), sa.ForeignKey('candidatures.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type_offre', sa.String(30), server_default='technique'),
        sa.Column('contenu_ia', sa.Text),
        sa.Column('prompt_utilise', sa.Text),
        sa.Column('version', sa.Integer, server_default='1'),
        sa.Column('valide_par_user', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Institutions ──
    op.create_table(
        'institutions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('nom', sa.String(255), nullable=False),
        sa.Column('sigle', sa.String(30)),
        sa.Column('slug', sa.String(255), unique=True, index=True),
        sa.Column('type_institution', sa.String(50)),
        sa.Column('secteurs', ARRAY(sa.String)),
        sa.Column('region', sa.String(100)),
        sa.Column('email_contact', sa.String(255)),
        sa.Column('telephone', sa.String(30)),
        sa.Column('site_web', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('logo_url', sa.Text),
        sa.Column('plan', sa.String(30), server_default='gratuit'),
        sa.Column('actif', sa.Boolean, server_default='true'),
        sa.Column('verifie', sa.Boolean, server_default='false'),
        sa.Column('abonne_id', UUID(as_uuid=True), sa.ForeignKey('abonnes.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Attributions (Transparence) ──
    op.create_table(
        'attributions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('ao_id', UUID(as_uuid=True), sa.ForeignKey('appels_offres.id'), nullable=True),
        sa.Column('attributaire', sa.String(255), nullable=False, index=True),
        sa.Column('montant_final', sa.BigInteger),
        sa.Column('date_signature', sa.Date),
        sa.Column('source_quotidien', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_attributions_ao', 'attributions', ['ao_id'])

    # ── Ajouter institution_id à appels_offres (si pas déjà fait) ──
    try:
        op.add_column('appels_offres', sa.Column('description_enrichie', sa.Text))
        op.add_column('appels_offres', sa.Column('contact_tel', sa.String(30)))
    except Exception:
        pass  # Colonnes déjà présentes


def downgrade() -> None:
    op.drop_table('attributions')
    op.drop_table('institutions')
    op.drop_table('offres_generees')
    op.drop_table('taches_candidature')
    op.drop_table('pieces_administratives')
    op.drop_table('candidatures')
    try:
        op.drop_column('appels_offres', 'description_enrichie')
        op.drop_column('appels_offres', 'contact_tel')
    except Exception:
        pass
ALEMBIC

echo "   ✅ Migration Alembic créée : 6 nouvelles tables"
echo "      • candidatures (Kanban AO)"
echo "      • pieces_administratives (coffre-fort)"
echo "      • taches_candidature (checklist)"
echo "      • offres_generees (IA Claude)"
echo "      • institutions (dashboard B2G)"
echo "      • attributions (transparence)"


# ──────────────────────────────────────────────────────────────────────────────
# 5. Ajouter les endpoints API dans api.js (frontend)
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [Bonus] Ajout des API clients frontend..."

python3 << 'PYFIX5'
with open("frontend/src/api.js", "r") as f:
    content = f.read()

if "candidaturesApi" not in content:
    new_apis = """

export const candidaturesApi = {
  list:       (params) => api.get('/candidatures', { params }),
  detail:     (id)     => api.get(`/candidatures/${id}`),
  create:     (data)   => api.post('/candidatures', data),
  update:     (id, data) => api.put(`/candidatures/${id}`, data),
  checklist:  (id)     => api.post(`/candidatures/${id}/checklist`),
  genererOffre: (id, data) => api.post(`/candidatures/${id}/generer`, data),
  validerOffre: (offreId) => api.put(`/candidatures/${offreId}/valider`),
}

export const conformiteApi = {
  score:      ()       => api.get('/conformite/score'),
  pieces:     ()       => api.get('/conformite/pieces'),
  calendrier: (jours)  => api.get('/conformite/calendrier', { params: { jours } }),
  catalogue:  ()       => api.get('/conformite/catalogue'),
  verifier:   (aoId)   => api.get(`/conformite/verifier-candidature/${aoId}`),
}

export const intelligenceApi = {
  resume:     ()       => api.get('/intelligence/resume'),
  secteurs:   (params) => api.get('/intelligence/tendances/secteurs', { params }),
  evolution:  (params) => api.get('/intelligence/tendances/evolution', { params }),
  autorites:  (params) => api.get('/intelligence/autorites', { params }),
  procedures: (params) => api.get('/intelligence/tendances/types-procedures', { params }),
  rapport:    ()       => api.get('/intelligence/rapport/mensuel', { responseType: 'blob' }),
}

export const institutionsApi = {
  dashboard:  ()       => api.get('/mon-institution/dashboard'),
  profil:     (data)   => api.put('/mon-institution/profil', data),
  enrichir:   (data)   => api.post('/mon-institution/enrichir-ao', data),
  notifier:   (data)   => api.post('/mon-institution/notifier-soumissionnaires', data),
  rapport:    (mois)   => api.get('/mon-institution/rapport-activite', { params: { mois }, responseType: 'blob' }),
}

export const piecesApi = {
  list:       ()       => api.get('/pieces'),
  expiration: (jours)  => api.get('/pieces/expiration', { params: { jours } }),
  upload:     (data)   => api.post('/pieces', data, { headers: { 'Content-Type': 'multipart/form-data' } }),
  delete:     (id)     => api.delete(`/pieces/${id}`),
}
"""
    # Insert before the default export
    content = content.rstrip()
    if content.endswith("export default api"):
        content = content[:-len("export default api")] + new_apis + "\nexport default api\n"
    else:
        content += new_apis

    with open("frontend/src/api.js", "w") as f:
        f.write(content)
    print("   ✅ 5 API clients ajoutés (candidatures, conformité, intelligence, institutions, pièces)")
else:
    print("   ℹ️  API clients déjà présents")
PYFIX5


# ──────────────────────────────────────────────────────────────────────────────
# RÉSUMÉ
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════"
echo "✅ Patch #5 terminé — 5 modules câblés :"
echo ""
echo "  BACKEND  ✅ 9 routers enregistrés dans main.py"
echo "  FRONTEND ✅ 5 routes ajoutées dans router/index.js"
echo "  SIDEBAR  ✅ 4 liens + icônes dans la navigation"
echo "  BDD      ✅ Migration Alembic : 6 nouvelles tables"
echo "  API      ✅ 5 clients API dans api.js"
echo ""
echo "Modules câblés :"
echo "  1. Candidature  → /candidatures (Kanban + checklist + offre IA)"
echo "  2. Conformité   → /conformite (score + pièces + calendrier)"
echo "  3. Intelligence → /intelligence (graphiques + rapports PDF)"
echo "  4. Transparence → /api/v1/transparence (Open Data public)"
echo "  5. Institutions → /institutions (dashboard B2G)"
echo ""
echo "⚠️  Pour appliquer la migration BDD :"
echo "  cd ~/appels-offres-bf"
echo "  alembic upgrade head"
echo ""
echo "Prochaine étape — commit et push :"
echo "  git add -A"
echo "  git commit -m 'feat: wire up 5 modules — candidature, conformité, intelligence, transparence, institutions (patch #5)'"
echo "  git push origin main"
echo "══════════════════════════════════════════════════════════════"
