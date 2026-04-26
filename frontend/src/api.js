import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// Ajouter le token à chaque requête
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Gérer le refresh automatique du token
let isRefreshing = false
let failedQueue = []

function processQueue(error, token = null) {
  failedQueue.forEach(prom => {
    if (error) prom.reject(error)
    else prom.resolve(token)
  })
  failedQueue = []
}

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config

    if (err.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refresh_token')

      if (!refreshToken) {
        localStorage.removeItem('token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/auth'
        return Promise.reject(err)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken,
        })

        localStorage.setItem('token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)

        api.defaults.headers.Authorization = `Bearer ${data.access_token}`
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`

        processQueue(null, data.access_token)
        return api(originalRequest)
      } catch (refreshErr) {
        processQueue(refreshErr, null)
        localStorage.removeItem('token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/auth'
        return Promise.reject(refreshErr)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(err)
  }
)

export const aoApi = {
  list:     (params) => api.get('/aos', { params }),
  detail:   (id)     => api.get(`/aos/${id}`),
  today:    (params) => api.get('/aos/today', { params }),
  urgent:   ()       => api.get('/aos/urgent'),
  secteurs: ()       => api.get('/aos/secteurs'),
}

export const authApi = {
  register:       (data)            => api.post('/auth/register', data),
  login:          (data)            => api.post('/auth/login', data),
  me:             ()                => api.get('/auth/me'),
  updateMe:       (data)            => api.put('/auth/me', data),
  verifyEmail:    (token)           => api.post('/auth/verify-email', { token }),
  forgotPassword: (email)           => api.post('/auth/forgot-password', { email }),
  resetPassword:  (token, password) => api.post('/auth/reset-password', { token, new_password: password }),
}

export const alertesApi = {
  list:   ()         => api.get('/alertes'),
  create: (data)     => api.post('/alertes', data),
  update: (id, data) => api.put(`/alertes/${id}`, data),
  toggle: (id)       => api.post(`/alertes/${id}/toggle`),
  delete: (id)       => api.delete(`/alertes/${id}`),
}

export const favorisApi = {
  list:   ()              => api.get('/favoris'),
  add:    (data)          => api.post('/favoris', data),
  update: (aoId, note)    => api.put(`/favoris/${aoId}`, null, { params: { note } }),
  remove: (aoId)          => api.delete(`/favoris/${aoId}`),
}

export const paiementsApi = {
  initier:    (data) => api.post('/paiements/initier', data),
  historique: ()     => api.get('/paiements/historique'),
  statut:     (id)   => api.get(`/paiements/statut/${id}`),
}



export const candidaturesApi = {
  list:       (params) => api.get('/candidatures', { params }),
  detail:     (id)     => api.get(`/candidatures/${id}`),
  create:     (data)   => api.post('/candidatures', data),
  update:     (id, data) => api.put(`/candidatures/${id}`, data),
  checklist:  (id)     => api.post(`/candidatures/${id}/checklist`),
  genererOffre: (id, data) => api.post(`/candidatures/${id}/generer`, data),
  validerOffre: (offreId) => api.put(`/candidatures/${offreId}/valider`),
}

export const conformiteApi = {
  score:      ()       => api.get('/conformite/score'),
  pieces:     ()       => api.get('/conformite/pieces'),
  calendrier: (jours)  => api.get('/conformite/calendrier', { params: { jours } }),
  catalogue:  ()       => api.get('/conformite/catalogue'),
  verifier:   (aoId)   => api.get(`/conformite/verifier-candidature/${aoId}`),
}

export const intelligenceApi = {
  resume:     ()       => api.get('/intelligence/resume'),
  secteurs:   (params) => api.get('/intelligence/tendances/secteurs', { params }),
  evolution:  (params) => api.get('/intelligence/tendances/evolution', { params }),
  autorites:  (params) => api.get('/intelligence/autorites', { params }),
  procedures: (params) => api.get('/intelligence/tendances/types-procedures', { params }),
  rapport:    ()       => api.get('/intelligence/rapport/mensuel', { responseType: 'blob' }),
}

export const institutionsApi = {
  dashboard:  ()       => api.get('/mon-institution/dashboard'),
  profil:     (data)   => api.put('/mon-institution/profil', data),
  enrichir:   (data)   => api.post('/mon-institution/enrichir-ao', data),
  notifier:   (data)   => api.post('/mon-institution/notifier-soumissionnaires', data),
  rapport:    (mois)   => api.get('/mon-institution/rapport-activite', { params: { mois }, responseType: 'blob' }),
}

export const piecesApi = {
  list:       ()       => api.get('/pieces'),
  expiration: (jours)  => api.get('/pieces/expiration', { params: { jours } }),
  upload:     (data)   => api.post('/pieces', data, { headers: { 'Content-Type': 'multipart/form-data' } }),
  delete:     (id)     => api.delete(`/pieces/${id}`),
}


export const assistantApi = {
  chat:        (data) => api.post('/assistant/chat', data),
  suggestions: ()     => api.get('/assistant/suggestions'),
}

export default api
