<template>
  <div class="ao-card card" @click="$router.push(`/aos/${ao.id}`)">
    <div class="ao-card-top">
      <div class="ao-tags">
        <span class="tag" :class="`tag-${ao.statut}`">{{ ao.statut }}</span>
        <span class="tag" :class="`tag-${ao.secteur}`">{{ ao.secteur }}</span>
        <span v-if="ao.est_urgent" class="tag tag-urgent">J-{{ ao.jours_restants }}</span>
      </div>
      <button class="save-btn" :class="{ saved: isSaved }" @click.stop="handleToggleSave" :aria-label="isSaved ? 'Retirer des favoris' : 'Enregistrer'">
        <svg width="14" height="14" viewBox="0 0 24 24" :fill="isSaved ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
      </button>
    </div>
    <h3 class="ao-title">{{ ao.titre }}</h3>
    <p class="ao-meta">
      <span>{{ ao.autorite_contractante }}</span>
      <span class="ao-ref">{{ ao.reference }}</span>
    </p>
    <div class="ao-footer">
      <span class="ao-date" :class="{ urgent: ao.est_urgent }">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        {{ ao.date_cloture ? formatDate(ao.date_cloture) : 'Date non précisée' }}
      </span>
      <span v-if="ao.montant_estime" class="ao-montant">{{ formatMontant(ao.montant_estime) }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useFavorisStore } from '@/stores/favoris'
import { useDate } from '@/composables/useDate'
import { useFormatMontant } from '@/composables/useFormatMontant'

const props = defineProps({ ao: { type: Object, required: true } })
const favorisStore = useFavorisStore()
const { formatDate } = useDate()
const { formatMontant } = useFormatMontant()

const isSaved = computed(() => favorisStore.aoIds.has(props.ao.id))

async function handleToggleSave() {
  await favorisStore.toggle(props.ao.id)
}
</script>

<style scoped>
.ao-card { padding:1rem 1.25rem; cursor:pointer; display:flex; flex-direction:column; gap:.5rem; }
.ao-card-top { display:flex; align-items:flex-start; justify-content:space-between; gap:.5rem; }
.ao-tags { display:flex; gap:5px; flex-wrap:wrap; }
.save-btn { width:28px; height:28px; border-radius:var(--radius-sm); border:1px solid var(--border); background:var(--white); cursor:pointer; display:flex; align-items:center; justify-content:center; color:var(--muted); flex-shrink:0; transition:all var(--transition-fast); }
.save-btn:hover, .save-btn.saved { border-color:var(--amber-400); color:var(--amber-400); background:var(--amber-50); }
.ao-title { font-size:13px; font-weight:500; color:var(--ink); line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.ao-meta { display:flex; align-items:center; justify-content:space-between; gap:.5rem; }
.ao-meta span { font-size:11px; color:var(--muted); }
.ao-ref { font-family:var(--font-mono); font-size:10px; }
.ao-footer { display:flex; align-items:center; justify-content:space-between; }
.ao-date { display:flex; align-items:center; gap:4px; font-size:11px; font-weight:500; color:var(--muted); }
.ao-date.urgent { color:var(--red-600); }
.ao-montant { font-size:11px; font-weight:500; color:var(--blue-600); font-family:var(--font-mono); }
</style>
