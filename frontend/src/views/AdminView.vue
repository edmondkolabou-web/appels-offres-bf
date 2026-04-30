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
