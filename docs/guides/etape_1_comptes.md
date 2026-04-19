# Étape 1 — Créer les 4 comptes et récupérer les clés API

> Commencer par cette étape AVANT tout le reste.
> CinetPay peut prendre 24–72h pour valider le KYC — le lancer en premier.

---

## Compte 1 — Resend (emails d'alerte)
**Coût : Gratuit jusqu'à 3 000 emails/mois**
**Durée : ~30 minutes**

### Étapes
1. Aller sur https://resend.com/signup
2. Créer un compte avec ton email
3. Dans le menu gauche → **Domains** → "Add Domain"
4. Entrer `gov.netsync.bf`
5. Resend te donne 3 enregistrements DNS à ajouter :
   - Enregistrement SPF (type TXT)
   - Enregistrement DKIM (type TXT)
   - Enregistrement DMARC (type TXT)
6. Ajouter ces 3 enregistrements chez ton registrar DNS
7. Revenir sur Resend → cliquer "Verify" → attendre 5 à 30 minutes
8. Menu gauche → **API Keys** → "Create API Key"
9. Donner un nom : `netsync-gov-prod`
10. Copier la clé immédiatement (elle ne s'affiche qu'une fois)

### Variables à noter
```
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=alertes@gov.netsync.bf
RESEND_REPLY_TO=support@netsync.bf
```

---

## Compte 2 — CinetPay (paiement Orange Money / Moov Money)
**Coût : Commission 1.5% à 3% par transaction**
**Durée : 30 min de création + 24 à 72h de validation KYC**

> LANCER EN PREMIER — le KYC est le point le plus long.

### Étapes
1. Aller sur https://cinetpay.com
2. Cliquer "Créer un compte" → choisir **Compte Marchand**
3. Remplir le formulaire avec les informations de ta structure
4. Compléter le **KYC** (vérification d'identité) :
   - Pièce d'identité (CNI, passeport)
   - Justificatif d'activité (si SARL : registre de commerce)
   - Attendre la validation par email (24 à 72h)
5. Une fois validé → Dashboard → **Mes applications** → "Créer une application"
   - Nom : `NetSync Gov`
   - URL de retour succès : `https://gov.netsync.bf/paiement/succes`
   - URL de retour annulation : `https://gov.netsync.bf/paiement/annulation`
6. Dans les paramètres de l'application → récupérer :
   - **Site ID**
   - **API Key**
   - **Secret Key**
7. Dans Paramètres → **Webhook** → entrer :
   `https://api.gov.netsync.bf/api/v1/paiements/webhook`

### Variables à noter
```
CINETPAY_SITE_ID=xxxxxxxxx
CINETPAY_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxx
CINETPAY_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxx
CINETPAY_NOTIFY_URL=https://api.gov.netsync.bf/api/v1/paiements/webhook
CINETPAY_RETURN_URL=https://gov.netsync.bf/paiement/succes
```

### Test sandbox
CinetPay fournit un environnement de test. Utiliser ces numéros de test :
- Orange Money BF test : `07000000`
- Moov Money BF test : `05000000`

---

## Compte 3 — Meta WhatsApp Business (alertes WhatsApp)
**Coût : ~0.013$ par message (~8 FCFA)**
**Durée : 1 à 2h de création + 48 à 72h d'approbation des templates**

### Étapes

#### 3a — Créer le compte Business Manager
1. Aller sur https://business.facebook.com
2. Si tu n'as pas de compte Facebook : en créer un d'abord
3. Cliquer "Créer un compte" → remplir le nom de l'entreprise (NetSync Gov ou NetSync Labs)
4. Vérifier le compte Business par email

#### 3b — Ajouter WhatsApp Business
1. Dans le Business Manager → menu gauche → **WhatsApp Manager**
2. Cliquer "Ajouter un numéro de téléphone"
3. Choisir un numéro dédié à NetSync Gov (pas ton numéro personnel)
   - Un numéro Orange BF ou Moov BF fonctionne
   - Ce numéro NE peut plus recevoir l'appli WhatsApp normale
4. Vérifier par SMS ou appel vocal
5. Le numéro devient le sender officiel de tes alertes

#### 3c — Créer l'application développeur
1. Aller sur https://developers.facebook.com
2. "Mes applications" → "Créer une application"
3. Type : **Business**
4. Nom : `NetSync Gov`
5. Dans l'application → "Ajouter un produit" → **WhatsApp**
6. Associer ton compte WABA (WhatsApp Business Account)
7. Dans WhatsApp → Configuration → récupérer :
   - **Token d'accès temporaire** (valable 24h, à remplacer par un token permanent)
   - **Phone Number ID**
   - **WhatsApp Business Account ID (WABA ID)**

#### 3d — Générer un token permanent
1. Dans le Business Manager → **Utilisateurs système** → "Ajouter"
2. Créer un utilisateur système avec le rôle Admin
3. Lui donner accès à l'application WhatsApp
4. Générer un token → durée : "Jamais" → cocher `whatsapp_business_messaging`
5. Copier le token (ne s'affiche qu'une fois)

#### 3e — Soumettre les templates (voir étape 6)
Les 3 templates à soumettre sont documentés dans le fichier `etape_6_whatsapp.md`

### Variables à noter
```
WHATSAPP_API_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_PHONE_ID=1234567890123
WHATSAPP_WABA_ID=9876543210987
```

---

## Compte 4 — Anthropic Claude API (fallback parsing PDF)
**Coût : ~6 000 à 10 000 FCFA/mois maximum**
**Durée : 15 minutes**
**Optionnel au lancement** — le pipeline regex fonctionne seul pour les PDFs bien formés

### Étapes
1. Aller sur https://console.anthropic.com
2. Cliquer "Sign up" → créer un compte avec ton email
3. Vérifier l'email
4. Menu gauche → **API Keys** → "Create Key"
5. Nom : `netsync-gov-prod`
6. Copier la clé immédiatement
7. Menu gauche → **Billing** → ajouter une carte bancaire
   - Mettre une limite mensuelle de 15$ pour éviter les mauvaises surprises

### Variables à noter
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Récapitulatif — Toutes les variables récupérées

Une fois les 4 comptes créés, tu dois avoir ces 12 variables :

```
# Resend
RESEND_API_KEY=
RESEND_FROM_EMAIL=alertes@gov.netsync.bf

# CinetPay
CINETPAY_SITE_ID=
CINETPAY_API_KEY=
CINETPAY_SECRET_KEY=

# WhatsApp Meta
WHATSAPP_API_TOKEN=
WHATSAPP_PHONE_ID=
WHATSAPP_WABA_ID=

# Anthropic
ANTHROPIC_API_KEY=
```

Quand toutes ces lignes sont remplies → passer à l'étape 2.
