// NetSync Gov Candidature — Store Pinia
import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from '@/api'
import { useToastStore } from './toast'

export const useCandidaturesStore = defineStore('candidatures', () => {
  const list    = ref([])
  const current = ref(null)
  const loading = ref(false)

  const api = {
    list:           (params) => axios.get('/candidatures', { params }),
    create:         (body)   => axios.post('/candidatures', body),
    get:            (id)     => axios.get(`/candidatures/${id}`),
    update:         (id, b)  => axios.put(`/candidatures/${id}`, b),
    delete:         (id)     => axios.delete(`/candidatures/${id}`),
    checklist:      (id)     => axios.post(`/candidatures/${id}/checklist`),
    genererOffre:   (id, b)  => axios.post(`/offres-ia/${id}/generer`, b),
    validerOffre:   (id)     => axios.put(`/offres-ia/${id}/valider`),
    createTache:    (id, b)  => axios.post(`/taches/${id}/taches`, b),
    updateTache:    (id, b)  => axios.put(`/taches/${id}`, b),
    pieces:         ()       => axios.get('/pieces'),
    piecesExpiration: ()     => axios.get('/pieces/expiration'),
    uploadPiece:    (fd)     => axios.post('/pieces', fd, { headers: { 'Content-Type': 'multipart/form-data' } }),
    deletePiece:    (id)     => axios.delete(`/pieces/${id}`),
  }

  async function fetchList(statut = null) {
    loading.value = true
    try {
      const params = statut ? { statut } : {}
      const { data } = await api.list(params)
      list.value = data
    } finally {
      loading.value = false
    }
  }

  async function create(aoId, notes = null) {
    const { data } = await api.create({ ao_id: aoId, notes })
    await fetchList()
    useToastStore().add('Candidature créée', 'success')
    return data
  }

  async function fetchDetail(id) {
    loading.value = true
    try {
      const { data } = await api.get(id)
      current.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function updateStatut(id, statut) {
    await api.update(id, { statut })
    const item = list.value.find(c => c.id === id)
    if (item) item.statut = statut
    useToastStore().add('Statut mis à jour')
  }

  async function genererOffre(candidatureId, payload) {
    useToastStore().add('Génération en cours…', 'info', 8000)
    try {
      const { data } = await api.genererOffre(candidatureId, payload)
      useToastStore().add('Offre technique générée !', 'success')
      return data
    } catch (e) {
      useToastStore().add("Erreur lors de la génération", 'error')
      throw e
    }
  }

  return {
    list, current, loading,
    fetchList, create, fetchDetail, updateStatut, genererOffre,
    api,
  }
})
