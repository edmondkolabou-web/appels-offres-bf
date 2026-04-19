<!-- NetSync Gov Institutions — Dashboard acheteur public -->
<template>
  <div class="institution-page">

    <!-- En-tête institution -->
    <div class="institution-header card">
      <div class="inst-identity">
        <div class="inst-logo-wrap">
          <img v-if="inst.logo_url" :src="inst.logo_url" :alt="inst.nom" class="inst-logo">
          <div v-else class="inst-logo-placeholder">{{ inst.sigle || inst.nom?.charAt(0) }}</div>
        </div>
        <div>
          <div class="inst-badges">
            <span class="badge badge-type">{{ inst.type?.replace('_', ' ') }}</span>
            <span v-if="inst.verifie" class="badge badge-verifie">✓ Vérifié</span>
            <span class="badge" :class="`badge-${inst.plan}`">{{ inst.plan?.toUpperCase() }}</span>
          </div>
          <h1 class="inst-nom">{{ inst.nom }}</h1>
          <p class="inst-meta">{{ inst.region }} · {{ inst.email }}</p>
        </div>
      </div>
      <div class="inst-actions">
        <button class="btn btn-ghost" @click="$router.push(`/institutions/${inst.slug}`)">
          Voir profil public →
        </button>
        <button class="btn btn-primary" @click="downloadRapport" :disabled="generating">
          <svg v-if="!generating" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          {{ generating ? 'Génération…' : 'Rapport PDF' }}
        </button>
      </div>
    </div>

    <AppSpinner v-if="loading" label="Chargement du tableau de bord..." />

    <template v-else-if="dashboard">
      <!-- KPIs -->
      <div class="kpi-grid">
        <div class="kpi-card card">
          <div class="kpi-label">Total AOs publiés</div>
          <div class="kpi-val">{{ dashboard.stats.total_ao }}</div>
          <div class="kpi-sub">Depuis le démarrage</div>
        </div>
        <div class="kpi-card card">
          <div class="kpi-label">En cours</div>
          <div class="kpi-val kpi-green">{{ dashboard.stats.ao_ouverts }}</div>
          <div class="kpi-sub">AOs ouverts actuellement</div>
        </div>
        <div class="kpi-card card">
          <div class="kpi-label">Ce mois</div>
          <div class="kpi-val kpi-blue">{{ dashboard.stats.ao_ce_mois }}</div>
          <div class="kpi-sub">AOs publiés ce mois</div>
        </div>
        <div class="kpi-card card">
          <div class="kpi-label">Montant total estimé</div>
          <div class="kpi-val kpi-sm">{{ formatMontant(dashboard.stats.montant_total) }}</div>
          <div class="kpi-sub">Tous marchés confondus</div>
        </div>
        <div class="kpi-card card">
          <div class="kpi-label">Délai moyen</div>
          <div class="kpi-val">{{ dashboard.stats.delai_moyen_j || '—' }} <span class="kpi-unit">j</span></div>
          <div class="kpi-sub">Publication → clôture</div>
        </div>
        <div class="kpi-card card">
          <div class="kpi-label">Attribués</div>
          <div class="kpi-val">{{ dashboard.stats.ao_attribues }}</div>
          <div class="kpi-sub">Marchés finalisés</div>
        </div>
      </div>

      <!-- AOs urgents -->
      <div v-if="dashboard.ao_urgents?.length" class="card urgent-card">
        <h2 class="section-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--red-400)" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          Clôtures imminentes ({{ dashboard.ao_urgents.length }})
        </h2>
        <div class="urgent-list">
          <div v-for="ao in dashboard.ao_urgents" :key="ao.id" class="urgent-item"
               @click="$router.push(`/aos/${ao.id}`)">
            <div class="urgent-item-info">
              <p class="urgent-titre">{{ ao.titre }}</p>
              <span class="tag">{{ ao.secteur }}</span>
            </div>
            <div class="urgent-countdown" :class="ao.jours_restants <= 3 ? 'critique' : 'proche'">
              J-{{ ao.jours_restants }}
            </div>
          </div>
        </div>
      </div>

      <!-- Graphiques -->
      <div class="charts-row">

        <!-- Évolution 6 mois -->
        <div class="card chart-card">
          <h2 class="section-title">Évolution 6 mois</h2>
          <svg v-if="dashboard.evolution_6m?.length"
               :viewBox="`0 0 400 140`" width="100%" height="140">
            <g v-for="(pt, i) in dashboard.evolution_6m" :key="pt.mois">
              <rect
                :x="20 + i * (360 / dashboard.evolution_6m.length)"
                :y="20 + (1 - pt.nb / maxEvo) * 90"
                :width="(360 / dashboard.evolution_6m.length) - 6"
                :height="(pt.nb / maxEvo) * 90"
                fill="#0082C9" opacity="0.8" rx="3"
              />
              <text
                :x="20 + i * (360 / dashboard.evolution_6m.length) + (360 / dashboard.evolution_6m.length - 6) / 2"
                y="128" text-anchor="middle" font-size="9" fill="var(--color-text-secondary)">
                {{ pt.mois.slice(5) }}
              </text>
              <text
                :x="20 + i * (360 / dashboard.evolution_6m.length) + (360 / dashboard.evolution_6m.length - 6) / 2"
                :y="16 + (1 - pt.nb / maxEvo) * 90" text-anchor="middle" font-size="9"
                fill="var(--color-text-primary)">
                {{ pt.nb }}
              </text>
            </g>
          </svg>
          <p v-else class="chart-empty">Pas encore de données</p>
        </div>

        <!-- Répartition sectorielle -->
        <div class="card chart-card">
          <h2 class="section-title">Par secteur</h2>
          <div class="secteur-bars">
            <div v-for="s in dashboard.par_secteur" :key="s.secteur" class="secteur-row">
              <span class="secteur-label">{{ s.secteur }}</span>
              <div class="secteur-bar-bg">
                <div class="secteur-bar-fill"
                     :style="{ width: (s.nb / maxSecteur * 100) + '%' }"></div>
              </div>
              <span class="secteur-count">{{ s.nb }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Notification ciblée -->
      <div class="card notif-card" v-if="inst.plan !== 'gratuit'">
        <h2 class="section-title">Notifier des soumissionnaires qualifiés</h2>
        <p class="notif-desc">
          Envoyez une notification ciblée aux abonnés NetSync Gov spécialisés dans vos secteurs.
          Tarif : 5 000 FCFA par envoi.
        </p>
        <div class="notif-form">
          <div class="notif-secteurs">
            <label v-for="s in secteursDispo" :key="s">
              <input type="checkbox" :value="s" v-model="secteursCibles">
              {{ s }}
            </label>
          </div>
          <select v-model="aoSelectionne" class="notif-select" aria-label="Sélectionner un AO">
            <option value="">Sélectionner un AO…</option>
            <option v-for="ao in dashboard.ao_urgents" :key="ao.id" :value="ao.id">
              {{ ao.titre?.slice(0, 60) }}…
            </option>
          </select>
          <button class="btn btn-primary" @click="envoyerNotification"
                  :disabled="!aoSelectionne || !secteursCibles.length || envoi">
            {{ envoi ? 'Envoi…' : 'Envoyer la notification (5 000 FCFA)' }}
          </button>
        </div>
      </div>

      <!-- Upgrade si gratuit -->
      <div v-else class="card upgrade-card">
        <h2 class="section-title">Passez à l'abonnement institutionnel</h2>
        <p>Accédez aux notifications ciblées, aux rapports enrichis et au badge vérifié.</p>
        <div class="upgrade-plans">
          <div class="upgrade-plan">
            <div class="upgrade-plan-nom">Collectivité</div>
            <div class="upgrade-plan-prix">35 000 FCFA <span>/mois</span></div>
            <div class="upgrade-plan-cible">Mairies, communes</div>
            <button class="btn btn-ghost">Souscrire</button>
          </div>
          <div class="upgrade-plan featured">
            <div class="upgrade-plan-nom">Institutionnel</div>
            <div class="upgrade-plan-prix">75 000 FCFA <span>/mois</span></div>
            <div class="upgrade-plan-cible">Ministères, EPA, projets</div>
            <button class="btn btn-primary">Souscrire</button>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToastStore } from '@/stores/toast'
import AppSpinner from '@/components/ui/AppSpinner.vue'
import api from '@/api'

const toast     = useToastStore()
const loading   = ref(true)
const generating = ref(false)
const envoi     = ref(false)
const dashboard = ref(null)
const inst      = ref({})
const secteursCibles  = ref([])
const aoSelectionne   = ref('')

const secteursDispo = [
  'btp', 'informatique', 'sante', 'agriculture',
  'conseil', 'transport', 'energie', 'education'
]

const maxEvo     = computed(() => Math.max(...(dashboard.value?.evolution_6m || []).map(e => e.nb), 1))
const maxSecteur = computed(() => Math.max(...(dashboard.value?.par_secteur || []).map(s => s.nb), 1))

function formatMontant(v) {
  if (!v) return 'N/A'
  if (v >= 1_000_000_000) return (v / 1_000_000_000).toFixed(1) + ' Mrd FCFA'
  if (v >= 1_000_000)     return (v / 1_000_000).toFixed(0) + ' M FCFA'
  return v.toLocaleString('fr-FR') + ' FCFA'
}

async function loadDashboard() {
  try {
    const { data } = await api.get('/mon-institution/dashboard')
    dashboard.value = data
    inst.value = data.institution
  } catch {
    toast.add('Erreur chargement dashboard', 'error')
  } finally {
    loading.value = false
  }
}

async function downloadRapport() {
  generating.value = true
  try {
    const resp = await api.get('/mon-institution/rapport-activite', { responseType: 'blob' })
    const url = URL.createObjectURL(resp.data)
    const a   = document.createElement('a')
    a.href = url
    a.download = `rapport_netsync_${new Date().toISOString().slice(0,7)}.pdf`
    a.click()
    URL.revokeObjectURL(url)
    toast.add('Rapport téléchargé', 'success')
  } catch {
    toast.add('Erreur génération rapport', 'error')
  } finally {
    generating.value = false
  }
}

async function envoyerNotification() {
  if (!aoSelectionne.value || !secteursCibles.value.length) return
  envoi.value = true
  try {
    const { data } = await api.post('/mon-institution/notifier-soumissionnaires', {
      ao_id: aoSelectionne.value,
      secteurs_cibles: secteursCibles.value,
    })
    toast.add(data.message, 'success')
    secteursCibles.value = []
    aoSelectionne.value  = ''
  } catch {
    toast.add('Erreur lors de la notification', 'error')
  } finally {
    envoi.value = false
  }
}

onMounted(loadDashboard)
</script>

<style scoped>
.institution-page { display:flex; flex-direction:column; gap:1rem; }
.institution-header { display:flex; align-items:flex-start; justify-content:space-between; padding:1.25rem; flex-wrap:wrap; gap:1rem; }
.inst-identity { display:flex; align-items:flex-start; gap:1rem; }
.inst-logo { width:56px; height:56px; object-fit:contain; border-radius:var(--radius-md); }
.inst-logo-placeholder { width:56px; height:56px; background:var(--blue-50); color:var(--blue-600); border-radius:var(--radius-md); display:flex; align-items:center; justify-content:center; font-family:var(--font-display); font-size:1.25rem; font-weight:600; }
.inst-badges { display:flex; gap:.375rem; flex-wrap:wrap; margin-bottom:.375rem; }
.badge { font-size:10px; font-weight:600; padding:2px 8px; border-radius:var(--radius-full); text-transform:capitalize; }
.badge-type { background:var(--surface-2); color:var(--muted); }
.badge-verifie { background:var(--green-50); color:var(--green-600); }
.badge-gratuit { background:var(--surface-2); color:var(--muted); }
.badge-institutionnel { background:var(--blue-50); color:var(--blue-600); }
.badge-collectivite { background:var(--purple-50); color:var(--purple-600); }
.inst-nom { font-family:var(--font-display); font-size:1.25rem; color:var(--ink); }
.inst-meta { font-size:12px; color:var(--muted); margin-top:.25rem; }
.inst-actions { display:flex; gap:.5rem; align-items:center; }

.kpi-grid { display:grid; grid-template-columns:repeat(6, 1fr); gap:.75rem; }
.kpi-card { padding:1rem; }
.kpi-label { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; margin-bottom:.25rem; }
.kpi-val { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); line-height:1; }
.kpi-val.kpi-sm { font-size:1rem; }
.kpi-green { color:var(--green-400); }
.kpi-blue  { color:var(--blue-500); }
.kpi-unit  { font-size:.75rem; color:var(--muted); }
.kpi-sub   { font-size:10px; color:var(--muted); margin-top:.25rem; }

.section-title { font-size:13px; font-weight:600; color:var(--ink); margin-bottom:.75rem; display:flex; align-items:center; gap:.375rem; }
.urgent-card { padding:1rem; }
.urgent-list { display:flex; flex-direction:column; gap:.5rem; }
.urgent-item { display:flex; align-items:center; justify-content:space-between; padding:.625rem; border:1px solid var(--border); border-radius:var(--radius-md); cursor:pointer; }
.urgent-item:hover { background:var(--surface-2); }
.urgent-titre { font-size:12px; font-weight:500; color:var(--ink); }
.urgent-countdown { font-family:var(--font-mono); font-size:12px; font-weight:700; padding:3px 8px; border-radius:var(--radius-full); }
.urgent-countdown.critique { background:var(--red-50); color:var(--red-600); }
.urgent-countdown.proche   { background:var(--amber-50); color:var(--amber-600); }

.charts-row { display:grid; grid-template-columns:1fr 1fr; gap:1rem; }
.chart-card { padding:1rem; }
.chart-empty { font-size:12px; color:var(--muted); text-align:center; padding:2rem 0; }
.secteur-bars { display:flex; flex-direction:column; gap:.5rem; }
.secteur-row { display:flex; align-items:center; gap:.5rem; }
.secteur-label { font-size:11px; color:var(--ink-500); width:80px; flex-shrink:0; }
.secteur-bar-bg { flex:1; height:8px; background:var(--surface-2); border-radius:4px; overflow:hidden; }
.secteur-bar-fill { height:100%; background:var(--blue-500); border-radius:4px; }
.secteur-count { font-size:11px; font-weight:600; color:var(--blue-600); width:24px; text-align:right; }

.notif-card { padding:1rem; }
.notif-desc { font-size:12px; color:var(--muted); margin-bottom:.75rem; }
.notif-form { display:flex; flex-direction:column; gap:.75rem; }
.notif-secteurs { display:flex; flex-wrap:wrap; gap:.5rem; }
.notif-secteurs label { display:flex; align-items:center; gap:.375rem; font-size:12px; cursor:pointer; }
.notif-select { font-family:var(--font-body); font-size:12px; border:1px solid var(--border-md); border-radius:var(--radius-md); padding:8px 12px; background:var(--white); color:var(--ink); }

.upgrade-card { padding:1rem; }
.upgrade-plans { display:flex; gap:1rem; margin-top:1rem; flex-wrap:wrap; }
.upgrade-plan { border:1px solid var(--border-md); border-radius:var(--radius-lg); padding:1rem; flex:1; min-width:160px; }
.upgrade-plan.featured { border-color:var(--blue-400); background:var(--blue-50); }
.upgrade-plan-nom { font-size:13px; font-weight:600; color:var(--ink); }
.upgrade-plan-prix { font-family:var(--font-display); font-size:1.25rem; color:var(--blue-600); margin:.375rem 0; }
.upgrade-plan-prix span { font-size:12px; color:var(--muted); }
.upgrade-plan-cible { font-size:11px; color:var(--muted); margin-bottom:.75rem; }

@media(max-width:1024px) {
  .kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .charts-row { grid-template-columns: 1fr; }
}
</style>
