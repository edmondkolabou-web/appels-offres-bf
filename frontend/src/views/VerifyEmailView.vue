<template>
  <div class="verify-page">
    <div class="verify-card card">
      <div v-if="status === 'loading'"><AppSpinner label="Vérification en cours…" /></div>
      <div v-else-if="status === 'success'" class="verify-success">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--green-400)" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
        <h2>Email vérifié ✓</h2>
        <p>Ton compte est maintenant activé.</p>
        <RouterLink to="/dashboard" class="btn btn-primary">Accéder à mon tableau de bord →</RouterLink>
      </div>
      <div v-else class="verify-error">
        <h2>Lien invalide ou expiré</h2>
        <RouterLink to="/auth" class="btn btn-ghost">Retour à la connexion</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { authApi } from '@/api'
import AppSpinner from '@/components/ui/AppSpinner.vue'

const route  = useRoute()
const status = ref('loading')

onMounted(async () => {
  try {
    await authApi.verifyEmail(route.query.token)
    status.value = 'success'
  } catch {
    status.value = 'error'
  }
})
</script>

<style scoped>
.verify-page { display:flex; align-items:center; justify-content:center; min-height:100vh; padding:2rem; }
.verify-card { padding:3rem; max-width:400px; width:100%; text-align:center; }
.verify-success, .verify-error { display:flex; flex-direction:column; align-items:center; gap:1rem; }
.verify-success h2 { font-size:1.5rem; color:var(--ink); }
.verify-success p { font-size:13px; color:var(--muted); }
.verify-error h2 { font-size:1.2rem; color:var(--red-600); }
</style>
