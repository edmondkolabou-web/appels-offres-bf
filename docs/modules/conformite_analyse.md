# NetSync Gov Conformité — Analyse du besoin

## Le problème numéro 1 des soumissionnaires BF

Parmi les causes de rejet des dossiers aux marchés publics burkinabè,
la pièce administrative expirée est la plus fréquente et la plus évitable.

**Situation typique :**
- Une PME prépare un dossier pour un AO clôturant le 30 avril
- Elle rassemble tout : offre technique, financière, références
- Au moment de déposer, elle réalise que son ASF a expiré le 25 avril
- Résultat : dossier rejeté. Marché perdu.

Ce scénario se répète des dizaines de fois par mois au Burkina Faso.

---

## Les pièces concernées et leurs durées de validité

| Pièce | Sigle | Organisme délivrant | Validité |
|-------|-------|---------------------|---------|
| Attestation de Situation Fiscale | ASF | DGI via SECOP | 90 jours |
| Attestation CNSS | CNSS | CNSS | 90 jours |
| Attestation de Jouissance d'Existence | AJE | Tribunal de commerce | 1 an |
| Registre du Commerce | RCCM | CEFORE | Permanent (à renouveler si changement) |
| Identifiant Fiscal Unique | IFU | DGI | Permanent |
| Statuts de la société | — | Notaire | Permanent (à mettre à jour si changement) |
| Attestation bancaire | — | Banque | 30 jours |
| Casier judiciaire dirigeant | — | Tribunal | 3 mois |
| CV experts | — | Interne | Pas d'expiration (à mettre à jour) |
| Références marchés similaires | — | Autorités contractantes | Pas d'expiration |

---

## Ce que NetSync Gov Conformité apporte

### Pour l'entreprise
- **Tableau de bord pièces** : statut de chaque pièce en temps réel (valide, expire bientôt, expirée)
- **Calendrier de renouvellement** : vue calendrier des échéances à venir
- **Alertes automatiques** : WhatsApp + email à J-30, J-15, J-7 avant expiration
- **Instructions de renouvellement** : lien vers SECOP, adresse des organismes, documents à fournir
- **Score de conformité** : pourcentage de pièces valides à tout moment

### Pour l'équipe (Plan Équipe)
- **Partage des pièces** : toute l'équipe accède aux pièces validées
- **Historique des versions** : traçabilité des renouvellements
- **Validation par le responsable** : workflow d'approbation interne

---

## Valeur différenciante

**NetSync Gov Conformité est le premier "coffre-fort administratif"
dédié aux soumissionnaires aux marchés publics burkinabè.**

Aucun service local n'offre :
- La surveillance automatique des dates d'expiration
- Les alertes WhatsApp avant expiration
- Les instructions de renouvellement contextualisées (lien SECOP direct)
- L'intégration avec le module Candidature (vérification automatique à chaque nouveau dossier)

---

## Intégration avec les modules existants

```
Module Conformité
    ↕ (synchronisation automatique)
Module Candidature
    → Lors de la création d'un dossier, vérification automatique
      que toutes les pièces requises sont valides
    → Blocage si pièce expirée + suggestion de renouvellement
```

---

## Modèle économique

| Plan | Accès | Pièces stockées |
|------|-------|----------------|
| Gratuit | Non | — |
| Pro | Oui | Illimité |
| Équipe | Oui + partage équipe | Illimité + historique |

**Inclus dans le plan Pro existant** — argument de vente supplémentaire
sans surcoût pour l'abonné.

---

## KPIs cibles M3

| KPI | Cible |
|-----|-------|
| Pièces enregistrées / abonné Pro | > 6 |
| Alertes expiration envoyées / mois | > 200 |
| Taux renouvellement avant expiration | > 80% |
| Dossiers bloqués évités | Mesurable via feedback |
