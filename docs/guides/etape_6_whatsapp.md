# Étape 6 — Soumettre les templates WhatsApp Meta

> Cette étape peut être faite en parallèle des étapes 3-5.
> L'approbation Meta prend 48 à 72h.
> Le service fonctionne avec email uniquement pendant ce délai.

---

## Comment soumettre un template

1. Aller sur https://business.facebook.com
2. Menu gauche → **WhatsApp Manager**
3. Sélectionner ton compte → **Message Templates**
4. Cliquer "Create Template"
5. Remplir les champs selon les specs ci-dessous
6. Cliquer "Submit"

Répéter pour chacun des 3 templates.

---

## Template 1 — netsync_nouvel_ao

**Nom du template** : `netsync_nouvel_ao`
**Catégorie** : UTILITY (IMPORTANT — pas MARKETING)
**Langue** : Français

### Header (type TEXT)
```
{{1}} — Nouvel Appel d'Offres
```
Variable {{1}} = Emoji + secteur (ex : "💻 INFORMATIQUE")

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

### Footer
```
Gérer mes alertes : gov.netsync.bf/alertes
```

### Bouton (Call to Action — URL)
- Texte : `Voir l'AO →`
- URL : `https://gov.netsync.bf/aos/{{1}}`

### Variables (à remplir dans l'exemple de soumission)
| Variable | Exemple |
|----------|---------|
| {{1}} header | 💻 INFORMATIQUE |
| {{2}} | Adama |
| {{3}} | Acquisition matériel informatique — MAERAH |
| {{4}} | MAERAH / Direction des Marchés |
| {{5}} | Informatique |
| {{6}} | 30/04/2026 |
| {{7}} | https://gov.netsync.bf/aos/abc123 |

---

## Template 2 — netsync_rappel_cloture

**Nom du template** : `netsync_rappel_cloture`
**Catégorie** : UTILITY
**Langue** : Français

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

### Footer
```
Désactiver ce rappel : gov.netsync.bf/alertes
```

### Variables exemple
| Variable | Exemple |
|----------|---------|
| {{1}} | 3 |
| {{2}} | Adama |
| {{3}} | Acquisition matériel informatique — MAERAH |
| {{4}} | 30/04/2026 |
| {{5}} | https://gov.netsync.bf/aos/abc123 |

---

## Template 3 — netsync_bienvenue

**Nom du template** : `netsync_bienvenue`
**Catégorie** : UTILITY
**Langue** : Français

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

### Variables exemple
| Variable | Exemple |
|----------|---------|
| {{1}} | Adama |
| {{2}} | 07h00 |

---

## Points d'attention pour l'approbation Meta

### Ce qui aide à l'approbation
- Catégorie **UTILITY** (transactionnel) → taux d'approbation > 90%
- Exemples de variables réalistes et concrets
- Footer avec lien de désabonnement
- Langue cohérente (tout en français)

### Ce qui fait rejeter
- Mots marketing : "promotion", "offre spéciale", "gratuit", "cliquez ici"
- Variables trop vagues ou exemples peu réalistes
- Catégorie MARKETING au lieu de UTILITY

### Si un template est rejeté
- Lire le motif de rejet dans le Business Manager
- Corriger uniquement la partie indiquée
- Resoumettre (pas de délai de carence)

---

## Tester l'envoi après approbation

```bash
# Sur le VPS — tester l'envoi du template netsync_bienvenue
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec api python3 -c "
from alertes_netsync_gov.whatsapp import AOAlertWhatsApp
from unittest.mock import MagicMock

# Créer un abonné de test
abonne = MagicMock()
abonne.prenom = 'Adama'
abonne.whatsapp = '+226XXXXXXXX'  # Ton vrai numéro WhatsApp

wa = AOAlertWhatsApp()
result = wa.send_bienvenue(abonne)
print('Résultat:', result)
"
```

✅ Vert si message reçu sur WhatsApp

---

## Après l'approbation des 3 templates

Les alertes WhatsApp sont maintenant opérationnelles.
Le pipeline enverra automatiquement les alertes chaque matin à 07h00.

**Passer au lancement bêta.**
