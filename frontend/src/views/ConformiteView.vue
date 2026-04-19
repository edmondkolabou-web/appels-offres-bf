<!-- NetSync Gov Conformité — Dashboard des pièces administratives -->
<template>
  <div class="conformite-page">

    <!-- Header + Score -->
    <div class="conformite-header">
      <div>
        <h1 class="page-title">Conformité administrative</h1>
        <p class="page-sub">Coffre-fort de tes pièces · Alertes renouvellement automatiques</p>
      </div>
      <div class="score-circle" :class="`score-${scoreNiveau}`" aria-label="Score de conformité">
        <svg viewBox="0 0 36 36" class="score-svg">
          <path class="score-bg" d="M18 2.0845a15.9155 15.9155 0 0 1 0 31.831"/>
          <path class="score-fill" :stroke-dasharray="`${score}, 100`" d="M18 2.0845a15.9155 15.9155 0 0 1 0 31.831"/>
        </svg>
        <div class="score-text">
          <span class="score-val">{{ score }}%</span>
          <span class="score-label">conformité</span>
        </div>
      </div>
    </div>

    <!-- Message conformité -->
    <div class="conformite-banner" :class="`banner-${scoreNiveau}`" v-if="scoreMessage" role="alert">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      {{ scoreMessage }}
    </div>

    <AppSpinner v-if="loading" size="lg" label="Chargement des pièces..." />

    <template v-else>

      <!-- Pièces critiques / urgentes en premier -->
      <div v-if="piecesUrgentes.length" class="section-urgentes">
        <h2 class="section-title urgent-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--red-400)" stroke-width="2" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
          Action requise ({{ piecesUrgentes.length }})
        </h2>
        <div class="pieces-grid">
          <PieceCard v-for="p in piecesUrgentes" :key="p.type_piece" :piece="p"
                     @refresh="fetchPieces" />
        </div>
      </div>

      <!-- Pièces valides -->
      <div class="section-valides">
        <h2 class="section-title">Pièces valides ({{ piecesValides.length }})</h2>
        <div class="pieces-grid">
          <PieceCard v-for="p in piecesValides" :key="p.type_piece" :piece="p"
                     @refresh="fetchPieces" />
        </div>
      </div>

      <!-- Pièces manquantes -->
      <div v-if="piecesManquantes.length" class="section-manquantes">
        <h2 class="section-title">Non enregistrées ({{ piecesManquantes.length }})</h2>
        <div class="pieces-grid">
          <PieceCard v-for="p in piecesManquantes" :key="p.type_piece" :piece="p"
                     @refresh="fetchPieces" />
        </div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent } from 'vue'
import { useToastStore } from '@/stores/toast'
import AppSpinner from '@/components/ui/AppSpinner.vue'
import api from '@/api'

const toast   = useToastStore()
const loading = ref(true)
const pieces  = ref([])
const score   = ref(0)
const scoreNiveau  = ref('attention')
const scoreMessage = ref('')

const piecesUrgentes  = computed(() =>
  pieces.value.filter(p => ['expiree', 'critique', 'urgent'].includes(p.statut?.statut))
)
const piecesValides   = computed(() =>
  pieces.value.filter(p => ['valide', 'permanent', 'attention'].includes(p.statut?.statut) && p.enregistree)
)
const piecesManquantes = computed(() =>
  pieces.value.filter(p => p.statut?.statut === 'manquante')
)

async function fetchPieces() {
  try {
    const [pRes, sRes] = await Promise.all([
      api.get('/conformite/pieces'),
      api.get('/conformite/score'),
    ])
    pieces.value       = pRes.data
    score.value        = sRes.data.score
    scoreNiveau.value  = sRes.data.niveau
    scoreMessage.value = sRes.data.message
  } catch {
    toast.add('Erreur chargement conformité', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(fetchPieces)
</script>

<!-- Composant PieceCard inline -->
<script>
export const PieceCard = defineComponent({
  name: 'PieceCard',
  props: { piece: { type: Object, required: true } },
  emits: ['refresh'],
  setup(props, { emit }) {
    const toast = useToastStore()
    const uploading = ref(false)
    const showInstructions = ref(false)

    const couleurClass = computed(() => ({
      'piece-rouge':  props.piece.statut?.couleur === 'rouge',
      'piece-orange': props.piece.statut?.couleur === 'orange',
      'piece-jaune':  props.piece.statut?.couleur === 'jaune',
      'piece-vert':   props.piece.statut?.couleur === 'vert',
      'piece-bleu':   props.piece.statut?.couleur === 'bleu',
      'piece-gris':   props.piece.statut?.couleur === 'gris',
    }))

    async function uploadFichier(event) {
      const file = event.target.files[0]
      if (!file) return
      uploading.value = true
      try {
        const fd = new FormData()
        fd.append('type_piece', props.piece.type_piece)
        fd.append('fichier', file)
        await api.post('/pieces', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
        toast.add('Pièce enregistrée', 'success')
        emit('refresh')
      } catch (e) {
        toast.add('Erreur upload', 'error')
      } finally {
        uploading.value = false
      }
    }

    return { toast, uploading, showInstructions, couleurClass, uploadFichier }
  },
  template: `
    <div class="piece-card card" :class="couleurClass">
      <div class="piece-card-header">
        <div class="piece-info">
          <span class="piece-sigle">{{ piece.type_piece.toUpperCase() }}</span>
          <p class="piece-label">{{ piece.label }}</p>
          <p class="piece-organisme">{{ piece.organisme }}</p>
        </div>
        <div class="piece-status-badge" :class="'badge-' + piece.statut?.couleur">
          {{ piece.statut?.statut?.replace('_', ' ') }}
        </div>
      </div>

      <p class="piece-message">{{ piece.statut?.message }}</p>

      <div class="piece-actions">
        <label class="btn btn-ghost piece-upload-btn" :class="{ loading: uploading }">
          <input type="file" accept=".pdf,.jpg,.png,.docx" @change="uploadFichier" style="display:none">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          {{ piece.enregistree ? 'Renouveler' : 'Enregistrer' }}
        </label>

        <a v-if="piece.lien_renouvellement" :href="piece.lien_renouvellement"
           target="_blank" class="btn btn-primary" style="font-size:11px;padding:5px 10px;">
          SECOP →
        </a>

        <button class="btn btn-ghost" style="font-size:11px;padding:5px 10px;"
                @click="showInstructions = !showInstructions">
          Guide
        </button>
      </div>

      <div v-if="showInstructions && piece.instructions" class="piece-instructions">
        <pre>{{ piece.instructions }}</pre>
      </div>
    </div>
  `
})
</script>

<style scoped>
.conformite-page { display:flex; flex-direction:column; gap:1.25rem; }
.conformite-header { display:flex; align-items:flex-start; justify-content:space-between; }
.page-title { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); }
.page-sub { font-size:13px; color:var(--muted); margin-top:4px; }

/* Score circulaire */
.score-circle { position:relative; width:80px; height:80px; }
.score-svg { transform:rotate(-90deg); width:80px; height:80px; }
.score-bg { fill:none; stroke:var(--border); stroke-width:3; stroke-dasharray:100; }
.score-fill { fill:none; stroke-width:3; stroke-linecap:round; transition:stroke-dasharray .5s ease; }
.score-conforme .score-fill    { stroke:var(--green-400); }
.score-quasi_conforme .score-fill { stroke:var(--blue-500); }
.score-attention .score-fill   { stroke:var(--amber-400); }
.score-non_conforme .score-fill{ stroke:var(--red-400); }
.score-text { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; }
.score-val { font-family:var(--font-display); font-size:1.1rem; color:var(--ink); line-height:1; }
.score-label { font-size:9px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }

.conformite-banner { display:flex; align-items:center; gap:.75rem; padding:.875rem 1.25rem; border-radius:var(--radius-lg); font-size:13px; }
.banner-conforme    { background:var(--green-50); color:var(--green-600); }
.banner-quasi_conforme { background:var(--blue-50); color:var(--blue-600); }
.banner-attention   { background:var(--amber-50); color:var(--amber-600); }
.banner-non_conforme{ background:var(--red-50); color:var(--red-600); }

.section-title { font-size:14px; font-weight:600; color:var(--ink); margin-bottom:.75rem; }
.urgent-title { color:var(--red-600); display:flex; align-items:center; gap:.5rem; }
.pieces-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px,1fr)); gap:1rem; }

/* Piece card colors */
:deep(.piece-card) { padding:1.25rem; transition:box-shadow var(--transition-base); }
:deep(.piece-rouge) { border-color:var(--red-400); background:var(--red-50); }
:deep(.piece-orange) { border-color:var(--amber-400); background:var(--amber-50); }
:deep(.piece-vert) { border-color:var(--green-400); }
:deep(.piece-bleu) { border-color:var(--blue-200); }
:deep(.piece-gris) { border-color:var(--border); background:var(--surface-2); }

:deep(.piece-card-header) { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:.625rem; }
:deep(.piece-sigle) { font-family:var(--font-mono); font-size:10px; font-weight:600; color:var(--muted); }
:deep(.piece-label) { font-size:13px; font-weight:500; color:var(--ink); line-height:1.3; margin:.2rem 0; }
:deep(.piece-organisme) { font-size:11px; color:var(--muted); }
:deep(.piece-status-badge) { font-size:10px; font-weight:600; padding:2px 8px; border-radius:var(--radius-full); text-transform:capitalize; flex-shrink:0; }
:deep(.badge-rouge) { background:var(--red-50); color:var(--red-600); }
:deep(.badge-orange) { background:var(--amber-50); color:var(--amber-600); }
:deep(.badge-vert) { background:var(--green-50); color:var(--green-600); }
:deep(.badge-bleu) { background:var(--blue-50); color:var(--blue-600); }
:deep(.badge-gris) { background:var(--surface-2); color:var(--muted); }
:deep(.piece-message) { font-size:12px; color:var(--ink-500); margin-bottom:.75rem; }
:deep(.piece-actions) { display:flex; gap:.5rem; flex-wrap:wrap; }
:deep(.piece-upload-btn) { font-size:11px; padding:5px 10px; cursor:pointer; }
:deep(.piece-instructions) { margin-top:.75rem; padding:.75rem; background:var(--surface); border-radius:var(--radius-md); }
:deep(.piece-instructions pre) { font-size:11px; color:var(--ink-500); white-space:pre-wrap; font-family:var(--font-body); line-height:1.6; }
</style>
