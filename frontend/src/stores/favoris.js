import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { favorisApi } from '@/api'
import { useToastStore } from './toast'

export const useFavorisStore = defineStore('favoris', () => {
  const items   = ref([])
  const loading = ref(false)

  const aoIds = computed(() => new Set(items.value.map(f => f.ao.id)))

  async function fetch() {
    loading.value = true
    try {
      const { data } = await favorisApi.list()
      items.value = data
    } finally {
      loading.value = false
    }
  }

  async function toggle(aoId) {
    if (aoIds.value.has(aoId)) {
      await favorisApi.remove(aoId)
      items.value = items.value.filter(f => f.ao.id !== aoId)
      useToastStore().add('Retiré des favoris')
    } else {
      const { data } = await favorisApi.add({ ao_id: aoId })
      items.value.unshift(data)
      useToastStore().add('Ajouté aux favoris', 'success')
    }
  }

  async function updateNote(aoId, note) {
    const { data } = await favorisApi.update(aoId, note)
    const idx = items.value.findIndex(f => f.ao.id === aoId)
    if (idx !== -1) items.value[idx] = data
    useToastStore().add('Note mise à jour', 'success')
  }

  return { items, loading, aoIds, fetch, toggle, updateNote }
})
