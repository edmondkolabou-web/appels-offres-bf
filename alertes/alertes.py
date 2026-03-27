"""
Système d'alertes email — Appels Offres BF

Fonctions principales :
  traiter_alertes()          — vérifie les nouvelles offres du jour,
                               matche avec les préférences utilisateurs,
                               envoie les emails
  envoyer_email_test(email)  — envoie un email de test avec les 3 dernières offres
  generer_html(offres, nom)  — retourne le template HTML de l'email (testable
                               sans serveur SMTP)

Configuration SMTP via variables d'environnement :
  SMTP_HOST  (défaut : smtp.gmail.com)
  SMTP_PORT  (défaut : 587)
  SMTP_USER
  SMTP_PASS
"""

import os
import sys
import json
import smtplib
import re
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.database import get_connection

# ── Config SMTP ──────────────────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_NAME = "Appels Offres BF 🇧🇫"


# ── Requêtes base de données ─────────────────────────────────────────────────

def offres_du_jour() -> list[dict]:
    """Retourne toutes les offres créées aujourd'hui (date locale)."""
    today = date.today().isoformat()          # ex: "2026-03-28"
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, titre, source, url_source, type_offre,
               secteur, date_publication, date_limite, statut
        FROM   offres
        WHERE  DATE(created_at) = ?
        ORDER  BY id DESC
        """,
        (today,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def dernieres_offres(n: int = 3) -> list[dict]:
    """Retourne les N offres les plus récentes (pour l'email de test)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, titre, source, url_source, type_offre,
               secteur, date_publication, date_limite, statut
        FROM   offres
        ORDER  BY id DESC
        LIMIT  ?
        """,
        (n,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def utilisateurs_actifs_avec_alertes() -> list[dict]:
    """
    Retourne tous les utilisateurs actifs ayant au moins une alerte active.
    Pour chaque utilisateur, charge la liste de ses alertes.
    """
    conn = get_connection()
    users = conn.execute(
        """
        SELECT DISTINCT u.id, u.nom, u.prenom, u.email
        FROM   utilisateurs u
        JOIN   alertes a ON a.utilisateur_id = u.id
        WHERE  u.actif = 1 AND a.actif = 1
        """
    ).fetchall()

    result = []
    for u in users:
        alertes = conn.execute(
            """
            SELECT mots_cles, secteur, montant_min, montant_max,
                   type_offre, canal, frequence
            FROM   alertes
            WHERE  utilisateur_id = ? AND actif = 1
            """,
            (u["id"],),
        ).fetchall()
        result.append({
            "id":     u["id"],
            "nom":    u["nom"],
            "prenom": u["prenom"],
            "email":  u["email"],
            "alertes": [dict(a) for a in alertes],
        })

    conn.close()
    return result


# ── Matching offre ↔ alerte ──────────────────────────────────────────────────

def offre_correspond(offre: dict, alerte: dict) -> bool:
    """
    Retourne True si l'offre satisfait tous les critères non-vides de l'alerte.

    Critères vérifiés :
      - mots_cles  : au moins un mot-clé présent dans le titre (insensible à la casse)
      - secteur    : correspondance exacte (insensible à la casse)
      - type_offre : correspondance exacte
      - montant_min/max : (données rarement disponibles, vérifiées si présentes)
    """
    titre = (offre.get("titre") or "").lower()

    # Mots-clés (JSON array stocké en texte)
    if alerte.get("mots_cles"):
        try:
            mots = json.loads(alerte["mots_cles"])
        except (json.JSONDecodeError, TypeError):
            mots = [alerte["mots_cles"]]
        if mots and not any(m.lower() in titre for m in mots if m):
            return False

    # Secteur
    if alerte.get("secteur") and offre.get("secteur"):
        if alerte["secteur"].lower() != (offre["secteur"] or "").lower():
            return False

    # Type d'offre
    if alerte.get("type_offre") and alerte["type_offre"] != offre.get("type_offre"):
        return False

    # Montant estimé (si disponible)
    montant = offre.get("montant_estime")
    if montant is not None:
        if alerte.get("montant_min") and montant < alerte["montant_min"]:
            return False
        if alerte.get("montant_max") and montant > alerte["montant_max"]:
            return False

    return True


def filtrer_offres_pour_utilisateur(offres: list[dict], alertes: list[dict]) -> list[dict]:
    """Retourne les offres correspondant à au moins une alerte de l'utilisateur."""
    correspondantes = []
    for offre in offres:
        if any(offre_correspond(offre, a) for a in alertes):
            correspondantes.append(offre)
    return correspondantes


# ── Template HTML ─────────────────────────────────────────────────────────────

def generer_html(offres: list[dict], nom_destinataire: str = "Madame, Monsieur") -> str:
    """
    Génère le corps HTML de l'email d'alerte.
    Peut être appelé indépendamment pour tester le rendu sans SMTP.
    """
    nb = len(offres)
    today_fr = date.today().strftime("%d/%m/%Y")

    cartes_html = ""
    SOURCE_LABELS = {
        "lesaffairesbf": "lesaffairesbf.com",
        "arcop":         "arcop.bf",
    }
    SOURCE_COLORS = {
        "lesaffairesbf": "#009a44",
        "arcop":         "#ef2b2d",
    }

    for o in offres:
        source_label = SOURCE_LABELS.get(o.get("source", ""), o.get("source", ""))
        source_color = SOURCE_COLORS.get(o.get("source", ""), "#6b7280")
        date_pub   = o.get("date_publication") or "—"
        date_lim   = o.get("date_limite") or "—"
        titre      = _esc(o.get("titre") or "Sans titre")
        url        = _esc(o.get("url_source") or "#")
        statut     = (o.get("statut") or "ouvert").capitalize()

        date_lim_html = ""
        if o.get("date_limite"):
            date_lim_html = f"""
            <tr>
              <td style="padding:4px 0;color:#b45309;font-size:13px;">
                ⚠️ <strong>Clôture :</strong> {_esc(date_lim)}
              </td>
            </tr>"""

        cartes_html += f"""
        <tr>
          <td style="padding:0 0 16px 0;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:10px;
                          border:1px solid #e5e7eb;
                          border-top:4px solid {source_color};
                          border-collapse:separate;">
              <tr>
                <td style="padding:16px 20px 12px;">
                  <!-- Badge source + statut -->
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="padding:3px 10px;background:{source_color}22;
                                 color:{source_color};font-size:11px;font-weight:700;
                                 border-radius:20px;text-transform:uppercase;
                                 letter-spacing:.5px;">
                        {_esc(source_label)}
                      </td>
                      <td width="8"></td>
                      <td style="padding:3px 10px;background:#dcfce7;
                                 color:#166534;font-size:11px;font-weight:600;
                                 border-radius:20px;">
                        {_esc(statut)}
                      </td>
                    </tr>
                  </table>
                  <!-- Titre -->
                  <p style="margin:10px 0 8px;font-size:15px;font-weight:600;
                             color:#111827;line-height:1.45;">
                    {titre}
                  </p>
                  <!-- Méta -->
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="padding:4px 0;color:#6b7280;font-size:13px;">
                        📅 <strong>Publiée le :</strong> {_esc(date_pub)}
                      </td>
                    </tr>
                    {date_lim_html}
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:0 20px 16px;text-align:right;">
                  <a href="{url}"
                     style="display:inline-block;background:#ef2b2d;color:#ffffff;
                            text-decoration:none;font-size:13px;font-weight:600;
                            padding:8px 18px;border-radius:6px;">
                    Voir l'offre ↗
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Alertes Appels Offres BF</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;
             font-family:'Segoe UI',system-ui,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#f3f4f6;padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;">

          <!-- ── En-tête ───────────────────────────────────────── -->
          <tr>
            <td style="background:linear-gradient(135deg,#ef2b2d,#c0392b);
                       border-radius:12px 12px 0 0;padding:28px 32px;
                       text-align:center;">
              <p style="margin:0;font-size:2rem;line-height:1;">🇧🇫</p>
              <h1 style="margin:10px 0 4px;font-size:22px;color:#ffffff;
                         font-weight:700;letter-spacing:-.3px;">
                Appels Offres BF
              </h1>
              <p style="margin:0;font-size:13px;color:rgba(255,255,255,.85);">
                Vos nouvelles offres du {today_fr}
              </p>
            </td>
          </tr>

          <!-- ── Corps ────────────────────────────────────────── -->
          <tr>
            <td style="background:#f9fafb;padding:28px 32px;">

              <!-- Salutation -->
              <p style="margin:0 0 8px;font-size:15px;color:#111827;">
                Bonjour <strong>{_esc(nom_destinataire)}</strong>,
              </p>
              <p style="margin:0 0 24px;font-size:14px;color:#374151;line-height:1.6;">
                {nb} nouvelle{"s" if nb > 1 else ""} offre{"s correspondent" if nb > 1 else " correspond"}
                à vos critères d'alerte aujourd'hui.
                Consultez-les avant expiration des délais.
              </p>

              <!-- Cartes offres -->
              <table width="100%" cellpadding="0" cellspacing="0">
                {cartes_html}
              </table>

              <!-- CTA principal -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="margin-top:8px;">
                <tr>
                  <td align="center">
                    <a href="http://127.0.0.1:8000"
                       style="display:inline-block;background:#111827;color:#ffffff;
                              text-decoration:none;font-size:14px;font-weight:600;
                              padding:12px 28px;border-radius:8px;">
                      Voir toutes les offres sur la plateforme
                    </a>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- ── Pied de page ──────────────────────────────────── -->
          <tr>
            <td style="background:#e5e7eb;border-radius:0 0 12px 12px;
                       padding:20px 32px;text-align:center;">
              <p style="margin:0 0 4px;font-size:12px;color:#6b7280;">
                Vous recevez cet email car vous avez activé des alertes
                sur <strong>Appels Offres BF</strong>.
              </p>
              <p style="margin:0;font-size:12px;color:#9ca3af;">
                Pour modifier vos alertes, connectez-vous à votre espace.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""
    return html


def _esc(s: str) -> str:
    """Échappe les caractères HTML dangereux."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ── Envoi SMTP ────────────────────────────────────────────────────────────────

def envoyer_email(destinataire: str, sujet: str, corps_html: str) -> bool:
    """
    Envoie un email HTML via SMTP (TLS port 587).
    Retourne True si envoi réussi, False sinon.
    Nécessite SMTP_USER et SMTP_PASS dans l'environnement.
    """
    if not SMTP_USER or not SMTP_PASS:
        print("  [SMTP] Variables SMTP_USER / SMTP_PASS non configurées — envoi simulé.")
        print(f"  [SMTP] Destinataire : {destinataire}")
        print(f"  [SMTP] Sujet        : {sujet}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = sujet
    msg["From"]    = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"]      = destinataire
    msg.attach(MIMEText(corps_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, destinataire, msg.as_bytes())
        print(f"  [SMTP] ✓ Email envoyé → {destinataire}")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"  [SMTP] Erreur d'authentification — vérifiez SMTP_USER/PASS")
    except smtplib.SMTPException as e:
        print(f"  [SMTP] Erreur SMTP : {e}")
    except OSError as e:
        print(f"  [SMTP] Erreur réseau : {e}")
    return False


# ── Orchestrateur principal ───────────────────────────────────────────────────

def traiter_alertes() -> dict:
    """
    Traitement complet des alertes :
      1. Récupère les offres ajoutées aujourd'hui
      2. Charge les utilisateurs avec alertes actives
      3. Filtre les offres correspondantes par utilisateur
      4. Envoie un email récapitulatif à chaque utilisateur concerné

    Retourne un dict résumé : {traites, emails_envoyes, emails_echec}
    """
    print("\n── Traitement des alertes ──────────────────────────────────")
    offres = offres_du_jour()
    print(f"  Offres du jour      : {len(offres)}")

    if not offres:
        print("  Aucune nouvelle offre aujourd'hui. Fin.")
        return {"traites": 0, "emails_envoyes": 0, "emails_echec": 0}

    utilisateurs = utilisateurs_actifs_avec_alertes()
    print(f"  Utilisateurs actifs : {len(utilisateurs)}")

    envoyes = 0
    echecs  = 0

    for user in utilisateurs:
        offres_matchees = filtrer_offres_pour_utilisateur(offres, user["alertes"])
        if not offres_matchees:
            continue

        nb    = len(offres_matchees)
        prenom = user.get("prenom") or user["nom"]
        sujet  = f"🇧🇫 {nb} nouvelle{'s' if nb > 1 else ''} offre{'s correspondent' if nb > 1 else ' correspond'} à vos critères"
        html   = generer_html(offres_matchees, prenom)

        print(f"  → {user['email']} : {nb} offre(s) matchée(s)")
        ok = envoyer_email(user["email"], sujet, html)
        if ok:
            envoyes += 1
        else:
            echecs += 1

    print(f"  Emails envoyés : {envoyes}  |  Échecs : {echecs}")
    print("──────────────────────────────────────────────────────────\n")
    return {
        "traites":        len(utilisateurs),
        "emails_envoyes": envoyes,
        "emails_echec":   echecs,
    }


def envoyer_email_test(email: str) -> dict:
    """
    Envoie un email de test à l'adresse indiquée
    avec les 3 dernières offres en base.
    Utilisé par la route GET /alertes/test
    """
    offres = dernieres_offres(3)
    if not offres:
        return {"statut": "erreur", "detail": "Aucune offre en base"}

    nb    = len(offres)
    sujet = f"🇧🇫 [TEST] {nb} offres — Appels Offres BF"
    html  = generer_html(offres, "Testeur")
    ok    = envoyer_email(email, sujet, html)

    return {
        "statut":       "envoyé" if ok else "simulé (SMTP non configuré)",
        "destinataire": email,
        "nb_offres":    nb,
        "sujet":        sujet,
    }


# ── Test direct ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    print("\n" + "=" * 58)
    print("  TEST — Système d'alertes Appels Offres BF")
    print("=" * 58)

    # 1. Aperçu des offres du jour
    offres_j = offres_du_jour()
    print(f"\n[1/4] Offres du jour : {len(offres_j)}")
    for o in offres_j[:3]:
        print(f"  • {o['titre'][:60]}")

    # 2. Utilisateurs avec alertes
    users = utilisateurs_actifs_avec_alertes()
    print(f"\n[2/4] Utilisateurs avec alertes actives : {len(users)}")
    for u in users:
        print(f"  • {u['nom']} ({u['email']}) — {len(u['alertes'])} alerte(s)")

    # 3. Génération du template HTML (sans envoi SMTP)
    print("\n[3/4] Génération du template HTML ...")
    offres_demo = dernieres_offres(3)
    html_demo = generer_html(offres_demo, "Koné Mamadou")

    # Sauvegarder le template pour inspection
    out_path = os.path.join(os.path.dirname(__file__), "email_test.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_demo)
    print(f"  Template généré → {out_path}  ({len(html_demo)} octets)")
    print(f"  Offres incluses : {len(offres_demo)}")
    for o in offres_demo:
        print(f"    • {o['titre'][:60]}")

    # 4. Simulation d'envoi
    print("\n[4/4] Simulation d'envoi (SMTP non configuré) ...")
    res = envoyer_email_test("test@example.com")
    print(f"  Statut   : {res['statut']}")
    print(f"  Sujet    : {res['sujet']}")
    print(f"  Nb offres: {res['nb_offres']}")

    # 5. Traitement complet
    print("\n[5/4] Traitement alertes (tous utilisateurs) ...")
    bilan = traiter_alertes()
    print(f"  Bilan : {bilan}")

    print("=" * 58 + "\n")
