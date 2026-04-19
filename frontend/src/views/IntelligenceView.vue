<!-- NetSync Gov Intelligence — Dashboard tendances -->
<template>
  <div class="intelligence-page">

    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Intelligence marché</h1>
        <p class="page-sub">Analyse de la commande publique burkinabè — données DGCMEF</p>
      </div>
      <div class="header-actions">
        <select class="periode-select" v-model="periode" @change="fetchAll" aria-label="Sélectionner la période">
          <option value="3m">3 derniers mois</option>
          <option value="6m">6 derniers mois</option>
          <option value="12m">12 derniers mois</option>
          <option value="24m">24 derniers mois</option>
        </select>
        <button class="btn btn-primary" @click="downloadRapport" :disabled="generatingPDF">
          <svg v-if="!generatingPDF" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          <div v-else class="spinner"></div>
          {{ generatingPDF ? 'Génération…' : 'Rapport PDF' }}
        </button>
      </div>
    </div>

    <AppSpinner v-if="loading" size="lg" label="Chargement des analyses..." />

    <template v-else>
      <!-- KPIs résumé -->
      <div class="kpi-grid" v-if="resume">
        <div class="kpi-card card">
          <div class="kpi-label">AOs indexés</div>
          <div class="kpi-val">{{ resume.total_ao_indexes?.toLocaleString('fr-FR') }}</div>
          <div class="kpi-trend">Depuis le lancement</div>
        </div>
        <div class="kpi-card card">
          <div class="kpi-label">Ce mois</div>
          <div class="kpi-val">{{ resume.ao_ce_mois }}</div>
          <div class="kpi-trend" :class="resume.tendance_vs_mois_pct > 0 ? 'up' : 'down'">
            {{ resume.tendance_vs_mois_pct > 0 ? '↑' : '↓' }}
            {{ Math.abs(resume.tendance_vs_mois_pct) }}% vs mois dernier
          </div>
        </div>
        <div class="kpi-card card">
          <div class="kpi-label">Top secteur</div>
          <div class="kpi-val kpi-secteur">{{ resume.top_secteur_ce_mois?.toUpperCase() }}</div>
          <div class="kpi-trend">Ce mois</div>
        </div>
        <div class="kpi-card card">
          <div class="kpi-label">Hier</div>
          <div class="kpi-val">{{ resume.ao_hier }}</div>
          <div class="kpi-trend">AOs publiés</div>
        </div>
      </div>

      <!-- Graphiques -->
      <div class="charts-grid">

        <!-- Évolution mensuelle -->
        <div class="card chart-card">
          <h2 class="chart-title">Évolution mensuelle des AOs</h2>
          <div class="chart-filters">
            <button v-for="s in secteursFiltres" :key="s.val"
                    class="filter-pill" :class="{ active: secteurActif === s.val }"
                    @click="secteurActif = s.val; fetchEvolution()">
              {{ s.label }}
            </button>
          </div>
          <div class="chart-wrap" ref="evolutionChart">
            <!-- Graphique barres SVG inline -->
            <svg v-if="evolution.length" :viewBox="`0 0 ${chartW} ${chartH}`" width="100%" :height="chartH">
              <g v-for="(point, i) in evolution" :key="point.mois">
                <rect
                  :x="barX(i)" :y="barY(point.nb_ao)"
                  :width="barWidth" :height="chartH - 40 - barY(point.nb_ao)"
                  :fill="secteurActif ? '#0082C9' : '#0082C9'"
                  opacity="0.85" rx="3"
                  @mouseover="tooltip = point" @mouseleave="tooltip = null"
                  style="cursor:pointer;"
                />
                <text v-if="evolution.length <= 12"
                      :x="barX(i) + barWidth/2" :y="chartH - 25"
                      text-anchor="middle" font-size="10"
                      fill="var(--color-text-secondary)">
                  {{ point.mois_label?.slice(0,3) }}
                </text>
                <text :x="barX(i) + barWidth/2" :y="barY(point.nb_ao) - 4"
                      text-anchor="middle" font-size="10"
                      fill="var(--color-text-primary)">
                  {{ point.nb_ao }}
                </text>
              </g>
            </svg>
            <div v-if="tooltip" class="chart-tooltip">
              <strong>{{ tooltip.mois_label }}</strong><br>
              {{ tooltip.nb_ao }} AOs
            </div>
          </div>
        </div>

        <!-- Top secteurs barres horizontales -->
        <div class="card chart-card">
          <h2 class="chart-title">Volume par secteur</h2>
          <div class="secteurs-bars">
            <div v-for="s in secteurs.slice(0, 7)" :key="s.secteur" class="secteur-row">
              <span class="secteur-name">{{ s.secteur }}</span>
              <div class="secteur-bar-wrap">
                <div class="secteur-bar"
                     :style="{ width: (s.nb_ao / maxSecteur * 100) + '%' }"></div>
              </div>
              <span class="secteur-count">{{ s.nb_ao }}</span>
            </div>
          </div>
        </div>

        <!-- Top autorités -->
        <div class="card chart-card">
          <h2 class="chart-title">Top autorités contractantes</h2>
          <div class="autorites-list">
            <div v-for="(a, i) in autorites.slice(0, 8)" :key="a.nom"
                 class="autorite-item"
                 @click="voirProfilAutorite(a.nom)">
              <span class="autorite-rank">{{ i + 1 }}</span>
              <div class="autorite-info">
                <p class="autorite-nom">{{ a.nom }}</p>
                <p class="autorite-meta">{{ a.nb_ao }} AOs · {{ formatMontant(a.montant_moyen) || 'Montant N/A' }} moy.</p>
              </div>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </div>
          </div>
        </div>

        <!-- Répartition procédures -->
        <div class="card chart-card">
          <h2 class="chart-title">Types de procédures</h2>
          <div class="procedures-list">
            <div v-for="p in procedures" :key="p.type" class="procedure-row">
              <div class="procedure-info">
                <span class="procedure-type">{{ p.type.toUpperCase() }}</span>
                <span class="procedure-pct">{{ p.pct }}%</span>
              </div>
              <div class="procedure-bar-wrap">
                <div class="procedure-bar" :style="{ width: p.pct + '%' }"></div>
              </div>
              <span class="procedure-nb">{{ p.nb_ao }}</span>
            </div>
          </div>
        </div>

      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useFormatMontant } from '@/composables/useFormatMontant'
import { useToastStore } from '@/stores/toast'
import AppSpinner from '@/components/ui/AppSpinner.vue'
import api from '@/api'

const { formatMontant } = useFormatMontant()
const toast = useToastStore()

const loading       = ref(true)
const generatingPDF = ref(false)
const periode       = ref('12m')
const secteurActif  = ref(null)
const tooltip       = ref(null)
const resume        = ref(null)
const secteurs      = ref([])
const evolution     = ref([])
const autorites     = ref([])
const procedures    = ref([])

const chartW = 600
const chartH = 200
const barWidth = computed(() => evolution.value.length ? (chartW - 40) / evolution.value.length - 4 : 20)
const maxNbAo = computed(() => Math.max(...evolution.value.map(e => e.nb_ao), 1))

function barX(i) { return 20 + i * ((chartW - 40) / (evolution.value.length || 1)) }
function barY(nb) { return 20 + (1 - nb / maxNbAo.value) * (chartH - 60) }

const maxSecteur = computed(() => Math.max(...secteurs.value.map(s => s.nb_ao), 1))

const secteursFiltres = [
  { val: null,           label: 'Tous' },
  { val: 'btp',          label: 'BTP' },
  { val: 'informatique', label: 'IT' },
  { val: 'sante',        label: 'Santé' },
  { val: 'agriculture',  label: 'Agriculture' },
  { val: 'conseil',      label: 'Conseil' },
]

async function fetchAll() {
  loading.value = true
  try {
    const [r, s, e, a, p] = await Promise.all([
      api.get('/intelligence/resume'),
      api.get('/intelligence/tendances/secteurs', { params: { periode: periode.value } }),
      api.get('/intelligence/tendances/evolution', { params: { periode: periode.value } }),
      api.get('/intelligence/autorites', { params: { periode: periode.value, limite: 8 } }),
      api.get('/intelligence/tendances/types-procedures', { params: { periode: periode.value } }),
    ])
    resume.value     = r.data
    secteurs.value   = s.data.secteurs
    evolution.value  = e.data.evolution
    autorites.value  = a.data.autorites
    procedures.value = p.data.procedures
  } catch (e) {
    toast.add('Erreur chargement Intelligence', 'error')
  } finally {
    loading.value = false
  }
}

async function fetchEvolution() {
  const { data } = await api.get('/intelligence/tendances/evolution', {
    params: { periode: periode.value, secteur: secteurActif.value }
  })
  evolution.value = data.evolution
}

async function downloadRapport() {
  generatingPDF.value = true
  try {
    const resp = await api.get('/intelligence/rapport/mensuel', { responseType: 'blob' })
    const url  = URL.createObjectURL(resp.data)
    const a    = document.createElement('a')
    a.href = url
    a.download = `rapport_netsync_gov_${new Date().toISOString().slice(0,7)}.pdf`
    a.click()
    URL.revokeObjectURL(url)
    toast.add('Rapport PDF téléchargé', 'success')
  } catch {
    toast.add('Erreur génération rapport', 'error')
  } finally {
    generatingPDF.value = false
  }
}

function voirProfilAutorite(nom) {
  // Navigation vers la page profil autorité
  window.open(`/intelligence/autorites/${encodeURIComponent(nom)}`, '_blank')
}

onMounted(fetchAll)
</script>

<style scoped>
.intelligence-page { display:flex; flex-direction:column; gap:1rem; }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:1rem; }
.page-title { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); }
.page-sub { font-size:13px; color:var(--muted); margin-top:4px; }
.header-actions { display:flex; gap:.75rem; align-items:center; }
.periode-select { font-family:var(--font-body); font-size:13px; border:1px solid var(--border-md); border-radius:var(--radius-md); padding:8px 12px; background:var(--white); color:var(--ink); cursor:pointer; }

.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; }
.kpi-card { padding:1.25rem; }
.kpi-label { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; margin-bottom:.375rem; }
.kpi-val { font-family:var(--font-display); font-size:1.75rem; color:var(--ink); line-height:1; }
.kpi-secteur { font-size:1.1rem; color:var(--blue-500); }
.kpi-trend { font-size:11px; color:var(--muted); margin-top:4px; }
.kpi-trend.up { color:var(--green-400); }
.kpi-trend.down { color:var(--red-400); }

.charts-grid { display:grid; grid-template-columns:1fr 1fr; gap:1rem; }
.chart-card { padding:1.25rem; }
.chart-title { font-size:14px; font-weight:600; color:var(--ink); margin-bottom:.875rem; }
.chart-filters { display:flex; gap:.375rem; flex-wrap:wrap; margin-bottom:.75rem; }
.filter-pill { font-size:11px; padding:3px 10px; border-radius:var(--radius-full); border:1px solid var(--border-md); background:var(--white); color:var(--muted); cursor:pointer; }
.filter-pill.active { background:var(--blue-500); color:var(--white); border-color:var(--blue-500); }
.chart-wrap { position:relative; }
.chart-tooltip { position:absolute; top:10px; right:10px; background:var(--ink); color:var(--white); font-size:11px; padding:6px 10px; border-radius:var(--radius-md); pointer-events:none; }

.secteurs-bars { display:flex; flex-direction:column; gap:.625rem; }
.secteur-row { display:flex; align-items:center; gap:.5rem; }
.secteur-name { font-size:12px; color:var(--ink-500); width:90px; flex-shrink:0; }
.secteur-bar-wrap { flex:1; height:8px; background:var(--surface-2); border-radius:4px; overflow:hidden; }
.secteur-bar { height:100%; background:var(--blue-500); border-radius:4px; transition:width .5s ease; }
.secteur-count { font-size:11px; font-weight:600; color:var(--blue-600); width:30px; text-align:right; }

.autorites-list { display:flex; flex-direction:column; }
.autorite-item { display:flex; align-items:center; gap:.75rem; padding:.625rem 0; border-bottom:1px solid var(--border); cursor:pointer; }
.autorite-item:last-child { border-bottom:none; }
.autorite-item:hover { background:var(--surface); border-radius:var(--radius-md); padding-left:.5rem; }
.autorite-rank { width:20px; height:20px; border-radius:50%; background:var(--blue-50); color:var(--blue-600); font-size:11px; font-weight:600; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.autorite-info { flex:1; }
.autorite-nom { font-size:12px; font-weight:500; color:var(--ink); }
.autorite-meta { font-size:11px; color:var(--muted); }

.procedures-list { display:flex; flex-direction:column; gap:.625rem; }
.procedure-row { display:grid; grid-template-columns:1fr auto; gap:.5rem; align-items:center; }
.procedure-info { display:flex; align-items:center; justify-content:space-between; grid-column:1; }
.procedure-type { font-size:11px; font-weight:600; color:var(--ink); }
.procedure-pct { font-size:11px; color:var(--blue-600); font-family:var(--font-mono); }
.procedure-bar-wrap { grid-column:1; height:6px; background:var(--surface-2); border-radius:3px; }
.procedure-bar { height:100%; background:var(--blue-400); border-radius:3px; }
.procedure-nb { font-size:11px; color:var(--muted); grid-row:1; }

@media(max-width:900px) {
  .kpi-grid { grid-template-columns:1fr 1fr; }
  .charts-grid { grid-template-columns:1fr; }
}
</style>
