# Étape 2 — Commander le VPS et configurer le DNS

> Prérequis : avoir un domaine gov.netsync.bf (ou netsync.bf avec sous-domaine)
> Cette étape peut se faire en parallèle de l'attente du KYC CinetPay.

---

## 2a — Commander le VPS sur Hostinger

### Plan recommandé
**KVM 2** — 2 vCPU / 8 GB RAM / 100 GB SSD NVMe / ~45$/mois

### Étapes
1. Aller sur https://hostinger.com/vps-hosting
2. Sélectionner **KVM 2**
3. Localisation serveur : choisir **Europe** (Amsterdam ou Paris) — meilleure latence depuis le BF
4. Système d'exploitation : **Ubuntu 22.04 LTS** (important — pas Ubuntu 24)
5. Payer (carte bancaire ou PayPal)
6. Recevoir l'email avec :
   - **Adresse IP du VPS** (ex : 185.XXX.XXX.XXX)
   - **Mot de passe root temporaire**
7. Se connecter une première fois pour changer le mot de passe :
   ```bash
   ssh root@185.XXX.XXX.XXX
   # Entrer le mot de passe reçu par email
   passwd  # Changer le mot de passe root
   ```

---

## 2b — Configurer l'accès SSH par clé (sécurité)

> Obligatoire. L'accès par mot de passe sera désactivé après.

### Sur ton ordinateur local (pas sur le VPS)
```bash
# Générer une paire de clés SSH si tu n'en as pas
ssh-keygen -t ed25519 -C "netsync-gov-deploy"
# Appuyer sur Entrée 3 fois (accepter les défauts, pas de passphrase)

# Afficher la clé publique à copier
cat ~/.ssh/id_ed25519.pub
# Copier tout le contenu affiché
```

### Sur le VPS
```bash
# Se connecter au VPS
ssh root@185.XXX.XXX.XXX

# Créer le dossier SSH et ajouter la clé publique
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
# Coller la clé publique copiée → Ctrl+X → Y → Entrée

# Définir les bonnes permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# Désactiver l'accès par mot de passe (IMPORTANT)
nano /etc/ssh/sshd_config
# Trouver la ligne : PasswordAuthentication yes
# La changer en : PasswordAuthentication no
# Sauvegarder → Ctrl+X → Y → Entrée

systemctl restart sshd
```

### Tester (depuis ton ordinateur)
```bash
# Ouvrir un NOUVEAU terminal (ne pas fermer l'ancien tant que pas testé)
ssh root@185.XXX.XXX.XXX
# Si ça marche sans mot de passe → parfait, fermer l'ancien terminal
```

---

## 2c — Configurer le DNS

### Enregistrements DNS à créer
Dans le panneau de gestion de ton registrar (là où tu as acheté le domaine netsync.bf) :

| Type | Nom | Valeur | TTL |
|------|-----|--------|-----|
| A | gov | 185.XXX.XXX.XXX (IP de ton VPS) | 300 |
| A | api.gov | 185.XXX.XXX.XXX (même IP) | 300 |

Si tu gères netsync.bf chez un registrar burkinabè, l'interface est différente mais les champs sont les mêmes.

### Vérifier la propagation DNS
```bash
# Depuis ton ordinateur (attendre 5 à 30 minutes après avoir créé les enregistrements)
dig gov.netsync.bf
# Doit afficher l'IP de ton VPS dans la section ANSWER

dig api.gov.netsync.bf
# Doit afficher la même IP

# Alternative en ligne : https://dnschecker.org
# Entrer gov.netsync.bf → vérifier que l'IP apparaît partout
```

---

## 2d — Vérifications finales étape 2

```bash
# Depuis ton ordinateur
ping gov.netsync.bf
# Doit répondre avec l'IP de ton VPS

ssh root@185.XXX.XXX.XXX
# Connexion sans mot de passe → OK
```

**Si les deux commandes fonctionnent → passer à l'étape 3.**
