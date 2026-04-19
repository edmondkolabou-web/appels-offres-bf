<template>
  <div class="pricing-page">
    <div class="pricing-hero">
      <div class="pricing-tag">Tarifs NetSync Gov</div>
      <h1 class="pricing-title">Simple, transparent,<br><em>payable en Mobile Money</em></h1>
      <div class="billing-toggle">
        <span :class="{ active: billing === 'monthly' }" @click="billing = 'monthly'">Mensuel</span>
        <div class="toggle-switch" :class="{ annual: billing === 'annual' }" @click="toggleBilling" role="switch" :aria-checked="billing === 'annual'" aria-label="Facturation annuelle">
          <div class="toggle-thumb"></div>
        </div>
        <span :class="{ active: billing === 'annual' }" @click="billing = 'annual'">Annuel <span class="badge-off">-20%</span></span>
      </div>
    </div>

    <div class="plans-grid">
      <!-- Gratuit -->
      <div class="plan-card card">
        <div class="plan-name">Gratuit</div>
        <div class="plan-price">0 <span class="plan-unit">FCFA / mois</span></div>
        <div class="plan-divider"></div>
        <ul class="plan-feats">
          <li class="feat-ok">3 AO consultables par jour</li>
          <li class="feat-ok">Recherche basique</li>
          <li class="feat-off">Alertes email / WhatsApp</li>
          <li class="feat-off">Historique des AO</li>
          <li class="feat-off">Filtres avancés</li>
        </ul>
        <RouterLink to="/auth" class="btn btn-ghost" style="width:100%;justify-content:center;">Commencer gratuitement</RouterLink>
      </div>

      <!-- Pro -->
      <div class="plan-card card featured">
        <div class="plan-badge">Recommandé</div>
        <div class="plan-current" v-if="authStore.plan === 'pro'">✓ Votre plan actuel</div>
        <div class="plan-name">Pro</div>
        <div class="plan-price">{{ proPrice.toLocaleString('fr-FR') }} <span class="plan-unit">FCFA / mois</span></div>
        <div v-if="billing === 'annual'" class="plan-annual">Soit 144 000 FCFA / an (-20%)</div>
        <div class="plan-divider"></div>
        <ul class="plan-feats">
          <li class="feat-ok">AO illimités</li>
          <li class="feat-ok">Alertes email + WhatsApp</li>
          <li class="feat-ok">Filtres avancés</li>
          <li class="feat-ok">Historique 12 mois</li>
          <li class="feat-ok">Rappels clôture J-3</li>
          <li class="feat-ok">Multi-sources (DGCMEF, UNDP, BM)</li>
        </ul>
        <button class="btn btn-primary" style="width:100%;justify-content:center;" @click="initiatePaiement('pro')" :disabled="paying">
          <div v-if="paying" class="spinner"></div>
          {{ authStore.plan === 'pro' ? 'Renouveler' : 'Choisir Pro' }} — {{ proPrice.toLocaleString('fr-FR') }} FCFA
        </button>
      </div>

      <!-- Équipe -->
      <div class="plan-card card">
        <div class="plan-badge green">Nouveau</div>
        <div class="plan-name">Équipe</div>
        <div class="plan-price">{{ teamPrice.toLocaleString('fr-FR') }} <span class="plan-unit">FCFA / mois</span></div>
        <div class="plan-divider"></div>
        <ul class="plan-feats">
          <li class="feat-ok">Tout Pro inclus</li>
          <li class="feat-ok">5 comptes utilisateurs</li>
          <li class="feat-ok">Dashboard équipe partagé</li>
          <li class="feat-ok">Suivi candidatures</li>
          <li class="feat-ok">Export CSV</li>
        </ul>
        <button class="btn" style="width:100%;justify-content:center;background:var(--ink);color:white;" @click="initiatePaiement('equipe')" :disabled="paying">
          Passer au plan Équipe →
        </button>
      </div>
    </div>

    <!-- Section paiement -->
    <div v-if="showPayment" class="payment-section card">
      <h2 class="pay-title">Finaliser votre abonnement — Plan {{ selectedPlan?.toUpperCase() }}</h2>
      <div class="method-grid">
        <div class="method" :class="{ selected: method === 'om' }" @click="method = 'om'" role="radio" :aria-checked="method === 'om'">🟠 Orange Money</div>
        <div class="method" :class="{ selected: method === 'mv' }" @click="method = 'mv'" role="radio" :aria-checked="method === 'mv'">🔵 Moov Money</div>
        <div class="method" :class="{ selected: method === 'card' }" @click="method = 'card'" role="radio" :aria-checked="method === 'card'">💳 Carte bancaire</div>
      </div>
      <div class="order-summary">
        <div class="order-row"><span>Plan</span><span>{{ selectedPlan === 'pro' ? 'Pro' : 'Équipe' }}</span></div>
        <div class="order-row"><span>Période</span><span>{{ billing === 'annual' ? 'Annuel (-20%)' : 'Mensuel' }}</span></div>
        <div class="order-divider"></div>
        <div class="order-total"><span>Total</span><span class="total-val">{{ totalAmount.toLocaleString('fr-FR') }} FCFA</span></div>
      </div>
      <button class="btn btn-primary" style="width:100%;justify-content:center;padding:13px;font-size:15px;" @click="confirmPay" :disabled="paying">
        <div v-if="paying" class="spinner"></div>
        Confirmer et payer — {{ totalAmount.toLocaleString('fr-FR') }} FCFA
      </button>
      <p class="pay-secure">🔒 Paiement sécurisé via CinetPay · SSL</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { paiementsApi } from '@/api'

const authStore  = useAuthStore()
const toastStore = useToastStore()

const billing      = ref('monthly')
const showPayment  = ref(false)
const selectedPlan = ref(null)
const method       = ref('om')
const paying       = ref(false)

const TARIFS = { pro: { monthly: 15000, annual: 12000 }, equipe: { monthly: 45000, annual: 36000 } }
const proPrice    = computed(() => TARIFS.pro[billing.value === 'annual' ? 'annual' : 'monthly'])
const teamPrice   = computed(() => TARIFS.equipe[billing.value === 'annual' ? 'annual' : 'monthly'])
const totalAmount = computed(() => selectedPlan.value ? TARIFS[selectedPlan.value][billing.value === 'annual' ? 'annual' : 'monthly'] : 0)

function toggleBilling() { billing.value = billing.value === 'monthly' ? 'annual' : 'monthly' }
function initiatePaiement(plan) { selectedPlan.value = plan; showPayment.value = true }

async function confirmPay() {
  paying.value = true
  try {
    const { data } = await paiementsApi.initier({ plan: selectedPlan.value, periode: billing.value === 'annual' ? 'annuel' : 'mensuel', methode: method.value })
    if (data.metadata_?.payment_url) {
      window.location.href = data.metadata_.payment_url
    } else {
      toastStore.add('Paiement initié — confirmation en attente', 'success')
      showPayment.value = false
    }
  } catch (err) {
    toastStore.add(err.response?.data?.detail || 'Erreur paiement', 'error')
  } finally {
    paying.value = false
  }
}
</script>

<style scoped>
.pricing-page { display:flex; flex-direction:column; gap:1.5rem; }
.pricing-hero { background:var(--ink); border-radius:var(--radius-xl); padding:2.5rem; text-align:center; }
.pricing-tag { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.08em; color:rgba(255,255,255,.4); margin-bottom:.75rem; }
.pricing-title { font-family:var(--font-display); font-size:2rem; color:var(--white); line-height:1.2; margin-bottom:1.5rem; }
.pricing-title em { font-style:italic; color:var(--blue-300); }
.billing-toggle { display:inline-flex; align-items:center; gap:.875rem; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.1); border-radius:var(--radius-full); padding:5px 16px; }
.billing-toggle span { font-size:13px; color:rgba(255,255,255,.45); cursor:pointer; }
.billing-toggle span.active { color:var(--white); font-weight:500; }
.toggle-switch { width:38px; height:22px; border-radius:var(--radius-full); background:var(--blue-500); position:relative; cursor:pointer; }
.toggle-switch .toggle-thumb { position:absolute; top:3px; left:3px; width:16px; height:16px; border-radius:50%; background:var(--white); transition:left .2s; }
.toggle-switch.annual .toggle-thumb { left:19px; }
.badge-off { font-size:9px; font-weight:600; background:var(--green-400); color:var(--white); padding:1px 6px; border-radius:var(--radius-full); margin-left:4px; }
.plans-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:1.25rem; }
.plan-card { padding:2rem; position:relative; }
.plan-card.featured { border:2px solid var(--blue-500); box-shadow:var(--shadow-blue); }
.plan-badge { position:absolute; top:-12px; left:50%; transform:translateX(-50%); background:var(--blue-500); color:var(--white); font-size:11px; font-weight:600; padding:3px 14px; border-radius:var(--radius-full); }
.plan-badge.green { background:var(--green-400); }
.plan-current { font-size:11px; font-weight:600; color:var(--green-600); background:var(--green-50); padding:2px 8px; border-radius:var(--radius-full); display:inline-block; margin-bottom:.75rem; }
.plan-name { font-size:13px; font-weight:500; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; margin-bottom:.625rem; }
.plan-price { font-family:var(--font-display); font-size:2rem; color:var(--ink); line-height:1; }
.plan-unit { font-size:12px; color:var(--muted); font-family:var(--font-body); }
.plan-annual { font-size:11px; color:var(--green-600); margin-top:3px; }
.plan-divider { height:1px; background:var(--border); margin:1.25rem 0; }
.plan-feats { list-style:none; display:flex; flex-direction:column; gap:.5rem; margin-bottom:1.5rem; }
.plan-feats li { font-size:13px; padding-left:1.25rem; position:relative; }
.feat-ok::before { content:'✓'; position:absolute; left:0; color:var(--green-400); font-weight:700; }
.feat-off { color:var(--muted); opacity:.6; }
.feat-off::before { content:'–'; position:absolute; left:0; color:var(--border-md); }
.payment-section { padding:2rem; max-width:560px; margin:0 auto; width:100%; }
.pay-title { font-size:16px; font-weight:600; color:var(--ink); margin-bottom:1.25rem; }
.method-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:.75rem; margin-bottom:1.5rem; }
.method { border:1.5px solid var(--border); border-radius:var(--radius-lg); padding:.875rem .5rem; cursor:pointer; text-align:center; font-size:12px; font-weight:500; transition:all .2s; }
.method:hover, .method.selected { border-color:var(--blue-500); background:var(--blue-50); }
.order-summary { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); padding:1rem; margin-bottom:1.25rem; }
.order-row { display:flex; justify-content:space-between; font-size:13px; padding:.25rem 0; color:var(--muted); }
.order-divider { height:1px; background:var(--border); margin:.5rem 0; }
.order-total { display:flex; justify-content:space-between; font-size:15px; font-weight:600; }
.total-val { color:var(--blue-500); font-family:var(--font-mono); }
.pay-secure { font-size:11px; color:var(--muted); text-align:center; margin-top:.75rem; }
@media(max-width:900px) { .plans-grid { grid-template-columns:1fr; } }
</style>
