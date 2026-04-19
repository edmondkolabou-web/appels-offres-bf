<template>
  <div class="alertes-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Mes alertes</h1>
        <p class="page-sub">Configure les secteurs et canaux pour recevoir les AOs correspondants.</p>
      </div>
      <button class="btn btn-primary" @click="showForm = true" :disabled="hitLimit" aria-label="Créer une nouvelle alerte">
        + Nouvelle alerte
      </button>
    </div>

    <div v-if="hitLimit" class="limit-banner card">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      Limite atteinte ({{ authStore.isPro ? 10 : 1 }} alerte{{ authStore.isPro ? 's' : '' }} maximum).
      <RouterLink v-if="!authStore.isPro" to="/pricing">Passer Pro →</RouterLink>
    </div>

    <AppSpinner v-if="alertesStore.loading" />

    <div v-else-if="alertesStore.items.length" class="alertes-list">
      <div v-for="alerte in alertesStore.items" :key="alerte.id" class="alerte-card card">
        <div class="alerte-head">
          <div class="alerte-title">
            <span v-if="alerte.secteurs.length">{{ alerte.secteurs.join(', ') }}</span>
            <span v-else style="color:var(--muted)">Tous les secteurs</span>
          </div>
          <div class="toggle" :class="{ on: alerte.actif }" @click="alertesStore.toggle(alerte.id)" :aria-label="alerte.actif ? 'Désactiver' : 'Activer'">
            <div class="toggle-thumb"></div>
          </div>
        </div>
        <div class="alerte-meta">
          <span>Canal : <strong>{{ alerte.canal }}</strong></span>
          <span v-if="alerte.rappel_j3">· Rappel J-3 activé</span>
          <span v-if="alerte.mots_cles?.length">· Mots-clés : {{ alerte.mots_cles.join(', ') }}</span>
        </div>
        <div class="alerte-actions">
          <button class="btn btn-ghost" style="font-size:11px;padding:4px 10px;" @click="editAlerte = alerte; showForm = true" aria-label="Modifier l'alerte">Modifier</button>
          <button class="btn btn-danger" style="font-size:11px;padding:4px 10px;" @click="alertesStore.remove(alerte.id)" aria-label="Supprimer l'alerte">Supprimer</button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state card">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" stroke-width="1"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/></svg>
      <h3>Aucune alerte configurée</h3>
      <p>Crée ta première alerte pour recevoir les AOs par email ou WhatsApp.</p>
      <button class="btn btn-primary" @click="showForm = true">Créer une alerte</button>
    </div>

    <!-- Modal formulaire alerte -->
    <Teleport to="body">
      <div v-if="showForm" class="modal-overlay" @click.self="closeForm">
        <div class="modal card">
          <h2 class="modal-title">{{ editAlerte ? 'Modifier l\'alerte' : 'Nouvelle alerte' }}</h2>
          <div class="form-group">
            <label class="form-label">Secteurs surveillés</label>
            <div class="secteurs-grid">
              <label v-for="s in SECTEURS" :key="s" class="secteur-check">
                <input type="checkbox" :value="s" v-model="form.secteurs" />
                <span>{{ s }}</span>
              </label>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Canal de réception</label>
            <select class="form-input" v-model="form.canal">
              <option value="les_deux">Email + WhatsApp</option>
              <option value="email">Email uniquement</option>
              <option value="whatsapp">WhatsApp uniquement</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Mots-clés personnalisés <span style="color:var(--muted);font-weight:400;">(séparés par des virgules)</span></label>
            <input class="form-input" type="text" v-model="motsClesInput" placeholder="audit, systeme d'information, réseau…" />
          </div>
          <label style="display:flex;align-items:center;gap:.5rem;font-size:13px;margin-bottom:1rem;">
            <input type="checkbox" v-model="form.rappel_j3" style="accent-color:var(--blue-500);" />
            Envoyer un rappel 3 jours avant la clôture
          </label>
          <div class="modal-actions">
            <button class="btn btn-ghost" @click="closeForm">Annuler</button>
            <button class="btn btn-primary" @click="saveAlerte" :disabled="saving">
              <div v-if="saving" class="spinner"></div>
              {{ editAlerte ? 'Mettre à jour' : 'Créer l\'alerte' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useAlertesStore } from '@/stores/alertes'
import { useAuthStore } from '@/stores/auth'
import AppSpinner from '@/components/ui/AppSpinner.vue'

const alertesStore = useAlertesStore()
const authStore    = useAuthStore()

const SECTEURS = ['informatique','btp','sante','agriculture','conseil','equipement','transport','energie','education']

const showForm     = ref(false)
const editAlerte   = ref(null)
const saving       = ref(false)
const motsClesInput = ref('')
const form = reactive({ secteurs: [], canal: 'les_deux', rappel_j3: true })

const hitLimit = computed(() => {
  const max = authStore.isPro ? 10 : 1
  return alertesStore.items.length >= max
})

function closeForm() { showForm.value = false; editAlerte.value = null }

watch(editAlerte, (al) => {
  if (al) {
    Object.assign(form, { secteurs: [...al.secteurs], canal: al.canal, rappel_j3: al.rappel_j3 })
    motsClesInput.value = (al.mots_cles || []).join(', ')
  } else {
    Object.assign(form, { secteurs: [], canal: 'les_deux', rappel_j3: true })
    motsClesInput.value = ''
  }
})

async function saveAlerte() {
  saving.value = true
  const payload = { ...form, mots_cles: motsClesInput.value.split(',').map(s=>s.trim()).filter(Boolean), sources: [] }
  try {
    if (editAlerte.value) await alertesStore.update(editAlerte.value.id, payload)
    else await alertesStore.create(payload)
    closeForm()
  } finally {
    saving.value = false
  }
}

onMounted(() => alertesStore.fetch())
</script>

<style scoped>
.alertes-page { display:flex; flex-direction:column; gap:1rem; }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; }
.page-title { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); }
.page-sub { font-size:13px; color:var(--muted); margin-top:4px; }
.limit-banner { display:flex; align-items:center; gap:.75rem; padding:.875rem 1.25rem; font-size:13px; color:var(--amber-600); background:var(--amber-50); border-color:#F0D5A0; }
.limit-banner a { color:var(--blue-500); margin-left:auto; text-decoration:none; font-weight:500; }
.alertes-list { display:flex; flex-direction:column; gap:.75rem; }
.alerte-card { padding:1.25rem; }
.alerte-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:.5rem; }
.alerte-title { font-size:14px; font-weight:600; color:var(--ink); }
.alerte-meta { font-size:12px; color:var(--muted); margin-bottom:.875rem; }
.alerte-actions { display:flex; gap:.5rem; }
.empty-state { padding:3rem 2rem; text-align:center; display:flex; flex-direction:column; align-items:center; gap:.75rem; }
.empty-state h3 { font-size:15px; }
.empty-state p { font-size:13px; color:var(--muted); }
.modal-overlay { position:fixed; inset:0; background:rgba(15,25,35,.5); display:flex; align-items:center; justify-content:center; z-index:500; padding:1rem; }
.modal { width:100%; max-width:480px; padding:1.75rem; }
.modal-title { font-family:var(--font-display); font-size:1.25rem; color:var(--ink); margin-bottom:1.25rem; }
.secteurs-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:.5rem; }
.secteur-check { display:flex; align-items:center; gap:6px; font-size:12px; cursor:pointer; }
.secteur-check input { accent-color:var(--blue-500); }
.modal-actions { display:flex; gap:.75rem; justify-content:flex-end; margin-top:1.25rem; }
</style>
