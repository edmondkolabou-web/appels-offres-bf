<template>
  <div class="auth-page">
    <!-- Panneau gauche -->
    <div class="auth-left">
      <div class="auth-left-bg"></div>
      <div class="auth-brand">
        <div class="brand-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>
        </div>
        <span class="brand-name">NetSync Gov</span>
      </div>
      <h1 class="auth-tagline">Ne rate plus<br>aucun <em>appel d'offres</em><br>au Burkina Faso</h1>
      <p class="auth-sub">Agrégation automatique du Quotidien DGCMEF chaque matin. Alertes WhatsApp + email dès la publication.</p>
      <div class="auth-stats">
        <div class="stat-item"><div class="stat-val">714+</div><div class="stat-lbl">Quotidiens indexés</div></div>
        <div class="stat-item"><div class="stat-val">07h00</div><div class="stat-lbl">Heure d'alerte</div></div>
        <div class="stat-item"><div class="stat-val">0</div><div class="stat-lbl">Concurrent local</div></div>
        <div class="stat-item"><div class="stat-val">15k</div><div class="stat-lbl">FCFA/mois Pro</div></div>
      </div>
    </div>

    <!-- Panneau droit -->
    <div class="auth-right">
      <div class="auth-box">
        <!-- Tabs -->
        <div class="auth-tabs" role="tablist">
          <button role="tab" class="auth-tab" :class="{ active: tab === 'login' }" @click="tab = 'login'" :aria-selected="tab === 'login'">Se connecter</button>
          <button role="tab" class="auth-tab" :class="{ active: tab === 'register' }" @click="tab = 'register'" :aria-selected="tab === 'register'">Créer un compte</button>
        </div>

        <!-- Connexion -->
        <div v-if="tab === 'login'">
          <h2 class="form-heading">Bon retour 👋</h2>
          <p class="form-sub">Connecte-toi pour accéder à tes alertes et tes AO.</p>
          <div class="form-group">
            <label class="form-label" for="login-email">Email</label>
            <input id="login-email" class="form-input" type="email" v-model="loginForm.email" placeholder="vous@entreprise.bf" autocomplete="email" />
          </div>
          <div class="form-group">
            <label class="form-label" for="login-password">Mot de passe</label>
            <input id="login-password" class="form-input" :type="showPwd ? 'text' : 'password'" v-model="loginForm.password" placeholder="••••••••" autocomplete="current-password" @keyup.enter="handleLogin" />
          </div>
          <p v-if="loginError" class="error-msg" role="alert">{{ loginError }}</p>
          <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" :disabled="authStore.loading" @click="handleLogin">
            <div v-if="authStore.loading" class="spinner"></div>
            <span>{{ authStore.loading ? 'Connexion…' : 'Se connecter' }}</span>
          </button>
          <p class="auth-switch">Pas de compte ? <button @click="tab = 'register'">S'inscrire gratuitement →</button></p>
        </div>

        <!-- Inscription -->
        <div v-else>
          <h2 class="form-heading">Créer ton compte</h2>
          <p class="form-sub">Gratuit pour commencer. Pas de carte requise.</p>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem;">
            <div class="form-group">
              <label class="form-label">Prénom</label>
              <input class="form-input" type="text" v-model="regForm.prenom" placeholder="Adama" autocomplete="given-name" />
            </div>
            <div class="form-group">
              <label class="form-label">Nom</label>
              <input class="form-input" type="text" v-model="regForm.nom" placeholder="Kaboré" autocomplete="family-name" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Email</label>
            <input class="form-input" type="email" v-model="regForm.email" placeholder="vous@entreprise.bf" autocomplete="email" />
          </div>
          <div class="form-group">
            <label class="form-label">Numéro WhatsApp <span style="color:var(--muted);font-weight:400;">(optionnel)</span></label>
            <input class="form-input" type="tel" v-model="regForm.whatsapp" placeholder="+226 70 00 00 00" autocomplete="tel" />
          </div>
          <div class="form-group">
            <label class="form-label">Mot de passe</label>
            <input class="form-input" type="password" v-model="regForm.password" placeholder="8 caractères minimum" autocomplete="new-password" />
            <div class="pw-bars">
              <div v-for="i in 4" :key="i" class="pw-bar" :class="pwClass(i)"></div>
            </div>
          </div>
          <p v-if="regError" class="error-msg" role="alert">{{ regError }}</p>
          <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" :disabled="authStore.loading" @click="handleRegister">
            <div v-if="authStore.loading" class="spinner"></div>
            <span>{{ authStore.loading ? 'Création…' : 'Créer mon compte →' }}</span>
          </button>
          <p class="auth-switch">Déjà un compte ? <button @click="tab = 'login'">Se connecter</button></p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router    = useRouter()
const route     = useRoute()
const authStore = useAuthStore()

const tab      = ref('login')
const showPwd  = ref(false)
const loginError = ref('')
const regError   = ref('')

const loginForm = reactive({ email: '', password: '' })
const regForm   = reactive({ prenom: '', nom: '', email: '', whatsapp: '', password: '', plan: 'gratuit', secteurs: [] })

async function handleLogin() {
  loginError.value = ''
  if (!loginForm.email || !loginForm.password) { loginError.value = 'Remplis tous les champs'; return }
  const ok = await authStore.login(loginForm.email, loginForm.password)
  if (ok) router.push(route.query.redirect || '/dashboard')
  else loginError.value = 'Email ou mot de passe incorrect'
}

async function handleRegister() {
  regError.value = ''
  if (!regForm.prenom || !regForm.nom || !regForm.email || !regForm.password) { regError.value = 'Remplis tous les champs'; return }
  if (regForm.password.length < 8) { regError.value = 'Mot de passe trop court (8 caractères minimum)'; return }
  const ok = await authStore.register(regForm)
  if (ok) router.push('/dashboard')
  else regError.value = 'Erreur lors de la création du compte'
}

function pwStrength(pwd) {
  let s = 0
  if (pwd.length >= 8) s++
  if (/[A-Z]/.test(pwd)) s++
  if (/[0-9]/.test(pwd)) s++
  if (/[^A-Za-z0-9]/.test(pwd)) s++
  return s
}
function pwClass(i) {
  const s = pwStrength(regForm.password)
  if (i > s) return ''
  if (s === 1) return 'weak'
  if (s <= 3)  return 'medium'
  return 'strong'
}
</script>

<style scoped>
.auth-page { display:grid; grid-template-columns:1fr 1fr; min-height:100vh; }
.auth-left { background:var(--ink); padding:2.5rem; position:relative; overflow:hidden; display:flex; flex-direction:column; gap:1.5rem; }
.auth-left-bg { position:absolute; inset:0; background-image:radial-gradient(circle at 2px 2px,rgba(255,255,255,.04) 1px,transparent 0); background-size:28px 28px; }
.auth-brand { display:flex; align-items:center; gap:10px; position:relative; z-index:1; }
.brand-icon { width:36px; height:36px; background:var(--blue-500); border-radius:var(--radius-md); display:flex; align-items:center; justify-content:center; }
.brand-name { font-family:var(--font-display); font-size:1.1rem; color:var(--white); }
.auth-tagline { font-family:var(--font-display); font-size:clamp(1.6rem,3vw,2.4rem); color:var(--white); line-height:1.2; position:relative; z-index:1; }
.auth-tagline em { font-style:italic; color:var(--blue-300); }
.auth-sub { font-size:13px; color:rgba(255,255,255,.5); line-height:1.7; position:relative; z-index:1; max-width:360px; }
.auth-stats { display:grid; grid-template-columns:1fr 1fr; gap:.75rem; position:relative; z-index:1; margin-top:auto; }
.stat-item { background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); border-radius:var(--radius-lg); padding:.875rem 1rem; }
.stat-val { font-family:var(--font-display); font-size:1.5rem; color:var(--white); }
.stat-lbl { font-size:11px; color:rgba(255,255,255,.4); margin-top:2px; }
.auth-right { display:flex; align-items:center; justify-content:center; padding:2.5rem; background:var(--white); }
.auth-box { width:100%; max-width:400px; }
.auth-tabs { display:flex; background:var(--surface); border-radius:var(--radius-xl); padding:4px; margin-bottom:1.75rem; }
.auth-tab { flex:1; padding:9px; text-align:center; font-size:13px; font-weight:500; border-radius:var(--radius-lg); cursor:pointer; border:none; background:none; color:var(--muted); transition:all var(--transition-base); font-family:var(--font-body); }
.auth-tab.active { background:var(--white); color:var(--ink); box-shadow:var(--shadow-sm); }
.form-heading { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); margin-bottom:.375rem; }
.form-sub { font-size:13px; color:var(--muted); margin-bottom:1.5rem; }
.error-msg { font-size:12px; color:var(--red-600); margin-bottom:.75rem; }
.auth-switch { font-size:12px; color:var(--muted); text-align:center; margin-top:1rem; }
.auth-switch button { background:none; border:none; color:var(--blue-500); cursor:pointer; font-family:var(--font-body); font-size:12px; }
.pw-bars { display:flex; gap:4px; margin-top:6px; }
.pw-bar { height:3px; flex:1; border-radius:2px; background:var(--border); }
.pw-bar.weak   { background:var(--red-400); }
.pw-bar.medium { background:var(--amber-400); }
.pw-bar.strong { background:var(--green-400); }
@media(max-width:768px) { .auth-page{grid-template-columns:1fr;} .auth-left{display:none;} }
</style>
