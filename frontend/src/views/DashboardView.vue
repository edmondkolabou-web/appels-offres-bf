<template>
  <div class="dashboard">
    <!-- Greeting -->
    <div class="dash-header">
      <div>
        <p class="greeting">Bonjour, {{ authStore.abonne?.prenom || 'utilisateur' }} 👋</p>
        <h1 class="page-title">Tableau de bord</h1>
      </div>
      <div class="dash-date">{{ formattedDate }}</div>
    </div>

    <!-- Banner urgence -->
    <div v-if="urgentCount > 0" class="urgent-banner" role="alert">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
      <strong>{{ urgentCount }} AO{{ urgentCount > 1 ? 's' : '' }}</strong> {{ urgentCount > 1 ? 'clôturent' : 'clôture' }} dans moins de 72h.
      <RouterLink to="/aos?urgent_only=true">Voir →</RouterLink>
    </div>

    <!-- KPIs -->
    <div class="kpi-grid">
      <div class="kpi-card card accent">
        <div class="kpi-top">
          <div class="kpi-icon blue"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>
          <span class="kpi-trend up" v-if="stats.todayCount > 0">↑ +{{ stats.todayCount }}</span>
        </div>
        <div class="kpi-val">{{ stats.totalMonth }}</div>
        <div class="kpi-label">AOs ce mois</div>
      </div>
      <div class="kpi-card card">
        <div class="kpi-top">
          <div class="kpi-icon green"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>
          <span class="kpi-trend up">{{ stats.todayCount }} aujourd'hui</span>
        </div>
        <div class="kpi-val">{{ matchCount }}</div>
        <div class="kpi-label">Correspondant à mes alertes</div>
      </div>
      <div class="kpi-card card">
        <div class="kpi-top">
          <div class="kpi-icon amber"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
          <span class="kpi-trend warn" v-if="urgentCount > 0">⚠ Action requise</span>
        </div>
        <div class="kpi-val">{{ urgentCount }}</div>
        <div class="kpi-label">Clôtures cette semaine</div>
      </div>
      <div class="kpi-card card">
        <div class="kpi-top">
          <div class="kpi-icon muted"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg></div>
        </div>
        <div class="kpi-val">{{ favorisStore.items.length }}</div>
        <div class="kpi-label">AO enregistrés</div>
      </div>
    </div>

    <div class="dash-grid">
      <!-- Main content -->
      <div class="dash-main">
        <!-- Tabs -->
        <div class="dash-tabs">
          <button :class="['tab', { active: activeTab === 'today' }]" @click="activeTab = 'today'">Nouveaux AOs</button>
          <button :class="['tab', { active: activeTab === 'calendar' }]" @click="activeTab = 'calendar'">Calendrier clôtures</button>
          <button :class="['tab', { active: activeTab === 'sectors' }]" @click="activeTab = 'sectors'">Par secteur</button>
        </div>

        <!-- Tab: AOs du jour -->
        <div v-if="activeTab === 'today'" class="card tab-content">
          <div class="section-head">
            <h2 class="section-title">AOs publiés ce matin</h2>
            <RouterLink to="/aos" class="view-all-link">Voir tous →</RouterLink>
          </div>
          <AppSpinner v-if="loadingToday" />
          <div v-else-if="todayAOs.length" class="ao-mini-list">
            <div v-for="ao in todayAOs.slice(0, 6)" :key="ao.id" class="ao-mini-item" @click="$router.push(`/aos/${ao.id}`)">
              <div class="ao-mini-tags">
                <span class="tag" :class="`tag-${ao.statut}`">{{ ao.statut }}</span>
                <span class="tag" :class="`tag-${ao.secteur}`">{{ ao.secteur }}</span>
                <span v-if="ao.est_urgent" class="tag tag-urgent">J-{{ ao.jours_restants }}</span>
              </div>
              <p class="ao-mini-title">{{ ao.titre }}</p>
              <div class="ao-mini-bottom">
                <span class="ao-mini-meta">{{ ao.autorite_contractante }}</span>
                <span v-if="ao.date_cloture" class="ao-mini-date">Clôture : {{ formatDate(ao.date_cloture) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <p>Aucun AO publié aujourd'hui — les publications arrivent vers 7h00.</p>
          </div>
        </div>

        <!-- Tab: Calendrier clôtures -->
        <div v-if="activeTab === 'calendar'" class="card tab-content">
          <div class="section-head">
            <h2 class="section-title">Clôtures à venir</h2>
          </div>
          <div v-if="urgentAOs.length" class="deadline-list">
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
        </div>

        <!-- Tab: Par secteur -->
        <div v-if="activeTab === 'sectors'" class="card tab-content">
          <div class="section-head">
            <h2 class="section-title">Répartition par secteur</h2>
          </div>
          <div v-if="secteurs.length" class="sector-bars">
            <div v-for="s in secteurs" :key="s.secteur" class="sector-row">
              <div class="sector-label">{{ s.secteur || 'autre' }}</div>
              <div class="sector-bar-wrap">
                <div class="sector-bar" :style="{ width: sectorWidth(s.nb_ao) + '%' }" :class="`bar-${s.secteur}`"></div>
              </div>
              <div class="sector-count">{{ s.nb_ao }}</div>
            </div>
          </div>
          <div v-else class="empty-state"><p>Chargement des secteurs...</p></div>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="dash-side">
        <!-- Notifications récentes -->
        <div class="card">
          <div class="section-head">
            <h2 class="section-title">Notifications</h2>
          </div>
          <div class="notif-list">
            <div v-for="n in notifications" :key="n.id" class="notif-item" :class="{ unread: n.unread }">
              <span class="notif-icon">{{ n.icon }}</span>
              <div class="notif-body">
                <p class="notif-text">{{ n.text }}</p>
                <p class="notif-time">{{ n.time }}</p>
              </div>
            </div>
            <div v-if="!notifications.length" class="empty-mini">Aucune notification</div>
          </div>
        </div>

        <!-- Alertes rapides -->
        <div class="card">
          <div class="section-head">
            <h2 class="section-title">Mes alertes</h2>
            <RouterLink to="/alertes" class="view-all-link">Gérer</RouterLink>
          </div>
          <div v-if="alertesStore.items.length">
            <div v-for="al in alertesStore.items.slice(0, 3)" :key="al.id" class="alerte-mini">
              <div class="alerte-info">
                <p class="alerte-secteurs">{{ al.secteurs?.join(', ') || 'Tous secteurs' }}</p>
                <p class="alerte-canal">
                  {{ al.canal_email ? '📧' : '' }}{{ al.canal_whatsapp ? ' 📱' : '' }}
                  {{ al.rappel_j3 ? ' · Rappel J-3' : '' }}
                </p>
              </div>
              <div class="toggle-mini" :class="{ on: al.actif }" @click="alertesStore.toggle(al.id)">
                <div class="toggle-thumb"></div>
              </div>
            </div>
          </div>
          <div v-else class="empty-mini">Aucune alerte configurée</div>
          <RouterLink to="/alertes" class="btn btn-ghost" style="width:100%;justify-content:center;margin-top:.75rem;font-size:12px;">+ Nouvelle alerte</RouterLink>
        </div>

        <!-- Activité récente -->
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

        <!-- Upgrade CTA si gratuit -->
        <div v-if="!authStore.isPro" class="upgrade-card">
          <h3 class="upgrade-title">Passer au plan Pro</h3>
          <p class="upgrade-desc">AOs illimités + alertes WhatsApp + rappels J-3.</p>
          <div class="upgrade-fomo" v-if="stats.totalMonth > 3">
            📊 {{ stats.totalMonth }} AOs ce mois — tu n'en vois que 3/jour.
          </div>
          <RouterLink to="/pricing" class="btn btn-primary" style="width:100%;justify-content:center;">Voir les tarifs →</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useFavorisStore } from '@/stores/favoris'
import { useAlertesStore } from '@/stores/alertes'
import AppSpinner from '@/components/ui/AppSpinner.vue'

const authStore    = useAuthStore()
const favorisStore = useFavorisStore()
const alertesStore = useAlertesStore()

const todayAOs     = ref([])
const urgentAOs    = ref([])
const secteurs     = ref([])
const loadingToday = ref(true)
const activeTab    = ref('today')

const urgentCount = computed(() => urgentAOs.value.length)
const matchCount  = computed(() => {
  // Estimation : AOs du jour dans les secteurs de mes alertes
  const mySecteurs = alertesStore.items.flatMap(a => a.secteurs || [])
  if (!mySecteurs.length) return todayAOs.value.length
  return todayAOs.value.filter(ao => mySecteurs.includes(ao.secteur)).length
})

const stats = computed(() => ({
  todayCount: todayAOs.value.length,
  totalMonth: todayAOs.value.length + urgentAOs.value.length + favorisStore.items.length,
}))

const maxSector = computed(() => Math.max(...secteurs.value.map(s => s.nb_ao), 1))
function sectorWidth(count) { return (count / maxSector.value) * 100 }

const formattedDate = computed(() => {
  const d = new Date()
  const days = ['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi']
  const months = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
  return `${days[d.getDay()]} ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const months = ['jan.','fév.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.']
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`
}

function deadlineClass(days) {
  if (days <= 1) return 'deadline-critical'
  if (days <= 3) return 'deadline-warn'
  return 'deadline-ok'
}

// Notifications simulées (sera remplacé par un vrai endpoint)
const notifications = computed(() => {
  const notifs = []
  if (todayAOs.value.length > 0) {
    notifs.push({
      id: 'today', icon: '📊', unread: true,
      text: `${todayAOs.value.length} nouveau(x) AO(s) publiés ce matin`,
      time: 'Aujourd\'hui 07:02'
    })
  }
  if (urgentAOs.value.length > 0) {
    notifs.push({
      id: 'urgent', icon: '⏰', unread: true,
      text: `${urgentAOs.value.length} clôture(s) cette semaine`,
      time: 'Aujourd\'hui'
    })
  }
  if (alertesStore.items.filter(a => a.actif).length > 0) {
    notifs.push({
      id: 'alertes', icon: '🔔', unread: false,
      text: `${alertesStore.items.filter(a => a.actif).length} alerte(s) active(s)`,
      time: 'En cours'
    })
  }
  return notifs
})

const recentActivity = computed(() => {
  const acts = []
  acts.push({ id: 'login', text: 'Connexion au tableau de bord', time: 'À l\'instant', color: 'dot-blue' })
  if (todayAOs.value.length) acts.push({ id: 'ao', text: `${todayAOs.value.length} nouveaux AOs consultés`, time: 'Aujourd\'hui', color: 'dot-green' })
  if (favorisStore.items.length) acts.push({ id: 'fav', text: `${favorisStore.items.length} AO(s) en favoris`, time: 'En cours', color: 'dot-amber' })
  if (alertesStore.items.filter(a => a.actif).length) acts.push({ id: 'alert', text: `${alertesStore.items.filter(a => a.actif).length} alerte(s) active(s)`, time: 'Configurées', color: 'dot-blue' })
  return acts.slice(0, 5)
})

onMounted(async () => {
  await Promise.all([
    favorisStore.fetch(),
    alertesStore.fetch(),
    (async () => {
      const { aoApi } = await import('@/api')
      const [today, urgent, sects] = await Promise.all([
        aoApi.today(),
        aoApi.urgent(),
        aoApi.secteurs().catch(() => ({ data: [] })),
      ])
      todayAOs.value  = today.data.items || []
      urgentAOs.value = urgent.data.items || []
      secteurs.value  = sects.data || []
      loadingToday.value = false
    })(),
  ])
})
</script>

<style scoped>
.dashboard { display:flex; flex-direction:column; gap:1rem; }

/* Header */
.dash-header { display:flex; align-items:flex-end; justify-content:space-between; margin-bottom:.25rem; }
.greeting { font-size:13px; color:var(--muted); margin-bottom:2px; }
.page-title { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); }
.dash-date { font-size:12px; color:var(--muted); }

/* Urgent banner */
.urgent-banner { background:var(--amber-50); border:1px solid #F0D5A0; border-radius:var(--radius-lg); padding:.875rem 1.25rem; display:flex; align-items:center; gap:.75rem; font-size:13px; color:var(--amber-600); }
.urgent-banner a { color:var(--blue-500); text-decoration:none; margin-left:auto; font-weight:500; }

/* KPIs */
.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:.75rem; }
.kpi-card { padding:1.15rem; }
.kpi-card.accent { border-color:var(--blue-200); background:var(--blue-50); }
.kpi-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:.75rem; }
.kpi-icon { width:34px; height:34px; border-radius:var(--radius-md); display:flex; align-items:center; justify-content:center; }
.kpi-icon.blue  { background:var(--blue-50);  color:var(--blue-500); }
.kpi-icon.green { background:var(--green-50); color:var(--green-400); }
.kpi-icon.amber { background:var(--amber-50); color:var(--amber-400); }
.kpi-icon.muted { background:var(--surface);  color:var(--muted); }
.kpi-val   { font-family:var(--font-display); font-size:1.8rem; color:var(--ink); line-height:1; }
.kpi-label { font-size:12px; color:var(--muted); margin-top:3px; }
.kpi-trend { font-size:10px; font-weight:500; padding:2px 7px; border-radius:var(--radius-full); }
.kpi-trend.up   { background:var(--green-50); color:var(--green-600); }
.kpi-trend.warn { background:var(--amber-50); color:var(--amber-600); }

/* Layout */
.dash-grid { display:grid; grid-template-columns:1fr 300px; gap:1rem; }
.dash-main { display:flex; flex-direction:column; gap:0; }
.dash-side { display:flex; flex-direction:column; gap:1rem; }

/* Tabs */
.dash-tabs { display:flex; border-bottom:1px solid var(--border); margin-bottom:0; }
.tab { padding:10px 16px; font-size:13px; font-weight:500; color:var(--muted); cursor:pointer; border:none; background:none; border-bottom:2px solid transparent; margin-bottom:-1px; font-family:inherit; transition:all .15s; }
.tab:hover { color:var(--ink); }
.tab.active { color:var(--blue-500); border-bottom-color:var(--blue-500); }
.tab-content { border-radius:0 0 var(--radius-lg) var(--radius-lg); border-top:none; }

/* Section */
.section-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem; padding:1.15rem 1.15rem 0; }
.tab-content .section-head { padding:1.15rem 0 0; }
.tab-content { padding:0 1.15rem 1.15rem; }
.section-title { font-size:14px; font-weight:600; color:var(--ink); }
.view-all-link { font-size:12px; color:var(--blue-500); text-decoration:none; font-weight:500; }

/* AO list */
.ao-mini-list { display:flex; flex-direction:column; }
.ao-mini-item { padding:.75rem 0; border-bottom:1px solid var(--border); cursor:pointer; transition:background .12s; }
.ao-mini-item:last-child { border-bottom:none; }
.ao-mini-item:hover { background:var(--surface); border-radius:var(--radius-md); padding-left:.5rem; }
.ao-mini-tags { display:flex; gap:4px; flex-wrap:wrap; margin-bottom:.3rem; }
.ao-mini-title { font-size:13px; font-weight:500; color:var(--ink); line-height:1.4; margin-bottom:.25rem; }
.ao-mini-bottom { display:flex; align-items:center; justify-content:space-between; gap:.5rem; }
.ao-mini-meta  { font-size:11px; color:var(--muted); }
.ao-mini-date  { font-size:10px; color:var(--muted); white-space:nowrap; }

/* Deadlines */
.deadline-list { display:flex; flex-direction:column; gap:6px; }
.deadline-item { display:flex; align-items:center; gap:12px; padding:10px; border:1px solid var(--border); border-radius:var(--radius-md); cursor:pointer; transition:all .15s; }
.deadline-item:hover { border-color:var(--blue-200); box-shadow:0 2px 8px rgba(0,0,0,.04); }
.deadline-days { width:40px; height:40px; border-radius:var(--radius-md); display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; flex-shrink:0; }
.deadline-critical { background:var(--red-50); color:var(--red-400); }
.deadline-warn { background:var(--amber-50); color:var(--amber-600); }
.deadline-ok { background:var(--surface); color:var(--muted); }
.deadline-info { flex:1; min-width:0; }
.deadline-title { font-size:12px; font-weight:500; color:var(--ink); line-height:1.4; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.deadline-meta { font-size:11px; color:var(--muted); }

/* Sectors */
.sector-bars { display:flex; flex-direction:column; gap:8px; }
.sector-row { display:flex; align-items:center; gap:10px; }
.sector-label { font-size:12px; font-weight:500; color:var(--ink); width:100px; text-transform:capitalize; flex-shrink:0; }
.sector-bar-wrap { flex:1; height:8px; background:var(--surface); border-radius:4px; overflow:hidden; }
.sector-bar { height:100%; border-radius:4px; transition:width .5s ease; background:var(--blue-500); }
.bar-informatique { background:var(--blue-500); }
.bar-btp { background:#6366F1; }
.bar-sante { background:var(--green-400); }
.bar-conseil { background:var(--amber-400); }
.bar-equipement { background:#EC4899; }
.bar-agriculture { background:#10B981; }
.bar-education { background:#F59E0B; }
.bar-energie { background:#EF4444; }
.bar-autre { background:var(--muted); }
.sector-count { font-size:12px; font-weight:600; color:var(--ink); width:28px; text-align:right; }

/* Notifications */
.notif-list { display:flex; flex-direction:column; gap:4px; }
.notif-item { display:flex; align-items:flex-start; gap:8px; padding:8px 10px; border-radius:var(--radius-md); transition:background .12s; }
.notif-item.unread { background:var(--blue-50); border-left:2px solid var(--blue-500); }
.notif-icon { font-size:14px; flex-shrink:0; margin-top:1px; }
.notif-body { flex:1; }
.notif-text { font-size:12px; font-weight:500; color:var(--ink); line-height:1.4; margin-bottom:1px; }
.notif-time { font-size:10px; color:var(--muted); }

/* Alertes */
.alerte-mini { display:flex; align-items:center; gap:.75rem; padding:.625rem 0; border-bottom:1px solid var(--border); }
.alerte-mini:last-child { border-bottom:none; }
.alerte-info { flex:1; }
.alerte-secteurs { font-size:12px; font-weight:500; color:var(--ink); }
.alerte-canal    { font-size:11px; color:var(--muted); }

/* Toggle mini */
.toggle-mini { width:32px; height:18px; border-radius:9px; background:var(--border-md); position:relative; cursor:pointer; transition:background .2s; flex-shrink:0; }
.toggle-mini.on { background:var(--green-400); }
.toggle-mini .toggle-thumb { position:absolute; top:2px; left:2px; width:14px; height:14px; border-radius:50%; background:white; transition:transform .2s; box-shadow:0 1px 3px rgba(0,0,0,.1); }
.toggle-mini.on .toggle-thumb { transform:translateX(14px); }

/* Upgrade */
.upgrade-card { background:var(--ink); border-radius:var(--radius-xl); padding:1.25rem; }
.upgrade-title { font-family:var(--font-display); font-size:1rem; color:var(--white); margin-bottom:.375rem; }
.upgrade-desc  { font-size:12px; color:rgba(255,255,255,.55); margin-bottom:.75rem; line-height:1.5; }
.upgrade-fomo  { font-size:11px; color:rgba(255,255,255,.7); background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.1); border-radius:var(--radius-md); padding:8px 10px; margin-bottom:1rem; }

/* Empty */
.empty-state { text-align:center; padding:2rem 1rem; }
.empty-state p { font-size:13px; color:var(--muted); }
.empty-mini { font-size:12px; color:var(--muted); padding:.5rem 0; }

/* Activity */
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

/* Responsive */
@media(max-width:1100px) { .dash-grid { grid-template-columns:1fr; } }
@media(max-width:900px)  { .kpi-grid { grid-template-columns:1fr 1fr; } }
@media(max-width:600px)  { .kpi-grid { grid-template-columns:1fr; } .dash-header { flex-direction:column; align-items:flex-start; gap:.25rem; } }
</style>
