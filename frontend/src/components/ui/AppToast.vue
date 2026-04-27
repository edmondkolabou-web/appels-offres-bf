<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div v-for="t in toastStore.toasts" :key="t.id" :class="['toast', `toast-${t.type}`]" @click="toastStore.remove(t.id)">
          <span class="toast-icon">{{ icons[t.type] || 'ℹ️' }}</span>
          <span class="toast-msg">{{ t.message }}</span>
          <button class="toast-close" @click.stop="toastStore.remove(t.id)">×</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useToastStore } from '@/stores/toast'
const toastStore = useToastStore()
const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' }
</script>

<style scoped>
.toast-container { position:fixed; top:72px; right:16px; z-index:9999; display:flex; flex-direction:column; gap:8px; max-width:380px; }
.toast { display:flex; align-items:center; gap:10px; padding:12px 16px; border-radius:10px; box-shadow:0 8px 24px rgba(0,0,0,.12); cursor:pointer; backdrop-filter:blur(8px); font-size:13px; }
.toast-success { background:#f0fdf4; border:1px solid #bbf7d0; color:#166534; }
.toast-error   { background:#fef2f2; border:1px solid #fecaca; color:#991b1b; }
.toast-warning { background:#fffbeb; border:1px solid #fde68a; color:#92400e; }
.toast-info    { background:#eff6ff; border:1px solid #bfdbfe; color:#1e40af; }
.toast-icon { font-size:16px; flex-shrink:0; }
.toast-msg { flex:1; line-height:1.4; }
.toast-close { background:none; border:none; font-size:18px; color:inherit; opacity:.5; cursor:pointer; padding:0 0 0 8px; }
.toast-close:hover { opacity:1; }

.toast-enter-active { animation:toast-in .3s ease; }
.toast-leave-active { animation:toast-out .25s ease forwards; }
@keyframes toast-in { from { opacity:0; transform:translateX(100px) scale(.95); } to { opacity:1; transform:translateX(0) scale(1); } }
@keyframes toast-out { to { opacity:0; transform:translateX(100px) scale(.95); } }
</style>
