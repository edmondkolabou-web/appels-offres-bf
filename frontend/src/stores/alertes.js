import { defineStore } from 'pinia'
import { ref } from 'vue'
import { alertesApi } from '@/api'
import { useToastStore } from './toast'

export const useAlertesStore = defineStore('alertes', () => {
  const items   = ref([])
  const loading = ref(false)

  async function fetch() {
    loading.value = true
    try {
      const { data } = await alertesApi.list()
      items.value = data
    } finally {
      loading.value = false
    }
  }

  async function create(payload) {
    const { data } = await alertesApi.create(payload)
    items.value.unshift(data)
    useToastStore().add('Alerte créée', 'success')
    return data
  }

  async function toggle(id) {
    const { data } = await alertesApi.toggle(id)
    const idx = items.value.findIndex(a => a.id === id)
    if (idx !== -1) items.value[idx] = data
    useToastStore().add(data.actif ? 'Alerte activée' : 'Alerte désactivée')
  }

  async function update(id, payload) {
    const { data } = await alertesApi.update(id, payload)
    const idx = items.value.findIndex(a => a.id === id)
    if (idx !== -1) items.value[idx] = data
    useToastStore().add('Alerte mise à jour', 'success')
  }

  async function remove(id) {
    await alertesApi.delete(id)
    items.value = items.value.filter(a => a.id !== id)
    useToastStore().add('Alerte supprimée')
  }

  return { items, loading, fetch, create, toggle, update, remove }
})
