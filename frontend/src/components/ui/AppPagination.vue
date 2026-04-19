<template>
  <div v-if="pages > 1" class="pagination">
    <button class="page-btn" :disabled="modelValue === 1" @click="$emit('update:modelValue', modelValue-1)" aria-label="Page précédente">←</button>
    <template v-for="p in pageRange" :key="p">
      <span v-if="p === '...'" style="padding:0 4px;color:var(--muted)">…</span>
      <button v-else class="page-btn" :class="{ active: p === modelValue }" @click="$emit('update:modelValue', p)">{{ p }}</button>
    </template>
    <button class="page-btn" :disabled="modelValue === pages" @click="$emit('update:modelValue', modelValue+1)" aria-label="Page suivante">→</button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ modelValue: Number, pages: Number })
defineEmits(['update:modelValue'])

const pageRange = computed(() => {
  const p = props.pages, c = props.modelValue
  if (p <= 7) return Array.from({length: p}, (_,i) => i+1)
  const r = []
  if (c > 3) r.push(1, '...')
  for (let i = Math.max(1, c-1); i <= Math.min(p, c+1); i++) r.push(i)
  if (c < p-2) r.push('...', p)
  return r
})
</script>
