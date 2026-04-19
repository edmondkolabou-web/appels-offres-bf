<template>
  <div class="toast-container" aria-live="polite" aria-atomic="true">
    <TransitionGroup name="toast">
      <div
        v-for="t in toastStore.toasts"
        :key="t.id"
        class="toast"
        :class="t.type"
        role="alert"
      >
        <svg v-if="t.type==='success'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
        <svg v-else-if="t.type==='error'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        {{ t.message }}
        <button @click="toastStore.remove(t.id)" style="margin-left:auto;background:none;border:none;cursor:pointer;color:inherit;opacity:.7;" aria-label="Fermer">×</button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToastStore } from '@/stores/toast'
const toastStore = useToastStore()
</script>

<style scoped>
.toast-enter-from { opacity:0; transform:translateY(8px); }
.toast-leave-to   { opacity:0; transform:translateX(100%); }
.toast-enter-active,.toast-leave-active { transition:all .3s ease; }
</style>
