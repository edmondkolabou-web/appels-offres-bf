import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { aoApi } from '@/api'
import { useToastStore } from './toast'

export const useAOStore = defineStore('aos', () => {
  const list       = ref([])
  const current    = ref(null)
  const total      = ref(0)
  const pages      = ref(1)
  const loading    = ref(false)
  const secteurs   = ref([])

  const filters = reactive({
    q: '', secteur: '', statut: 'ouvert', source: '',
    type_procedure: '', urgent_only: false,
    page: 1, per_page: 20,
  })

  async function fetchList() {
    loading.value = true
    try {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== '' && v !== false)
      )
      const { data } = await aoApi.list(params)
      list.value  = data.items
      total.value = data.total
      pages.value = data.pages
    } catch (err) {
      if (err.response?.status === 402) {
        useToastStore().add('Limite journalière atteinte — passez au plan Pro', 'error', 5000)
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    loading.value = true
    current.value = null
    try {
      const { data } = await aoApi.detail(id)
      current.value = data
    } catch (err) {
      useToastStore().add('AO introuvable', 'error')
    } finally {
      loading.value = false
    }
  }

  async function fetchSecteurs() {
    try {
      const { data } = await aoApi.secteurs()
      secteurs.value = data
    } catch { /* silencieux */ }
  }

  function setFilter(key, value) {
    filters[key] = value
    if (key !== 'page') filters.page = 1
  }

  function resetFilters() {
    Object.assign(filters, { q: '', secteur: '', statut: 'ouvert', source: '',
      type_procedure: '', urgent_only: false, page: 1 })
  }

  return { list, current, total, pages, loading, secteurs, filters,
           fetchList, fetchDetail, fetchSecteurs, setFilter, resetFilters }
})
