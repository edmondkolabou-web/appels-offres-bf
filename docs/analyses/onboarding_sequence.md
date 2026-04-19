# NetSync Gov — Séquence d'onboarding email (J0 → J30)

## J0 — Inscription
**Déclencheur** : inscription confirmée  
**Objet** : Bienvenue — ton premier AO arrive demain à 07h00  
**Contenu** :
- Confirmation compte activé
- Ce qui se passe à 07h00 demain matin
- Lien pour configurer les secteurs dès maintenant
- Numéro WhatsApp à ajouter aux contacts (pour éviter les spams)

---

## J1 — Première alerte reçue
**Déclencheur** : envoi de la première alerte (pipeline du matin)  
**Objet** : Tu viens de recevoir ton premier AO 🔔  
**Contenu** :
- Résumé du premier AO envoyé
- Lien vers le détail sur la plateforme
- "As-tu vu l'AO sur WhatsApp ?"
- CTA : configurer d'autres secteurs

---

## J3 — Activation (si pas encore Pro)
**Déclencheur** : 3 jours après inscription, plan = gratuit  
**Objet** : 3 AOs supplémentaires t'attendaient ce matin  
**Contenu** :
- Rappel de la limite gratuite (3 AO/jour)
- Nombre d'AOs publiés dans le secteur de l'abonné depuis l'inscription
- CTA : passer Pro pour accès illimité
- Argument : "tu as manqué X AOs cette semaine"

---

## J7 — Feedback bêta (si bêta testeur)
**Déclencheur** : 7 jours après inscription  
**Objet** : 2 questions rapides sur NetSync Gov  
**Contenu** :
- 2 questions seulement :
  1. "L'alerte WhatsApp arrive-t-elle bien chaque matin ?"
  2. "Qu'est-ce qui te ferait passer au plan Pro ?"
- Lien Typeform ou réponse directe à l'email

---

## J14 — Rappel conversion (plan gratuit)
**Déclencheur** : 14 jours, plan = gratuit  
**Objet** : 14 jours d'AOs — voici ce que tu as reçu  
**Contenu** :
- Statistiques personnalisées : X alertes envoyées, Y secteurs couverts
- Témoignage d'un bêta testeur Pro
- Offre limitée : premier mois Pro à 10 000 FCFA (réduction lancement)
- CTA paiement Orange Money / Moov

---

## J30 — Bilan bêta (si bêta testeur)
**Déclencheur** : 30 jours après inscription bêta  
**Objet** : Ton mois de bêta se termine — on continue ?  
**Contenu** :
- Résumé des 30 jours : X AOs reçus, Y rappels envoyés
- "Qu'as-tu décroché grâce à NetSync Gov ?"
- Offre de conversion : passer Pro à tarif préférentiel

---

## Séquence rappel clôture (Celery automatique)
**Déclencheur** : AO clôturant dans 3 jours, abonné Pro actif  
**Canal** : WhatsApp + email  
**Timing** : 07h00 (avec le pipeline quotidien)
