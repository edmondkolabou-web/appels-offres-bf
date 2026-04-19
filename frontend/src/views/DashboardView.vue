<template>
  <div class="dashboard">
    <!-- Banner urgence -->
    <div v-if="urgentCount > 0" class="urgent-banner" role="alert">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
      <strong>{{ urgentCount }} AO</strong> clôturent dans moins de 48h.
      <RouterLink to="/aos?urgent_only=true">Voir →</RouterLink>
    </div>

    <!-- KPIs -->
    <div class="kpi-grid">
      <div class="kpi-card card accent">
        <div class="kpi-icon blue"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/></svg></div>
        <div class="kpi-val">{{ stats.todayCount }}</div>
        <div class="kpi-label">AOs publiés aujourd'hui</div>
        <div class="kpi-trend up">↑ Mis à jour à 07h00</div>
      </div>
      <div class="kpi-card card">
        <div class="kpi-icon red"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
        <div class="kpi-val">{{ urgentCount }}</div>
        <div class="kpi-label">Clôtures dans 48h</div>
        <div class="kpi-trend down">Action requise</div>
      </div>
      <div class="kpi-card card">
        <div class="kpi-icon green"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg></div>
        <div class="kpi-val">{{ favorisStore.items.length }}</div>
        <div class="kpi-label">AO enregistrés</div>
      </div>
      <div class="kpi-card card">
        <div class="kpi-icon amber"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/></svg></div>
        <div class="kpi-val">{{ alertesStore.items.filter(a => a.actif).length }}</div>
        <div class="kpi-label">Alertes actives</div>
      </div>
    </div>

    <div class="dash-grid">
      <!-- AOs du jour -->
      <div class="card dash-main">
        <div class="section-head">
          <h2 class="section-title">AOs publiés ce matin</h2>
          <RouterLink to="/aos" class="view-all-link">Voir tous →</RouterLink>
        </div>
        <AppSpinner v-if="loadingToday" />
        <div v-else-if="todayAOs.length" class="ao-mini-list">
          <div v-for="ao in todayAOs.slice(0,5)" :key="ao.id" class="ao-mini-item" @click="$router.push(`/aos/${ao.id}`)">
            <div class="ao-mini-tags">
              <span class="tag" :class="`tag-${ao.statut}`">{{ ao.statut }}</span>
              <span class="tag" :class="`tag-${ao.secteur}`">{{ ao.secteur }}</span>
              <span v-if="ao.est_urgent" class="tag tag-urgent">J-{{ ao.jours_restants }}</span>
            </div>
            <p class="ao-mini-title">{{ ao.titre }}</p>
            <p class="ao-mini-meta">{{ ao.autorite_contractante }}</p>
          </div>
        </div>
        <div v-else class="empty-mini">Aucun AO publié aujourd'hui</div>
      </div>

      <!-- Sidebar -->
      <div class="dash-side">
        <!-- Alertes rapides -->
        <div class="card">
          <div class="section-head">
            <h2 class="section-title">Mes alertes</h2>
            <RouterLink to="/alertes" class="view-all-link">Gérer</RouterLink>
          </div>
          <div v-if="alertesStore.items.length">
            <div v-for="al in alertesStore.items.slice(0,3)" :key="al.id" class="alerte-mini">
              <div class="alerte-info">
                <p class="alerte-secteurs">{{ al.secteurs.join(', ') || 'Tous secteurs' }}</p>
                <p class="alerte-canal">{{ al.canal }} · {{ al.rappel_j3 ? 'Rappel J-3 activé' : '' }}</p>
              </div>
              <div class="toggle" :class="{ on: al.actif }" @click="alertesStore.toggle(al.id)" :aria-label="al.actif ? 'Désactiver' : 'Activer'"><div class="toggle-thumb"></div></div>
            </div>
          </div>
          <div v-else class="empty-mini">Aucune alerte configurée</div>
          <RouterLink to="/alertes" class="btn btn-ghost" style="width:100%;justify-content:center;margin-top:.75rem;font-size:12px;">+ Nouvelle alerte</RouterLink>
        </div>

        <!-- Upgrade si gratuit -->
        <div v-if="!authStore.isPro" class="upgrade-card">
          <h3 class="upgrade-title">Passer au plan Pro</h3>
          <p class="upgrade-desc">AOs illimités + alertes WhatsApp + rappels J-3.</p>
          <RouterLink to="/pricing" class="btn btn-primary" style="width:100%;justify-content:center;">Voir les tarifs →</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAOStore } from '@/stores/aos'
import { useFavorisStore } from '@/stores/favoris'
import { useAlertesStore } from '@/stores/alertes'
import { useAuthStore } from '@/stores/auth'
import AppSpinner from '@/components/ui/AppSpinner.vue'

const aoStore      = useAOStore()
const favorisStore = useFavorisStore()
const alertesStore = useAlertesStore()
const authStore    = useAuthStore()

const todayAOs     = ref([])
const urgentAOs    = ref([])
const loadingToday = ref(true)

const urgentCount = computed(() => urgentAOs.value.length)
const stats       = computed(() => ({ todayCount: todayAOs.value.length }))

onMounted(async () => {
  await Promise.all([
    favorisStore.fetch(),
    alertesStore.fetch(),
    (async () => {
      const { aoApi } = await import('@/api')
      const [today, urgent] = await Promise.all([aoApi.today(), aoApi.urgent()])
      todayAOs.value  = today.data.items
      urgentAOs.value = urgent.data.items
      loadingToday.value = false
    })(),
  ])
})
</script>

<style scoped>
.dashboard { display:flex; flex-direction:column; gap:1rem; }
.urgent-banner { background:var(--amber-50); border:1px solid #F0D5A0; border-radius:var(--radius-lg); padding:.875rem 1.25rem; display:flex; align-items:center; gap:.75rem; font-size:13px; color:var(--amber-600); }
.urgent-banner a { color:var(--blue-500); text-decoration:none; margin-left:auto; font-weight:500; }
.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; }
.kpi-card { padding:1.25rem; }
.kpi-card.accent { border-color:var(--blue-200); background:var(--blue-50); }
.kpi-icon { width:34px; height:34px; border-radius:var(--radius-md); display:flex; align-items:center; justify-content:center; margin-bottom:.75rem; }
.kpi-icon.blue  { background:var(--blue-50);  color:var(--blue-500); }
.kpi-icon.red   { background:var(--red-50);   color:var(--red-400); }
.kpi-icon.green { background:var(--green-50); color:var(--green-400); }
.kpi-icon.amber { background:var(--amber-50); color:var(--amber-400); }
.kpi-val   { font-family:var(--font-display); font-size:1.8rem; color:var(--ink); line-height:1; }
.kpi-label { font-size:12px; color:var(--muted); margin-top:3px; }
.kpi-trend { font-size:11px; font-weight:500; margin-top:6px; }
.kpi-trend.up   { color:var(--green-400); }
.kpi-trend.down { color:var(--red-400); }
.dash-grid { display:grid; grid-template-columns:1fr 320px; gap:1rem; }
.dash-main, .dash-side > .card { padding:1.25rem; }
.dash-side { display:flex; flex-direction:column; gap:1rem; }
.section-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem; }
.section-title { font-size:14px; font-weight:600; color:var(--ink); }
.view-all-link { font-size:12px; color:var(--blue-500); text-decoration:none; }
.ao-mini-list { display:flex; flex-direction:column; }
.ao-mini-item { padding:.75rem 0; border-bottom:1px solid var(--border); cursor:pointer; }
.ao-mini-item:last-child { border-bottom:none; }
.ao-mini-item:hover { background:var(--surface); border-radius:var(--radius-md); padding-left:.5rem; }
.ao-mini-tags { display:flex; gap:4px; flex-wrap:wrap; margin-bottom:.3rem; }
.ao-mini-title { font-size:12px; font-weight:500; color:var(--ink); line-height:1.4; margin-bottom:.2rem; }
.ao-mini-meta  { font-size:11px; color:var(--muted); }
.alerte-mini { display:flex; align-items:center; gap:.75rem; padding:.625rem 0; border-bottom:1px solid var(--border); }
.alerte-mini:last-child { border-bottom:none; }
.alerte-info { flex:1; }
.alerte-secteurs { font-size:12px; font-weight:500; color:var(--ink); }
.alerte-canal    { font-size:11px; color:var(--muted); }
.empty-mini { font-size:12px; color:var(--muted); padding:.5rem 0; }
.upgrade-card { background:var(--ink); border-radius:var(--radius-xl); padding:1.25rem; }
.upgrade-title { font-family:var(--font-display); font-size:1rem; color:var(--white); margin-bottom:.375rem; }
.upgrade-desc  { font-size:12px; color:rgba(255,255,255,.55); margin-bottom:1rem; line-height:1.5; }
@media(max-width:1100px) { .dash-grid { grid-template-columns:1fr; } }
@media(max-width:900px)  { .kpi-grid { grid-template-columns:1fr 1fr; } }
</style>
