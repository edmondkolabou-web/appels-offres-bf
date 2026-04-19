<!-- NetSync Gov Candidature — Vue Kanban des candidatures -->
<template>
  <div class="candidatures-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Mes candidatures</h1>
        <p class="page-sub">{{ total }} candidature{{ total > 1 ? 's' : '' }} en cours de suivi</p>
      </div>
    </div>

    <AppSpinner v-if="loading" size="lg" label="Chargement..." />

    <div v-else class="kanban-board">
      <div v-for="col in colonnes" :key="col.statut" class="kanban-col">
        <div class="kanban-col-header">
          <span class="col-label">{{ col.label }}</span>
          <span class="col-count">{{ candidaturesByStatut(col.statut).length }}</span>
        </div>
        <div class="kanban-cards">
          <div
            v-for="cand in candidaturesByStatut(col.statut)"
            :key="cand.id"
            class="kanban-card card"
            @click="$router.push(`/candidatures/${cand.id}`)"
          >
            <!-- Urgence -->
            <div v-if="cand.ao_est_urgent" class="card-urgent-bar" aria-label="Clôture urgente"></div>

            <!-- Tags -->
            <div class="card-tags">
              <span class="tag" :class="`tag-${cand.ao_secteur}`">{{ cand.ao_secteur }}</span>
              <span v-if="cand.ao_est_urgent" class="tag tag-urgent">⚡ Urgent</span>
            </div>

            <!-- Titre AO -->
            <p class="card-title">{{ cand.ao_titre }}</p>

            <!-- Avancement -->
            <div class="avancement-bar">
              <div class="avancement-fill" :style="{ width: cand.avancement + '%' }"
                   :class="getAvanAvancementClass(cand.avancement)"
                   :aria-valuenow="cand.avancement" role="progressbar" aria-label="Avancement du dossier"></div>
            </div>
            <p class="avancement-label">{{ cand.avancement }}% complet</p>

            <!-- Clôture -->
            <div class="card-footer">
              <span class="card-date" :class="{ urgent: cand.ao_est_urgent }">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                {{ cand.ao_date_cloture ? formatDate(cand.ao_date_cloture) : 'Date N/A' }}
              </span>
              <span v-if="cand.montant_offre" class="card-montant">{{ formatMontant(cand.montant_offre) }}</span>
            </div>

            <!-- Actions rapides -->
            <div class="card-actions" @click.stop>
              <select class="statut-select" :value="cand.statut" @change="changerStatut(cand.id, $event.target.value)" aria-label="Changer le statut">
                <option v-for="c in colonnes" :key="c.statut" :value="c.statut">{{ c.label }}</option>
              </select>
            </div>
          </div>

          <!-- Carte vide -->
          <div v-if="!candidaturesByStatut(col.statut).length" class="kanban-empty">
            Aucune candidature
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDate } from '@/composables/useDate'
import { useFormatMontant } from '@/composables/useFormatMontant'
import AppSpinner from '@/components/ui/AppSpinner.vue'
import { useCandidaturesStore } from '@/stores/candidatures'

const candidaturesStore = useCandidaturesStore()
const { formatDate } = useDate()
const { formatMontant } = useFormatMontant()

const loading = ref(true)

const colonnes = [
  { statut: 'en_veille',       label: 'En veille',         color: '#888780' },
  { statut: 'decision',        label: 'Décision go/no-go', color: '#BA7517' },
  { statut: 'en_preparation',  label: 'En préparation',    color: '#0082C9' },
  { statut: 'depose',          label: 'Déposé',            color: '#7F77DD' },
  { statut: 'gagne',           label: 'Gagné',             color: '#1D9E75' },
  { statut: 'perdu',           label: 'Perdu',             color: '#E24B4A' },
]

const total = computed(() => candidaturesStore.list.length)

function candidaturesByStatut(statut) {
  return candidaturesStore.list.filter(c => c.statut === statut)
}

function getAvanAvancementClass(score) {
  if (score >= 80) return 'avancement-ok'
  if (score >= 50) return 'avancement-moyen'
  return 'avancement-faible'
}

async function changerStatut(candidatureId, nouveauStatut) {
  await candidaturesStore.updateStatut(candidatureId, nouveauStatut)
}

onMounted(async () => {
  await candidaturesStore.fetchList()
  loading.value = false
})
</script>

<style scoped>
.candidatures-page { display:flex; flex-direction:column; gap:1rem; }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; }
.page-title { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); }
.page-sub { font-size:13px; color:var(--muted); margin-top:4px; }

.kanban-board { display:flex; gap:1rem; overflow-x:auto; padding-bottom:1rem; }
.kanban-col { min-width:260px; width:260px; flex-shrink:0; }
.kanban-col-header { display:flex; align-items:center; justify-content:space-between; padding:.5rem .75rem; margin-bottom:.5rem; }
.col-label { font-size:12px; font-weight:600; color:var(--ink-500); text-transform:uppercase; letter-spacing:.04em; }
.col-count { font-size:11px; font-weight:600; background:var(--surface-2); color:var(--muted); padding:1px 7px; border-radius:var(--radius-full); }
.kanban-cards { display:flex; flex-direction:column; gap:.625rem; }

.kanban-card { padding:1rem; cursor:pointer; position:relative; overflow:hidden; }
.card-urgent-bar { position:absolute; top:0; left:0; right:0; height:3px; background:var(--red-400); }
.card-tags { display:flex; gap:4px; flex-wrap:wrap; margin-bottom:.5rem; }
.card-title { font-size:12px; font-weight:500; color:var(--ink); line-height:1.4; margin-bottom:.625rem; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }

.avancement-bar { height:4px; background:var(--border); border-radius:2px; overflow:hidden; margin-bottom:3px; }
.avancement-fill { height:100%; border-radius:2px; transition:width .3s ease; }
.avancement-ok     { background:var(--green-400); }
.avancement-moyen  { background:var(--amber-400); }
.avancement-faible { background:var(--red-400); }
.avancement-label { font-size:10px; color:var(--muted); margin-bottom:.5rem; }

.card-footer { display:flex; align-items:center; justify-content:space-between; margin-bottom:.5rem; }
.card-date { display:flex; align-items:center; gap:3px; font-size:11px; color:var(--muted); }
.card-date.urgent { color:var(--red-600); font-weight:500; }
.card-montant { font-size:10px; font-weight:500; color:var(--blue-600); font-family:var(--font-mono); }

.card-actions { border-top:1px solid var(--border); padding-top:.5rem; }
.statut-select { width:100%; font-size:11px; font-family:var(--font-body); border:1px solid var(--border); border-radius:var(--radius-sm); padding:4px 6px; background:var(--surface); color:var(--ink); cursor:pointer; }

.kanban-empty { text-align:center; font-size:11px; color:var(--muted); padding:1.5rem; border:1px dashed var(--border); border-radius:var(--radius-md); }
</style>
