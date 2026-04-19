<template>
  <div class="profil-page">
    <h1 class="page-title">Mon profil</h1>
    <div class="profil-grid">
      <div class="card profil-card">
        <div class="profil-avatar">{{ authStore.initiales }}</div>
        <h2 class="profil-name">{{ authStore.abonne?.prenom }} {{ authStore.abonne?.nom }}</h2>
        <p class="profil-email">{{ authStore.abonne?.email }}</p>
        <span class="plan-badge">{{ authStore.plan.toUpperCase() }}</span>
      </div>
      <div class="card" style="padding:1.5rem;">
        <h2 style="font-size:14px;font-weight:600;margin-bottom:1.25rem;">Informations personnelles</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem;">
          <div class="form-group">
            <label class="form-label">Prénom</label>
            <input class="form-input" type="text" v-model="form.prenom" />
          </div>
          <div class="form-group">
            <label class="form-label">Nom</label>
            <input class="form-input" type="text" v-model="form.nom" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Entreprise</label>
          <input class="form-input" type="text" v-model="form.entreprise" placeholder="Optionnel" />
        </div>
        <div class="form-group">
          <label class="form-label">WhatsApp</label>
          <input class="form-input" type="tel" v-model="form.whatsapp" placeholder="+226 70 00 00 00" />
          <p class="form-hint">Pour recevoir tes alertes AO sur WhatsApp</p>
        </div>
        <button class="btn btn-primary" @click="save" :disabled="saving">
          <div v-if="saving" class="spinner"></div>
          {{ saving ? 'Enregistrement…' : 'Enregistrer les modifications' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const saving    = ref(false)
const form      = reactive({ prenom: '', nom: '', entreprise: '', whatsapp: '' })

onMounted(() => {
  if (authStore.abonne) Object.assign(form, { prenom: authStore.abonne.prenom, nom: authStore.abonne.nom, entreprise: authStore.abonne.entreprise || '', whatsapp: authStore.abonne.whatsapp || '' })
})

async function save() {
  saving.value = true
  await authStore.updateProfil(form)
  saving.value = false
}
</script>

<style scoped>
.profil-page { display:flex; flex-direction:column; gap:1rem; }
.page-title { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); margin-bottom:.5rem; }
.profil-grid { display:grid; grid-template-columns:280px 1fr; gap:1rem; align-items:start; }
.profil-card { padding:2rem; text-align:center; }
.profil-avatar { width:72px; height:72px; border-radius:50%; background:var(--blue-500); color:var(--white); font-size:1.5rem; font-weight:600; display:flex; align-items:center; justify-content:center; margin:0 auto 1rem; }
.profil-name { font-family:var(--font-display); font-size:1.2rem; color:var(--ink); margin-bottom:4px; }
.profil-email { font-size:12px; color:var(--muted); margin-bottom:.875rem; }
.plan-badge { font-size:10px; font-weight:600; background:var(--blue-500); color:var(--white); padding:3px 12px; border-radius:var(--radius-full); }
@media(max-width:768px) { .profil-grid { grid-template-columns:1fr; } }
</style>
