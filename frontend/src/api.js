import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/auth'
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
  verifyEmail:    (token)           => api.post('/auth/verify-email', null, { params: { token } }),
  forgotPassword: (email)           => api.post('/auth/forgot-password', null, { params: { email } }),
  resetPassword:  (token, password) => api.post('/auth/reset-password', null, { params: { token, new_password: password } }),
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

export default api
