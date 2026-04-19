<template>
  <div class="spinner-wrap" :style="{ padding: size === 'lg' ? '3rem' : '1rem' }">
    <div class="spin" :style="{ width: size === 'lg' ? '32px' : '20px', height: size === 'lg' ? '32px' : '20px' }"></div>
    <p v-if="label" class="spin-label">{{ label }}</p>
  </div>
</template>

<script setup>
defineProps({ size: { default: 'md' }, label: String })
</script>

<style scoped>
.spinner-wrap { display:flex; flex-direction:column; align-items:center; gap:.75rem; }
.spin { border:2px solid var(--border); border-top-color:var(--blue-500); border-radius:50%; animation:spin .7s linear infinite; }
@keyframes spin { to{transform:rotate(360deg)} }
.spin-label { font-size:12px; color:var(--muted); }
</style>
