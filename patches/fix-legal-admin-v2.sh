#!/bin/bash
set -e
cd ~/appels-offres-bf
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Patch #9 : CGU + APDP + Admin                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# 1. LegalView.vue
echo "🔧 [1/3] Page CGU + Mentions + APDP..."
cat > frontend/src/views/LegalView.vue << 'VEOF'
<template>
<div class="legal-page">
<div class="legal-nav"><RouterLink to="/" class="back">← Retour</RouterLink></div>
<div class="tabs"><button :class="{active:tab==='cgu'}" @click="tab='cgu'">CGU</button><button :class="{active:tab==='mentions'}" @click="tab='mentions'">Mentions légales</button><button :class="{active:tab==='apdp'}" @click="tab='apdp'">Confidentialité APDP</button></div>
<div v-if="tab==='cgu'" class="content card">
<h1>Conditions Générales d'Utilisation</h1><p class="date">Mise à jour : avril 2026</p>
<h2>1. Objet</h2><p>Les présentes CGU régissent l'utilisation de NetSync Gov, plateforme d'agrégation des appels d'offres publics du Burkina Faso, éditée par NetSync Africa.</p>
<h2>2. Acceptation</h2><p>L'inscription implique l'acceptation pleine des présentes CGU.</p>
<h2>3. Services</h2><ul><li><b>Gratuit :</b> 3 AOs/jour, recherche basique</li><li><b>Pro (15 000 FCFA/mois) :</b> illimité, alertes WhatsApp/email, assistant IA</li><li><b>Équipe (45 000 FCFA/mois) :</b> 5 utilisateurs, dashboard partagé</li></ul>
<h2>4. Inscription</h2><p>L'utilisateur fournit des informations exactes. Un essai Pro de 7 jours est offert à l'inscription.</p>
<h2>5. Données</h2><p>Les AOs proviennent de sources publiques (DGCMEF, CCI-BF, UNDP). NetSync Gov ne garantit pas l'exhaustivité absolue.</p>
<h2>6. Paiement</h2><p>Via CinetPay (Orange Money, Moov Money). Abonnement sans engagement, annulation à tout moment.</p>
<h2>7. Propriété intellectuelle</h2><p>La plateforme est la propriété de NetSync Africa. Les données AO restent propriété des autorités émettrices.</p>
<h2>8. Responsabilité</h2><p>NetSync Africa ne saurait être tenu responsable des conséquences liées à l'utilisation des informations diffusées.</p>
<h2>9. Résiliation</h2><p>Suppression de compte possible à tout moment depuis le profil.</p>
<h2>10. Droit applicable</h2><p>Droit burkinabè. Tribunaux de Ouagadougou.</p>
<h2>11. Contact</h2><p><b>legal@netsync.bf</b></p>
</div>
<div v-if="tab==='mentions'" class="content card">
<h1>Mentions légales</h1>
<h2>Éditeur</h2><ul><li><b>NetSync Africa</b> — Edmond Kolabou</li><li>Ouagadougou, Burkina Faso</li><li>contact@netsync.bf</li></ul>
<h2>Hébergement</h2><ul><li>Hostinger International Ltd — Larnaca, Cyprus</li></ul>
<h2>Directeur de publication</h2><p>Edmond Kolabou</p>
<h2>Technologies</h2><p>FastAPI, Vue.js 3, PostgreSQL, Redis</p>
</div>
<div v-if="tab==='apdp'" class="content card">
<h1>Politique de Confidentialité</h1><p class="date">Conforme à la loi n°001-2021/AN — APDP Burkina Faso</p>
<h2>1. Responsable</h2><p>NetSync Africa — privacy@netsync.bf</p>
<h2>2. Données collectées</h2><ul><li>Identification : nom, email, WhatsApp</li><li>Professionnelles : entreprise, secteur</li><li>Paiement : historique (données bancaires via CinetPay)</li><li>Usage : AOs consultés, favoris, alertes</li><li>Pièces : documents uploadés dans le coffre-fort</li></ul>
<h2>3. Finalités</h2><ul><li>Gestion du compte et abonnement</li><li>Alertes personnalisées email/WhatsApp</li><li>Recommandations et rapports</li><li>Amélioration du service</li></ul>
<h2>4. Base juridique</h2><p>Consentement, exécution du contrat, intérêt légitime.</p>
<h2>5. Conservation</h2><ul><li>Compte : tant qu'actif, supprimé 30j après demande</li><li>Pièces : à la demande ou 12 mois après expiration compte</li><li>Paiements : 5 ans (obligation comptable)</li><li>Logs : 12 mois</li></ul>
<h2>6. Destinataires</h2><p>Équipe NetSync, CinetPay (paiements), Resend (emails), Meta (WhatsApp). Aucune vente à des tiers.</p>
<h2>7. Sécurité</h2><ul><li>HTTPS/TLS, bcrypt, JWT + 2FA, rate limiting, backups chiffrés</li></ul>
<h2>8. Vos droits (Art. 15-22 loi n°001-2021/AN)</h2><ul><li>Accès, rectification, suppression, opposition, portabilité</li><li>Contact : privacy@netsync.bf</li></ul>
<h2>9. Cookies</h2><p>Cookies techniques uniquement (auth). Aucun tracking tiers.</p>
<h2>10. APDP</h2><p>Réclamations : APDP Burkina Faso — www.apdp.bf</p>
</div>
<p class="footer">© 2026 NetSync Gov — NetSync Africa | Ouagadougou, BF</p>
</div>
</template>
<script setup>
import { ref } from 'vue'; import { RouterLink } from 'vue-router'
const tab = ref('cgu')
</script>
<style scoped>
.legal-page{max-width:800px;margin:0 auto;padding:2rem 1.5rem}
.back{font-size:13px;color:#0082C9;text-decoration:none}
.tabs{display:flex;border-bottom:1px solid #E2E8F0;margin:1rem 0 0}
.tabs button{padding:10px 16px;font-size:13px;font-weight:500;color:#64748B;cursor:pointer;border:none;background:none;border-bottom:2px solid transparent;font-family:inherit}
.tabs button.active{color:#0082C9;border-bottom-color:#0082C9}
.content{padding:2rem;border-radius:0 0 12px 12px}
.content h1{font-size:1.5rem;font-weight:700;color:#0F1923;margin-bottom:.5rem}
.content h2{font-size:1rem;font-weight:600;color:#0F1923;margin:1.5rem 0 .5rem}
.content p,.content li{font-size:14px;color:#4A5568;line-height:1.7}
.content ul{padding-left:1.5rem}
.date{font-size:12px;color:#64748B;font-style:italic;margin-bottom:1.5rem}
.footer{text-align:center;margin-top:2rem;font-size:12px;color:#64748B}
</style>
VEOF
echo "   ✅ LegalView.vue"

# 2. AdminView.vue
echo "🔧 [2/3] Page Admin..."
cat > frontend/src/views/AdminView.vue << 'VEOF'
<template>
<div class="admin-page">
<div class="header"><div><h1 class="title">Administration</h1><p class="sub">Pipeline, abonnés, statistiques</p></div>
<button class="btn btn-primary" @click="runPipeline" :disabled="running">{{ running ? 'En cours...' : '▶ Lancer pipeline' }}</button></div>
<div v-if="loading" style="text-align:center;padding:3rem;color:#64748B;">Chargement...</div>
<template v-else>
<div class="kpis"><div class="kpi card" v-for="k in kpis" :key="k.l"><div class="kpi-l">{{k.l}}</div><div class="kpi-v">{{k.v}}</div><div class="kpi-s">{{k.s}}</div></div></div>
<div class="tabs"><button :class="{active:tab==='logs'}" @click="tab='logs'">Pipeline logs</button><button :class="{active:tab==='users'}" @click="tab='users';loadUsers()">Abonnés</button></div>
<div v-if="tab==='logs'" class="card" style="padding:1rem">
<table v-if="logs.length" class="tbl"><thead><tr><th>N°</th><th>Statut</th><th>AOs</th><th>Nouveaux</th><th>Durée</th><th>Date</th></tr></thead>
<tbody><tr v-for="l in logs" :key="l.id"><td>{{l.numero_quotidien||'—'}}</td><td><span :class="'st-'+l.statut">{{l.statut}}</span></td><td>{{l.nb_ao_extraits}}</td><td>{{l.nb_ao_nouveaux}}</td><td>{{l.duree_secondes?.toFixed(1)}}s</td><td>{{fmt(l.created_at)}}</td></tr></tbody></table>
<p v-else style="text-align:center;color:#64748B;padding:2rem">Aucun log</p></div>
<div v-if="tab==='users'" class="card" style="padding:1rem">
<table v-if="users.length" class="tbl"><thead><tr><th>Email</th><th>Nom</th><th>Plan</th><th>Actif</th><th>Inscrit</th><th>Changer</th></tr></thead>
<tbody><tr v-for="u in users" :key="u.id"><td>{{u.email}}</td><td>{{u.prenom}} {{u.nom}}</td><td><span :class="'pl-'+u.plan">{{u.plan?.toUpperCase()}}</span></td><td>{{u.actif?'✅':'❌'}}</td><td>{{fmt(u.created_at)}}</td>
<td><select :value="u.plan" @change="chgPlan(u.id,$event.target.value)"><option value="gratuit">Gratuit</option><option value="pro">Pro</option><option value="equipe">Équipe</option></select></td></tr></tbody></table>
<p v-else style="text-align:center;color:#64748B;padding:2rem">Aucun abonné</p></div>
</template></div>
</template>
<script setup>
import{ref,onMounted}from'vue';import api from'@/api'
const loading=ref(true),running=ref(false),tab=ref('logs'),kpis=ref([]),logs=ref([]),users=ref([])
function fmt(d){return d?new Date(d).toLocaleDateString('fr-FR',{day:'2-digit',month:'short',year:'numeric'}):'—'}
async function load(){try{const{data}=await api.get('/admin/stats');kpis.value=[{l:'AOs',v:data.total_ao||0,s:`${data.ao_ouverts||0} ouverts`},{l:'Abonnés',v:data.total_abonnes||0,s:`${data.abonnes_pro||0} Pro`},{l:'Pipeline',v:data.total_pipeline_runs||0,s:'Exécutions'},{l:'Alertes',v:data.total_alertes||0,s:'Envoyées'}]}catch{};try{const{data}=await api.get('/admin/pipeline/logs');logs.value=data.logs||data||[]}catch{};loading.value=false}
async function loadUsers(){try{const{data}=await api.get('/admin/abonnes');users.value=data.abonnes||data||[]}catch{}}
async function runPipeline(){running.value=true;try{await api.post('/admin/pipeline/run')}catch{};running.value=false;setTimeout(load,3000)}
async function chgPlan(id,p){try{await api.put(`/admin/abonnes/${id}/plan`,{plan:p});await loadUsers()}catch{}}
onMounted(load)
</script>
<style scoped>
.admin-page{display:flex;flex-direction:column;gap:1rem}
.header{display:flex;align-items:flex-start;justify-content:space-between}
.title{font-family:var(--font-display);font-size:1.5rem;color:var(--ink)}
.sub{font-size:13px;color:var(--muted);margin-top:4px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem}
.kpi{padding:1rem}.kpi-l{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.kpi-v{font-family:var(--font-display);font-size:1.6rem;color:var(--ink)}.kpi-s{font-size:11px;color:var(--muted);margin-top:4px}
.tabs{display:flex;border-bottom:1px solid var(--border)}.tabs button{padding:10px 16px;font-size:13px;font-weight:500;color:var(--muted);cursor:pointer;border:none;background:none;border-bottom:2px solid transparent;font-family:inherit}
.tabs button.active{color:var(--blue-500);border-bottom-color:var(--blue-500)}
.tbl{width:100%;border-collapse:collapse;font-size:12px}.tbl th{background:var(--surface);font-size:10px;font-weight:600;text-transform:uppercase;color:var(--muted);padding:8px 10px;text-align:left;border-bottom:1px solid var(--border)}
.tbl td{padding:8px 10px;border-bottom:1px solid var(--border)}.tbl tr:hover td{background:var(--surface)}
.st-succes,.st-success{color:#1D9E75;font-weight:600}.st-erreur,.st-error{color:#E24B4A;font-weight:600}
.pl-pro{background:#E6F1FB;color:#0082C9;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:600}
.pl-equipe{background:#E6F4EA;color:#1D9E75;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:600}
.pl-gratuit{color:#64748B;font-size:10px}
select{font-size:11px;border:1px solid var(--border);border-radius:4px;padding:3px 6px}
@media(max-width:900px){.kpis{grid-template-columns:1fr 1fr}}
</style>
VEOF
echo "   ✅ AdminView.vue"

# 3. Routes + Sidebar
echo "🔧 [3/3] Routes + sidebar..."
python3 << 'PY'
# Router
r=open("frontend/src/router/index.js").read()
if "Legal" not in r:
    r=r.replace("{ path: '/pricing', name: 'Pricing', component: () => import('@/views/PricingView.vue') },","{ path: '/pricing', name: 'Pricing', component: () => import('@/views/PricingView.vue') },\n  { path: '/legal', name: 'Legal', component: () => import('@/views/LegalView.vue') },")
if "Admin" not in r:
    r=r.replace("{ path: 'assistant',","{ path: 'admin', name: 'Admin', component: () => import('@/views/AdminView.vue') },\n      { path: 'assistant',")
open("frontend/src/router/index.js","w").write(r)

# Sidebar
s=open("frontend/src/components/layout/AppLayout.vue").read()
if "Admin" not in s:
    s=s.replace("const IconBot","const IconAdmin = { template: \`<svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><circle cx=\"12\" cy=\"12\" r=\"3\"/><path d=\"M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42\"/></svg>\` }\nconst IconBot")
    s=s.replace("{ to: '/assistant',    label: 'Assistant IA',    icon: IconBot },","{ to: '/assistant',    label: 'Assistant IA',    icon: IconBot },\n  { to: '/admin',        label: 'Administration', icon: IconAdmin },")
open("frontend/src/components/layout/AppLayout.vue","w").write(s)
print("   ✅ Routes /legal + /admin + sidebar")
PY

echo ""
echo "✅ Patch #9 terminé — CGU + APDP + Admin"
echo "  git add -A && git commit -m 'feat: CGU APDP admin (patch #9)' && git push origin main"
