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
