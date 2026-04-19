<template>
  <aside class="filters-panel card">
    <div class="filters-header">
      <h3 class="filters-title">Filtres</h3>
      <button class="btn btn-ghost" style="font-size:11px;padding:4px 10px;" @click="aoStore.resetFilters()">Réinitialiser</button>
    </div>

    <div class="filter-group">
      <label class="form-label">Recherche</label>
      <input class="form-input" type="search" placeholder="Titre, autorité, référence…" :value="aoStore.filters.q" @input="aoStore.setFilter('q', $event.target.value)" />
    </div>

    <div class="filter-group">
      <label class="form-label">Statut</label>
      <select class="form-input" :value="aoStore.filters.statut" @change="aoStore.setFilter('statut', $event.target.value)">
        <option value="">Tous</option>
        <option value="ouvert">Ouvert</option>
        <option value="cloture">Clôturé</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="form-label">Secteur</label>
      <select class="form-input" :value="aoStore.filters.secteur" @change="aoStore.setFilter('secteur', $event.target.value)">
        <option value="">Tous les secteurs</option>
        <option v-for="s in aoStore.secteurs" :key="s.secteur" :value="s.secteur">
          {{ s.secteur }} ({{ s.nb_ao }})
        </option>
      </select>
    </div>

    <div class="filter-group">
      <label class="form-label">Source</label>
      <select class="form-input" :value="aoStore.filters.source" @change="aoStore.setFilter('source', $event.target.value)">
        <option value="">Toutes les sources</option>
        <option value="dgcmef">DGCMEF</option>
        <option value="undp">UNDP</option>
        <option value="cci_bf">CCI-BF</option>
        <option value="bm_step">Banque Mondiale</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="form-label">Procédure</label>
      <select class="form-input" :value="aoStore.filters.type_procedure" @change="aoStore.setFilter('type_procedure', $event.target.value)">
        <option value="">Toutes</option>
        <option value="ouvert">Appel d'offres ouvert</option>
        <option value="restreint">Appel d'offres restreint</option>
        <option value="dpx">Demande de prix</option>
        <option value="ami">Manifestation d'intérêt</option>
        <option value="rfp">Demande de propositions</option>
      </select>
    </div>

    <label class="urgent-check">
      <input type="checkbox" :checked="aoStore.filters.urgent_only" @change="aoStore.setFilter('urgent_only', $event.target.checked)" />
      <span>Clôture dans 3 jours seulement</span>
    </label>

    <button class="btn btn-primary" style="width:100%;margin-top:.5rem;" @click="$emit('search')">
      Appliquer les filtres
    </button>
  </aside>
</template>

<script setup>
import { useAOStore } from '@/stores/aos'
const aoStore = useAOStore()
defineEmits(['search'])
</script>

<style scoped>
.filters-panel { padding:1.25rem; }
.filters-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem; }
.filters-title { font-size:14px; font-weight:600; }
.filter-group { margin-bottom:.875rem; }
.urgent-check { display:flex; align-items:center; gap:.5rem; font-size:12px; color:var(--ink-500); cursor:pointer; }
.urgent-check input { accent-color:var(--blue-500); }
</style>
