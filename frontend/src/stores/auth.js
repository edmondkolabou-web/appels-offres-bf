import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'
import { useToastStore } from './toast'

export const useAuthStore = defineStore('auth', () => {
  const token   = ref(localStorage.getItem('token') || null)
  const abonne  = ref(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value)
  const isPro = computed(() => abonne.value?.est_pro || false)
  const plan  = computed(() => abonne.value?.plan || 'gratuit')
  const initiales = computed(() => {
    if (!abonne.value) return '?'
    return (abonne.value.prenom?.[0] || '') + (abonne.value.nom?.[0] || '')
  })

  async function login(email, password) {
    loading.value = true
    try {
      const { data } = await authApi.login({ email, password })
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)
      await fetchMe()
      return true
    } catch (err) {
      useToastStore().add(err.response?.data?.detail || 'Erreur de connexion', 'error')
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(payload) {
    loading.value = true
    try {
      const { data } = await authApi.register(payload)
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)
      await fetchMe()
      return true
    } catch (err) {
      useToastStore().add(err.response?.data?.detail || 'Erreur inscription', 'error')
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const { data } = await authApi.me()
      abonne.value = data
    } catch {
      logout()
    }
  }

  async function updateProfil(payload) {
    try {
      const { data } = await authApi.updateMe(payload)
      abonne.value = data
      useToastStore().add('Profil mis à jour', 'success')
    } catch (err) {
      useToastStore().add(err.response?.data?.detail || 'Erreur', 'error')
    }
  }

  function logout() {
    token.value  = null
    abonne.value = null
    localStorage.removeItem('token')
  }

  return { token, abonne, loading, isAuthenticated, isPro, plan, initiales,
           login, register, fetchMe, updateProfil, logout }
})
