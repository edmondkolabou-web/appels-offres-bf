import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/auth', component: () => import('@/views/AuthView.vue'), meta: { guest: true } },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/DashboardView.vue') },
      { path: 'aos',       name: 'AOList',    component: () => import('@/views/AOListView.vue') },
      { path: 'aos/:id',   name: 'AODetail',  component: () => import('@/views/AODetailView.vue'), props: true },
      { path: 'favoris',   name: 'Favoris',   component: () => import('@/views/FavorisView.vue') },
      { path: 'alertes',   name: 'Alertes',   component: () => import('@/views/AlertesView.vue') },

      { path: 'profil',    name: 'Profil',    component: () => import('@/views/ProfilView.vue') },
      { path: 'candidatures',     name: 'Candidatures',  component: () => import('@/views/CandidaturesView.vue') },
      { path: 'candidatures/:id', name: 'CandidatureDetail', component: () => import('@/views/CandidaturesView.vue'), props: true },
      { path: 'conformite',       name: 'Conformite',    component: () => import('@/views/ConformiteView.vue') },
      { path: 'intelligence',     name: 'Intelligence',  component: () => import('@/views/IntelligenceView.vue') },
      { path: 'institutions',     name: 'Institutions',  component: () => import('@/views/InstitutionsView.vue') },
      { path: 'admin', name: 'Admin', component: () => import('@/views/AdminView.vue') },
      { path: 'assistant',        name: 'Assistant',     component: () => import('@/views/AssistantView.vue') },
    ],
  },
  { path: '/pricing', name: 'Pricing', component: () => import('@/views/PricingView.vue') },
  { path: '/legal', name: 'Legal', component: () => import('@/views/LegalView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { path: '/auth', query: { redirect: to.fullPath } }
  }
  if (to.meta.guest && auth.isAuthenticated) {
    return { path: '/dashboard' }
  }
})

export default router
