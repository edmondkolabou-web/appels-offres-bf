<template>
  <div class="ao-list-page">
    <!-- Barre de recherche top -->
    <div class="search-bar card">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input class="search-input" type="search" placeholder="Rechercher un appel d'offres…" v-model="aoStore.filters.q" @keyup.enter="search" />
      <button class="btn btn-primary" @click="search" aria-label="Rechercher">Rechercher</button>
    </div>

    <div class="ao-list-layout">
      <!-- Sidebar filtres -->
      <AOFilters @search="search" />

      <!-- Liste principale -->
      <div class="ao-main">
        <!-- Stats strip -->
        <div class="list-header">
          <p class="list-count">
            <strong>{{ aoStore.total }}</strong> AO trouvés
            <span v-if="aoStore.filters.q"> pour « {{ aoStore.filters.q }} »</span>
          </p>
          <div class="list-sort">
            <span class="sort-label">Trier par :</span>
            <select class="form-input" style="width:auto;font-size:12px;padding:5px 8px;" v-model="sortMode" @change="search">
              <option value="date">Date de publication</option>
              <option value="cloture">Date de clôture</option>
            </select>
          </div>
        </div>

        <!-- Loading -->
        <AppSpinner v-if="aoStore.loading" size="lg" label="Chargement des AOs…" />

        <!-- Mur freemium -->
        <div v-else-if="hitLimit" class="freemium-wall card">
          <div class="freemium-content">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--blue-500)" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            <h3>Limite journalière atteinte</h3>
            <p>Le plan Gratuit permet 3 consultations par jour. Passez au plan Pro pour un accès illimité.</p>
            <RouterLink to="/pricing" class="btn btn-primary">Voir les tarifs →</RouterLink>
          </div>
        </div>

        <!-- Grille AO -->
        <div v-else-if="aoStore.list.length" class="ao-grid">
          <AOCard v-for="ao in aoStore.list" :key="ao.id" :ao="ao" />
        </div>

        <!-- État vide -->
        <div v-else class="empty-state card">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" stroke-width="1"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/></svg>
          <h3>Aucun AO trouvé</h3>
          <p>Essaie de modifier tes filtres ou ta recherche.</p>
          <button class="btn btn-ghost" @click="aoStore.resetFilters(); search()">Réinitialiser les filtres</button>
        </div>

        <!-- Pagination -->
        <AppPagination v-model="aoStore.filters.page" :pages="aoStore.pages" @update:modelValue="search" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAOStore } from '@/stores/aos'
import { useFavorisStore } from '@/stores/favoris'
import AOCard from '@/components/ao/AOCard.vue'
import AOFilters from '@/components/ao/AOFilters.vue'
import AppSpinner from '@/components/ui/AppSpinner.vue'
import AppPagination from '@/components/ui/AppPagination.vue'

const aoStore      = useAOStore()
const favorisStore = useFavorisStore()
const hitLimit     = ref(false)
const sortMode     = ref('date')

async function search() {
  hitLimit.value = false
  try {
    await aoStore.fetchList()
  } catch (err) {
    if (err.response?.status === 402) hitLimit.value = true
  }
}

onMounted(async () => {
  await aoStore.fetchSecteurs()
  await favorisStore.fetch()
  await search()
})
</script>

<style scoped>
.ao-list-page { display:flex; flex-direction:column; gap:1rem; }
.search-bar { display:flex; align-items:center; gap:.75rem; padding:.75rem 1.25rem; }
.search-input { flex:1; border:none; outline:none; font-family:var(--font-body); font-size:14px; color:var(--ink); background:transparent; }
.search-input::placeholder { color:var(--muted); }
.ao-list-layout { display:grid; grid-template-columns:260px 1fr; gap:1rem; align-items:start; }
.list-header { display:flex; align-items:center; justify-content:space-between; padding:.75rem 0 .625rem; }
.list-count { font-size:13px; color:var(--muted); }
.sort-label { font-size:12px; color:var(--muted); margin-right:.5rem; }
.ao-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:1rem; }
.empty-state { padding:3rem 2rem; text-align:center; display:flex; flex-direction:column; align-items:center; gap:.75rem; }
.empty-state h3 { font-size:15px; color:var(--ink); }
.empty-state p { font-size:13px; color:var(--muted); }
.freemium-wall { padding:3rem 2rem; }
.freemium-content { display:flex; flex-direction:column; align-items:center; text-align:center; gap:.75rem; }
.freemium-content h3 { font-size:15px; color:var(--ink); }
.freemium-content p { font-size:13px; color:var(--muted); max-width:380px; }
@media(max-width:900px) { .ao-list-layout { grid-template-columns:1fr; } }
</style>
