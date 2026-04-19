<template>
  <div v-if="aoStore.loading" class="detail-loading">
    <AppSpinner size="lg" label="Chargement de l'AO…" />
  </div>
  <div v-else-if="ao" class="ao-detail">
    <!-- Breadcrumb -->
    <nav class="breadcrumb" aria-label="Fil d'Ariane">
      <RouterLink to="/aos">Appels d'offres</RouterLink>
      <span class="sep">›</span>
      <span>{{ ao.reference }}</span>
    </nav>

    <div class="detail-layout">
      <!-- Contenu principal -->
      <main class="detail-main">
        <!-- Hero -->
        <div class="ao-hero card">
          <div class="hero-tags">
            <span class="tag" :class="`tag-${ao.statut}`">{{ ao.statut }}</span>
            <span class="tag" :class="`tag-${ao.secteur}`">{{ ao.secteur }}</span>
            <span v-if="ao.est_urgent" class="tag tag-urgent">⚡ J-{{ ao.jours_restants }}</span>
          </div>
          <h1 class="hero-title">{{ ao.titre }}</h1>
          <p class="hero-ref">Réf. {{ ao.reference }}</p>
          <div class="hero-actions">
            <button class="btn btn-primary" @click="handleSave" :aria-label="isSaved ? 'Retirer des favoris' : 'Enregistrer'">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
              {{ isSaved ? 'Enregistré' : 'Enregistrer' }}
            </button>
            <button class="btn btn-ghost" @click="share" aria-label="Partager cet AO">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
              Partager
            </button>
            <a v-if="ao.pdf_url" :href="ao.pdf_url" target="_blank" class="btn btn-ghost" aria-label="Télécharger le PDF">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              PDF
            </a>
          </div>
        </div>

        <!-- Grille métadonnées -->
        <div class="meta-grid card">
          <div class="meta-item">
            <div class="meta-label">Autorité contractante</div>
            <div class="meta-val">{{ ao.autorite_contractante }}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Type de procédure</div>
            <div class="meta-val">{{ ao.type_procedure?.toUpperCase() }}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Date de publication</div>
            <div class="meta-val">{{ formatDate(ao.date_publication) }}</div>
          </div>
          <div class="meta-item" :class="{ urgent: ao.est_urgent }">
            <div class="meta-label">Date de clôture</div>
            <div class="meta-val">{{ ao.date_cloture ? formatDate(ao.date_cloture) : 'Non précisée' }}</div>
          </div>
          <div v-if="ao.montant_estime" class="meta-item">
            <div class="meta-label">Montant estimé</div>
            <div class="meta-val">{{ formatMontant(ao.montant_estime) }}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Source</div>
            <div class="meta-val">{{ ao.source?.toUpperCase() }}</div>
          </div>
          <div v-if="ao.numero_quotidien" class="meta-item">
            <div class="meta-label">N° Quotidien</div>
            <div class="meta-val mono">{{ ao.numero_quotidien }}</div>
          </div>
        </div>

        <!-- Description -->
        <div v-if="ao.description" class="card desc-card">
          <h2 class="section-h2">Description</h2>
          <p class="desc-text">{{ ao.description }}</p>
        </div>
      </main>

      <!-- Sidebar -->
      <aside class="detail-sidebar">
        <!-- Countdown -->
        <div v-if="ao.date_cloture" class="deadline-card card" :class="{ urgent: ao.est_urgent }">
          <div class="deadline-label">Date limite de soumission</div>
          <div class="deadline-date">{{ formatDate(ao.date_cloture) }}</div>
          <div class="deadline-remaining" v-if="ao.jours_restants !== null">
            {{ ao.jours_restants > 0 ? `${ao.jours_restants} jours restants` : 'Clôturé' }}
          </div>
        </div>

        <!-- Partage -->
        <div class="card" style="padding:1rem;">
          <h3 class="sidebar-h3">Partager cet AO</h3>
          <div class="share-btns">
            <button class="btn btn-ghost" style="width:100%;justify-content:center;font-size:12px;" @click="share">
              Copier le lien
            </button>
            <button class="btn btn-ghost" style="width:100%;justify-content:center;font-size:12px;background:#25D366;color:white;border-color:#25D366;" @click="shareWhatsApp">
              Partager via WhatsApp
            </button>
          </div>
        </div>
      </aside>
    </div>
  </div>
  <div v-else class="not-found card" style="padding:3rem;text-align:center;">
    <h2>AO introuvable</h2>
    <RouterLink to="/aos" class="btn btn-ghost" style="margin-top:1rem;">← Retour à la liste</RouterLink>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAOStore } from '@/stores/aos'
import { useFavorisStore } from '@/stores/favoris'
import { useToastStore } from '@/stores/toast'
import { useDate } from '@/composables/useDate'
import { useFormatMontant } from '@/composables/useFormatMontant'
import AppSpinner from '@/components/ui/AppSpinner.vue'

const props = defineProps({ id: { type: String, required: true } })

const aoStore      = useAOStore()
const favorisStore = useFavorisStore()
const toastStore   = useToastStore()
const { formatDate } = useDate()
const { formatMontant } = useFormatMontant()

const ao      = computed(() => aoStore.current)
const isSaved = computed(() => ao.value && favorisStore.aoIds.has(ao.value.id))

async function handleSave() {
  if (ao.value) await favorisStore.toggle(ao.value.id)
}

function share() {
  navigator.clipboard?.writeText(window.location.href)
  toastStore.add('Lien copié dans le presse-papier', 'success')
}

function shareWhatsApp() {
  const url = encodeURIComponent(window.location.href)
  const text = encodeURIComponent(`AO : ${ao.value?.titre?.slice(0,100)}`)
  window.open(`https://wa.me/?text=${text}%20${url}`, '_blank')
}

onMounted(async () => {
  await aoStore.fetchDetail(props.id)
  await favorisStore.fetch()
})
</script>

<style scoped>
.detail-loading { display:flex; justify-content:center; padding:4rem; }
.breadcrumb { display:flex; align-items:center; gap:.5rem; font-size:12px; color:var(--muted); margin-bottom:1rem; }
.breadcrumb a { color:var(--blue-500); text-decoration:none; }
.sep { color:var(--border-md); }
.detail-layout { display:grid; grid-template-columns:1fr 280px; gap:1rem; align-items:start; }
.detail-main { display:flex; flex-direction:column; gap:1rem; }
.ao-hero { padding:1.5rem; }
.hero-tags { display:flex; gap:5px; flex-wrap:wrap; margin-bottom:.875rem; }
.hero-title { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); line-height:1.3; margin-bottom:.375rem; }
.hero-ref { font-family:var(--font-mono); font-size:11px; color:var(--muted); margin-bottom:1rem; }
.hero-actions { display:flex; gap:.625rem; flex-wrap:wrap; }
.meta-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:0; padding:0; overflow:hidden; }
.meta-item { padding:.875rem 1.25rem; border-bottom:1px solid var(--border); border-right:1px solid var(--border); }
.meta-item:nth-child(even) { border-right:none; }
.meta-label { font-size:11px; color:var(--muted); margin-bottom:3px; }
.meta-val { font-size:13px; font-weight:500; color:var(--ink); }
.meta-val.mono { font-family:var(--font-mono); }
.meta-item.urgent .meta-val { color:var(--red-600); }
.desc-card { padding:1.25rem; }
.section-h2 { font-size:14px; font-weight:600; color:var(--ink); margin-bottom:.75rem; }
.desc-text { font-size:13px; color:var(--ink-500); line-height:1.7; white-space:pre-wrap; }
.detail-sidebar { display:flex; flex-direction:column; gap:1rem; }
.deadline-card { padding:1.25rem; text-align:center; }
.deadline-card.urgent { border-color:var(--red-400); background:var(--red-50); }
.deadline-label { font-size:11px; color:var(--muted); margin-bottom:.375rem; }
.deadline-date { font-size:1.1rem; font-weight:600; color:var(--ink); margin-bottom:.25rem; }
.deadline-remaining { font-size:13px; font-weight:500; color:var(--blue-500); }
.deadline-card.urgent .deadline-remaining { color:var(--red-600); }
.sidebar-h3 { font-size:13px; font-weight:600; color:var(--ink); margin-bottom:.75rem; }
.share-btns { display:flex; flex-direction:column; gap:.5rem; }
@media(max-width:900px) { .detail-layout { grid-template-columns:1fr; } }
</style>
