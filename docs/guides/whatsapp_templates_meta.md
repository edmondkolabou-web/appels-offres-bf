# NetSync Gov — Templates WhatsApp Business (Meta)

## Procédure de soumission

1. Accéder au **Meta Business Manager** → WhatsApp → Message Templates
2. Cliquer **Create Template**
3. Soumettre chaque template ci-dessous
4. Attendre l'approbation Meta (généralement 24–72h)
5. Configurer `TEMPLATE_NOUVEL_AO`, `TEMPLATE_RAPPEL_J3`, `TEMPLATE_BIENVENUE` dans le code

---

## Template 1 : `netsync_nouvel_ao`

**Catégorie** : UTILITY  
**Langue** : Français (fr)  
**Nom** : `netsync_nouvel_ao`

### Header (TEXT)
```
{{1}} — Nouvel Appel d'Offres
```
*Variable {{1}} = Emoji + secteur, ex : "💻 INFORMATIQUE"*

### Body
```
Bonjour {{2}},

Un nouvel appel d'offres correspond à tes critères de surveillance.

📋 *{{3}}*

🏛️ Autorité : {{4}}
📁 Secteur : {{5}}
📅 Clôture : {{6}}

🔗 Voir le détail : {{7}}

_NetSync Gov — Appels d'offres Burkina Faso_
```

**Variables :**
| N° | Contenu | Exemple |
|----|---------|---------|
| {{2}} | Prénom de l'abonné | Adama |
| {{3}} | Titre de l'AO (max 100 chars) | Acquisition matériel informatique — MAERAH |
| {{4}} | Autorité contractante | MAERAH / Direction des Marchés |
| {{5}} | Secteur | Informatique |
| {{6}} | Date de clôture | 30/04/2026 |
| {{7}} | URL de détail | https://gov.netsync.bf/aos/xxx |

### Footer
```
Gérer mes alertes : gov.netsync.bf/alertes
```

### Boutons (Call to Action)
- **URL dynamique** : "Voir l'AO →" → `https://gov.netsync.bf/aos/{{1}}`

---

## Template 2 : `netsync_rappel_cloture`

**Catégorie** : UTILITY  
**Langue** : Français (fr)  
**Nom** : `netsync_rappel_cloture`

### Body
```
⏰ *Rappel NetSync Gov* — Clôture dans {{1}} jour(s)

Bonjour {{2}},

L'appel d'offres suivant clôture bientôt :

*{{3}}*
📅 Date limite : *{{4}}*

Ne rate pas la date limite !

🔗 {{5}}

_NetSync Gov_
```

**Variables :**
| N° | Contenu | Exemple |
|----|---------|---------|
| {{1}} | Nombre de jours restants | 3 |
| {{2}} | Prénom | Adama |
| {{3}} | Titre AO | Acquisition matériel informatique |
| {{4}} | Date de clôture formatée | 30/04/2026 |
| {{5}} | URL de détail | https://gov.netsync.bf/aos/xxx |

### Footer
```
Désactiver ce rappel : gov.netsync.bf/alertes
```

---

## Template 3 : `netsync_bienvenue`

**Catégorie** : UTILITY  
**Langue** : Français (fr)  
**Nom** : `netsync_bienvenue`

### Body
```
🎉 Bienvenue sur *NetSync Gov*, {{1}} !

Ton compte est activé. Tu recevras tes premières alertes AO demain matin à {{2}}.

✅ Alertes email + WhatsApp configurées
✅ Quotidien DGCMEF indexé chaque matin
✅ Sources : DGCMEF, UNDP, Banque Mondiale

🔗 Accéder à ton tableau de bord : gov.netsync.bf/dashboard

_NetSync Gov — Ne rate plus aucun appel d'offres au Burkina Faso_
```

**Variables :**
| N° | Contenu | Exemple |
|----|---------|---------|
| {{1}} | Prénom | Adama |
| {{2}} | Heure d'envoi | 07h00 |

---

## Checklist soumission Meta

- [ ] Compte Meta Business Manager vérifié
- [ ] Numéro WhatsApp Business enregistré et approuvé
- [ ] Template `netsync_nouvel_ao` soumis et approuvé
- [ ] Template `netsync_rappel_cloture` soumis et approuvé
- [ ] Template `netsync_bienvenue` soumis et approuvé
- [ ] Variables d'env configurées : `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_WABA_ID`
- [ ] Test d'envoi manuel réussi sur un numéro de test

## Points d'attention Meta

- Les templates **UTILITY** (transactionnel) ont un taux d'approbation plus élevé que MARKETING
- Éviter les mots comme "promotion", "offre gratuite", "cliquez ici" — risque de rejet
- Le bouton URL dynamique doit pointer vers un domaine vérifié dans le Business Manager
- Prévoir 48–72h pour l'approbation Meta avant le lancement
