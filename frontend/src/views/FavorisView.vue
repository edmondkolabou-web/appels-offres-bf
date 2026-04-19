<template>
  <div class="favoris-page">
    <div class="page-header">
      <h1 class="page-title">Mes favoris</h1>
      <p class="page-sub">{{ favorisStore.items.length }} AO{{ favorisStore.items.length > 1 ? 's' : '' }} enregistrés</p>
    </div>
    <AppSpinner v-if="favorisStore.loading" size="lg" />
    <div v-else-if="favorisStore.items.length" class="favoris-grid">
      <div v-for="fav in favorisStore.items" :key="fav.id" class="fav-card card">
        <div class="fav-top">
          <div class="fav-tags">
            <span class="tag" :class="`tag-${fav.ao.statut}`">{{ fav.ao.statut }}</span>
            <span class="tag" :class="`tag-${fav.ao.secteur}`">{{ fav.ao.secteur }}</span>
            <span v-if="fav.ao.est_urgent" class="tag tag-urgent">J-{{ fav.ao.jours_restants }}</span>
          </div>
          <button class="save-btn saved" @click="favorisStore.toggle(fav.ao.id)" aria-label="Retirer des favoris">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
          </button>
        </div>
        <RouterLink :to="`/aos/${fav.ao.id}`" class="fav-title">{{ fav.ao.titre }}</RouterLink>
        <p class="fav-meta">{{ fav.ao.autorite_contractante }} · {{ formatDate(fav.ao.date_publication) }}</p>
        <div class="fav-date" :class="{ urgent: fav.ao.est_urgent }">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          Clôture : {{ fav.ao.date_cloture ? formatDate(fav.ao.date_cloture) : '—' }}
        </div>
        <div v-if="fav.note" class="fav-note">📝 {{ fav.note }}</div>
      </div>
    </div>
    <div v-else class="empty-state card">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" stroke-width="1"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
      <h3>Aucun favori</h3>
      <p>Enregistre des AOs depuis la liste pour les retrouver ici.</p>
      <RouterLink to="/aos" class="btn btn-primary">Parcourir les AOs →</RouterLink>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useFavorisStore } from '@/stores/favoris'
import { useDate } from '@/composables/useDate'
import AppSpinner from '@/components/ui/AppSpinner.vue'

const favorisStore = useFavorisStore()
const { formatDate } = useDate()

onMounted(() => favorisStore.fetch())
</script>

<style scoped>
.favoris-page { display:flex; flex-direction:column; gap:1rem; }
.page-header { }
.page-title { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); }
.page-sub { font-size:13px; color:var(--muted); margin-top:4px; }
.favoris-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:1rem; }
.fav-card { padding:1.25rem; display:flex; flex-direction:column; gap:.5rem; }
.fav-top { display:flex; align-items:flex-start; justify-content:space-between; gap:.5rem; }
.fav-tags { display:flex; gap:5px; flex-wrap:wrap; }
.save-btn { width:28px; height:28px; border-radius:var(--radius-sm); border:1px solid var(--amber-400); background:var(--amber-50); cursor:pointer; display:flex; align-items:center; justify-content:center; color:var(--amber-400); flex-shrink:0; }
.fav-title { font-size:13px; font-weight:500; color:var(--ink); text-decoration:none; line-height:1.4; }
.fav-title:hover { color:var(--blue-500); }
.fav-meta { font-size:11px; color:var(--muted); }
.fav-date { display:flex; align-items:center; gap:4px; font-size:11px; font-weight:500; color:var(--muted); }
.fav-date.urgent { color:var(--red-600); }
.fav-note { font-size:11px; color:var(--ink-500); background:var(--surface-2); padding:6px 8px; border-radius:var(--radius-sm); }
.empty-state { padding:3rem 2rem; text-align:center; display:flex; flex-direction:column; align-items:center; gap:.75rem; }
.empty-state h3 { font-size:15px; }
.empty-state p { font-size:13px; color:var(--muted); }
</style>
