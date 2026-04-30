<template>
  <div class="app-shell">
    <!-- Sidebar -->
    <nav class="sidenav" :class="{ 'nav-collapsed': collapsed }" aria-label="Navigation principale">
      <div class="sidenav-logo">
        <div class="logo-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>
        </div>
        <span v-if="!collapsed" class="logo-text">NetSync Gov</span>
      </div>

      <div class="sidenav-links">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-item" :title="item.label">
          <component :is="item.icon" />
          <span v-if="!collapsed">{{ item.label }}</span>
          <span v-if="item.badge && !collapsed" class="nav-badge">{{ item.badge }}</span>
        </RouterLink>
      </div>

      <div class="sidenav-bottom">
        <div class="user-card" @click="router.push('/profil')">
          <div class="avatar">{{ authStore.initiales }}</div>
          <div v-if="!collapsed" class="user-info">
            <div class="user-name">{{ authStore.abonne?.prenom }} {{ authStore.abonne?.nom }}</div>
            <div class="user-plan">
              <span class="plan-chip">{{ authStore.plan.toUpperCase() }}</span>
            </div>
          </div>
        </div>
        <button class="nav-item logout-btn" @click="handleLogout" title="Déconnexion" aria-label="Se déconnecter">
          <IconLogout />
          <span v-if="!collapsed">Déconnexion</span>
        </button>
      </div>
    </nav>

    <!-- Main -->
    <div class="main-area">
      <header class="topbar">
        <button class="collapse-btn" @click="collapsed = !collapsed" :aria-label="collapsed ? 'Ouvrir le menu' : 'Réduire le menu'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <div class="topbar-title">{{ currentPageTitle }}</div>
        <div class="topbar-right">
          <RouterLink to="/pricing" v-if="!authStore.isPro" class="upgrade-chip">
            ⚡ Passer Pro
          </RouterLink>
          <RouterLink to="/alertes" class="icon-btn" aria-label="Mes alertes">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
          </RouterLink>
        </div>
      </header>
      <main class="page-content">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { RouterLink, RouterView, useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// Stores pour les badges sidebar
let favorisCount = ref(0)
let alertesCount = ref(0)
import { onMounted } from 'vue'
onMounted(async () => {
  try {
    const { favorisApi, alertesApi } = await import('@/api')
    const [fav, al] = await Promise.all([
      favorisApi.list().catch(() => ({ data: [] })),
      alertesApi.list().catch(() => ({ data: [] })),
    ])
    favorisCount.value = (fav.data || []).length
    alertesCount.value = (al.data || []).filter(a => a.actif).length
  } catch {}
})
const router    = useRouter()
const route     = useRoute()
const collapsed = ref(false)

// Icônes inline SVG comme composants fonctionnels
const IconDashboard = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>` }
const IconDoc       = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>` }
const IconStar      = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>` }
const IconBell      = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>` }
const IconKanban    = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18"/></svg>` }
const IconShield    = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>` }
const IconTrend     = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>` }
const IconAdmin = { template: \`<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>\` }
const IconBot      = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="4"/><line x1="8" y1="16" x2="8" y2="16.01"/><line x1="16" y1="16" x2="16" y2="16.01"/></svg>` }
const IconBuilding  = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22V12h6v10M12 6v.01M12 10v.01"/></svg>` }
const IconLogout    = { template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>` }

const navItems = computed(() => [
  { to: '/dashboard', label: 'Tableau de bord', icon: IconDashboard },
  { to: '/aos',       label: 'Appels d\'offres', icon: IconDoc },
  { to: '/favoris',   label: 'Mes favoris',       icon: IconStar, badge: favorisCount.value || null },
  { to: '/alertes',   label: 'Mes alertes',        icon: IconBell, badge: alertesCount.value || null },
  { to: '/candidatures', label: 'Candidatures',   icon: IconKanban },
  { to: '/conformite',   label: 'Conformité',     icon: IconShield },
  { to: '/intelligence', label: 'Intelligence',   icon: IconTrend },
  { to: '/institutions', label: 'Mon institution', icon: IconBuilding },
  { to: '/assistant',    label: 'Assistant IA',    icon: IconBot },
  { to: '/admin',        label: 'Administration', icon: IconAdmin },
])

const titles = { Dashboard: 'Tableau de bord', AOList: 'Appels d\'offres', AODetail: 'Détail AO',
                 Favoris: 'Mes favoris', Alertes: 'Mes alertes', Pricing: 'Tarifs', Profil: 'Mon profil' }
const currentPageTitle = computed(() => titles[route.name] || 'NetSync Gov')

async function handleLogout() {
  authStore.logout()
  router.push('/auth')
}

</script>

<style scoped>
.app-shell { display:flex; min-height:100vh; }

.sidenav {
  width:240px; background:var(--ink); display:flex; flex-direction:column;
  position:fixed; top:0; left:0; bottom:0; z-index:200;
  transition:width var(--transition-base);
}
.sidenav.nav-collapsed { width:64px; }

.sidenav-logo {
  display:flex; align-items:center; gap:10px; padding:1.25rem 1rem;
  border-bottom:1px solid rgba(255,255,255,.07);
}
.logo-icon { width:32px; height:32px; background:var(--blue-500); border-radius:var(--radius-md); display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.logo-text { font-family:var(--font-display); font-size:1rem; color:var(--white); white-space:nowrap; }

.sidenav-links { flex:1; padding:.75rem .75rem; display:flex; flex-direction:column; gap:2px; }
.nav-item {
  display:flex; align-items:center; gap:10px; padding:.625rem .75rem;
  border-radius:var(--radius-md); color:rgba(255,255,255,.5);
  font-size:13px; text-decoration:none; cursor:pointer; border:none;
  background:none; width:100%; transition:all var(--transition-fast);
}
.nav-item:hover { background:rgba(255,255,255,.07); color:rgba(255,255,255,.85); }
.nav-item.router-link-active { background:rgba(0,130,201,.25); color:var(--white); }
.nav-badge { margin-left:auto; background:var(--blue-500); color:var(--white); font-size:10px; font-weight:600; padding:1px 6px; border-radius:var(--radius-full); }
.logout-btn { color:rgba(255,255,255,.4); }
.logout-btn:hover { color:var(--red-400); background:rgba(226,75,74,.1); }

.sidenav-bottom { padding:.75rem; border-top:1px solid rgba(255,255,255,.07); }
.user-card { display:flex; align-items:center; gap:10px; padding:.5rem .75rem; border-radius:var(--radius-md); cursor:pointer; margin-bottom:4px; }
.user-card:hover { background:rgba(255,255,255,.06); }
.avatar { width:30px; height:30px; border-radius:50%; background:var(--blue-500); color:var(--white); font-size:11px; font-weight:600; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.user-info { overflow:hidden; }
.user-name { font-size:12px; font-weight:500; color:var(--white); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.plan-chip { font-size:9px; font-weight:600; background:var(--blue-500); color:var(--white); padding:1px 6px; border-radius:var(--radius-full); }

.main-area { margin-left:240px; flex:1; display:flex; flex-direction:column; transition:margin-left var(--transition-base); }
.nav-collapsed ~ .main-area { margin-left:64px; }

.topbar { background:var(--white); border-bottom:1px solid var(--border); height:56px; display:flex; align-items:center; padding:0 1.5rem; gap:1rem; position:sticky; top:0; z-index:100; }
.collapse-btn { width:32px; height:32px; border-radius:var(--radius-md); border:1px solid var(--border); background:var(--white); cursor:pointer; display:flex; align-items:center; justify-content:center; color:var(--muted); }
.collapse-btn:hover { background:var(--surface); }
.topbar-title { font-size:15px; font-weight:500; color:var(--ink); }
.topbar-right { margin-left:auto; display:flex; align-items:center; gap:.75rem; }
.upgrade-chip { font-size:11px; font-weight:600; background:var(--blue-500); color:var(--white); padding:4px 12px; border-radius:var(--radius-full); text-decoration:none; }
.icon-btn { width:32px; height:32px; border-radius:var(--radius-md); border:1px solid var(--border); background:var(--white); display:flex; align-items:center; justify-content:center; cursor:pointer; color:var(--muted); }
.page-content { padding:1.5rem; flex:1; }

.page-enter-active { animation:page-in .2s ease; }
.page-leave-active { animation:page-out .15s ease forwards; }
@keyframes page-in { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
@keyframes page-out { to { opacity:0; transform:translateY(-4px); } }

@media(max-width:768px) {
  .sidenav { transform:translateX(-100%); }
  .main-area { margin-left:0; }
}
</style>
