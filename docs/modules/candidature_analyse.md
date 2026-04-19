# NetSync Gov Candidature — Analyse du besoin

## Le problème précis

Un abonné NetSync Gov reçoit une alerte à 07h00 :
"Acquisition matériel informatique — MAERAH · Clôture 30 avril 2026"

Il clique, voit la fiche. Il est intéressé. Maintenant il doit :

1. Télécharger le DAO (Dossier d'Appel d'Offres) — souvent 20 à 80 pages
2. Lire et comprendre les conditions de participation
3. Rassembler les pièces administratives obligatoires :
   - ASF (Attestation de Situation Fiscale) — via SECOP
   - CNSS (Attestation de situation cotisante)
   - AJE (Attestation de Jouissance d'Existence)
   - IFU (Identifiant Fiscal Unique)
   - Statuts de la société
   - Références de marchés similaires
   - Offre technique (rédigée de zéro)
   - Offre financière (tableaux de prix)
4. Vérifier que chaque pièce est valide (dates d'expiration)
5. Assembler le dossier physique ou électronique
6. Déposer avant la date limite

**Aujourd'hui, ce processus prend 3 à 10 jours de travail
et se fait 100% manuellement, souvent sur papier.**

---

## Ce qui se passe en réalité

| Douleur | Fréquence | Impact |
|---------|-----------|--------|
| Pièce expirée découverte au dernier moment | Très fréquent | Dossier rejeté |
| DAO trop long à lire, conditions mal comprises | Fréquent | Dossier non conforme |
| Oubli d'une pièce obligatoire | Fréquent | Dossier rejeté |
| Offre technique rédigée trop vite | Fréquent | Offre peu compétitive |
| Plusieurs AOs en même temps, perte de suivi | Fréquent | Chaos, retards |
| Délai trop court (2-5 jours) | Fréquent | Abandon de candidature |

---

## La cible

### Cible primaire
**PME burkinabè de 5 à 50 salariés** qui soumissionnent régulièrement
aux marchés publics (BTP, IT, santé, agriculture, conseil).

Elles n'ont pas de département juridique ni de spécialiste marchés publics.
Elles soumissionnent 3 à 15 fois par an.

### Cible secondaire
**Consultants indépendants et bureaux d'études** qui répondent aux
AMIs et RFPs — beaucoup de documents à produire, délais courts.

### Cible tertiaire (Plan Équipe)
**Équipes de 3 à 10 personnes** où plusieurs collaborateurs participent
à la préparation du dossier et ont besoin de coordination.

---

## La valeur créée

| Avant NetSync Gov Candidature | Après |
|-------------------------------|-------|
| Lire le DAO manuellement (2h) | Checklist auto générée en 30 secondes |
| Vérifier les pièces une par une | Dashboard pièces avec dates d'expiration |
| Pas de suivi — todo list papier | Kanban candidatures par statut |
| Rédiger l'offre de zéro | Modèles IA adaptés au secteur |
| Délai oublié ou mal suivi | Rappel J-7, J-3, J-1 automatique |
| Équipe non coordonnée | Tâches assignées par collaborateur |

---

## Périmètre du MVP (ce qu'on construit maintenant)

### Inclus
1. **Suivi de candidature** — Kanban AO avec statuts
2. **Checklist pièces auto** — générée par type de procédure
3. **Gestionnaire de pièces** — upload + dates d'expiration + alertes
4. **Générateur d'offre technique IA** — Claude API
5. **Rappels automatiques** — J-7, J-3, J-1 avant clôture
6. **Vue équipe** — assigner des tâches par collaborateur (Plan Équipe)

### Hors périmètre MVP
- Soumission électronique directe via SECOP (API non publique)
- Signature électronique intégrée
- Analyse concurrentielle automatique

---

## Intégration avec NetSync Gov existant

NetSync Gov Candidature s'intègre naturellement :

```
Page détail AO (existante)
    ↓ bouton "Démarrer ma candidature"
    ↓
Module Candidature (nouveau)
    → Checklist pièces auto
    → Gestionnaire documents
    → Offre technique IA
    → Rappels automatiques
    → Vue équipe
```

La table `candidatures` est déjà prévue dans la roadmap vague 2.
Le bouton "Marquer comme candidat" existe déjà dans la maquette
de la page détail AO.

---

## Modèle économique

| Plan | Accès candidature | Détail |
|------|-----------------|--------|
| Gratuit | Non | — |
| Pro | Oui — 5 candidatures simultanées | Génération IA incluse |
| Équipe | Oui — illimité + vue équipe | Tâches assignées |

**Argument de vente** : un dossier raté = un marché perdu.
Un marché moyen BTP = 50 à 500 millions FCFA.
L'abonnement Pro (15 000 FCFA/mois) est négligeable face à cet enjeu.

---

## KPIs de succès du module

| KPI | Cible M3 |
|-----|---------|
| Candidatures créées / abonné Pro | > 2/mois |
| Taux de complétion dossier | > 70% |
| Alertes pièces expirées envoyées | > 50/mois |
| Offres IA générées | > 30/mois |
| NPS module | > 55 |
