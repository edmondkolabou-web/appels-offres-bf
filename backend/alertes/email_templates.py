"""
NetSync Gov — Templates HTML emails (Resend)
Trois templates : alerte nouvel AO, rappel J-3, bienvenue.
"""
from datetime import date
from typing import Optional


def _base_layout(content: str, preview_text: str = "") -> str:
    """Layout HTML email partagé — compatible Gmail, Outlook, mobile."""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="x-apple-disable-message-reformatting">
<!--[if !mso]><!-->
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<!--<![endif]-->
<title>NetSync Gov</title>
<style>
  body,#root{{margin:0;padding:0;background:#F7F9FB;font-family:'Segoe UI',Arial,Helvetica,sans-serif;}}
  a{{color:#0082C9;text-decoration:none;}}
  a:hover{{text-decoration:underline;}}
  img{{border:0;display:block;}}
  .email-wrap{{max-width:580px;margin:0 auto;padding:24px 16px;}}
  .card{{background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);}}
  .header{{background:#0F1923;padding:20px 24px;display:flex;align-items:center;}}
  .logo-icon{{display:inline-block;background:#0082C9;width:36px;height:36px;border-radius:8px;text-align:center;line-height:36px;font-size:18px;color:white;font-weight:bold;vertical-align:middle;margin-right:10px;}}
  .logo-name{{color:white;font-size:17px;font-weight:600;vertical-align:middle;}}
  .body{{padding:28px 24px;}}
  .tag{{display:inline-block;background:#E6F1FB;color:#006AA3;font-size:11px;font-weight:700;padding:3px 9px;border-radius:4px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px;}}
  .tag-urgent{{background:#FCEBEB;color:#A32D2D;}}
  h1{{margin:0 0 8px;font-size:18px;color:#0F1923;line-height:1.4;font-weight:600;}}
  .ref{{font-family:monospace;font-size:11px;color:#64748B;margin-bottom:20px;}}
  .meta-table{{width:100%;border-collapse:collapse;margin-bottom:20px;}}
  .meta-table td{{padding:10px 0;font-size:13px;border-bottom:1px solid #E2E8F0;vertical-align:top;}}
  .meta-table td:first-child{{color:#64748B;width:40%;padding-right:12px;}}
  .meta-table td:last-child{{color:#0F1923;font-weight:500;}}
  .meta-table td.urgent-val{{color:#A32D2D;font-weight:600;}}
  .cta-btn{{display:block;background:#0082C9;color:#ffffff !important;text-align:center;padding:13px 28px;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none !important;margin:20px 0;}}
  .footer{{background:#F7F9FB;padding:16px 24px;font-size:11px;color:#94A3B8;text-align:center;line-height:1.6;border-top:1px solid #E2E8F0;}}
  .footer a{{color:#94A3B8;}}
  .urgent-banner{{background:#FCEBEB;border-left:3px solid #E24B4A;padding:10px 14px;border-radius:0 6px 6px 0;margin-bottom:16px;font-size:13px;color:#A32D2D;font-weight:500;}}
</style>
</head>
<body>
{"<div style='display:none;max-height:0;overflow:hidden;'>" + preview_text + "</div>" if preview_text else ""}
<div class="email-wrap">
  <div class="card">
    <div class="header">
      <span class="logo-icon">G</span>
      <span class="logo-name">NetSync Gov</span>
      <span style="color:rgba(255,255,255,.35);font-size:11px;margin-left:8px;">Appels d'offres BF</span>
    </div>
    <div class="body">
      {content}
    </div>
    <div class="footer">
      <p>
        Tu reçois cet email car tu as configuré une alerte sur
        <a href="https://gov.netsync.bf">gov.netsync.bf</a>.<br>
        <a href="https://gov.netsync.bf/alertes">Gérer mes alertes</a> &nbsp;·&nbsp;
        <a href="https://gov.netsync.bf/desabonner">Se désabonner</a>
      </p>
      <p style="margin-top:8px;">NetSync Gov · Ouagadougou, Burkina Faso</p>
    </div>
  </div>
</div>
</body>
</html>"""


def render_nouvel_ao(prenom: str, ao_titre: str, ao_reference: str,
                     autorite: str, type_procedure: str, secteur: str,
                     date_publication: str, date_cloture: Optional[str],
                     montant: Optional[str], source: str,
                     ao_url: str, est_urgent: bool = False,
                     jours_restants: Optional[int] = None) -> tuple[str, str]:
    """
    Template email : Nouvel appel d'offres détecté.
    Returns: (subject, html_body)
    """
    urgent_badge = ""
    cloture_class = ""
    if est_urgent and jours_restants is not None:
        urgent_badge = f'<div class="urgent-banner">⚡ Clôture dans <strong>{jours_restants} jour(s)</strong> — agis vite !</div>'
        cloture_class = "urgent-val"

    montant_row = f"""<tr><td>Montant estimé</td><td>{montant}</td></tr>""" if montant else ""

    content = f"""
    <p style="font-size:13px;color:#64748B;margin:0 0 4px;">Bonjour {prenom},</p>
    <p style="font-size:13px;color:#64748B;margin:0 0 16px;">Un nouvel AO correspond à tes critères de surveillance.</p>
    {urgent_badge}
    <div class="tag">🔔 {secteur.upper()}</div>
    <h1>{ao_titre}</h1>
    <p class="ref">Réf. {ao_reference}</p>
    <table class="meta-table">
      <tr><td>Autorité contractante</td><td>{autorite}</td></tr>
      <tr><td>Type de procédure</td><td>{type_procedure.upper()}</td></tr>
      <tr><td>Date de publication</td><td>{date_publication}</td></tr>
      <tr>
        <td>Date de clôture</td>
        <td class="{cloture_class}">{date_cloture or "Non précisée"}</td>
      </tr>
      {montant_row}
      <tr><td>Source</td><td>{source.upper()}</td></tr>
    </table>
    <a href="{ao_url}" class="cta-btn">Voir le détail de cet AO →</a>
    <p style="font-size:12px;color:#64748B;margin:0;">
      Tu peux aussi télécharger le PDF source directement depuis la fiche.
    </p>
    """

    urgency_prefix = f"⚡ J-{jours_restants} · " if est_urgent else ""
    subject = f"[NetSync Gov] {urgency_prefix}Nouveau AO — {secteur.upper()} · {ao_titre[:55]}"
    return subject, _base_layout(content, preview_text=f"Nouvel AO détecté : {ao_titre[:80]}")


def render_rappel_j3(prenom: str, ao_titre: str, ao_reference: str,
                     autorite: str, date_cloture: str, jours_restants: int,
                     ao_url: str) -> tuple[str, str]:
    """
    Template email : Rappel clôture dans N jours.
    Returns: (subject, html_body)
    """
    content = f"""
    <p style="font-size:13px;color:#64748B;margin:0 0 16px;">Bonjour {prenom},</p>
    <div class="urgent-banner">
      ⏰ Rappel : cet AO clôture dans <strong>{jours_restants} jour(s)</strong>.
      Ne rate pas la date limite !
    </div>
    <div class="tag tag-urgent">RAPPEL CLÔTURE</div>
    <h1>{ao_titre}</h1>
    <p class="ref">Réf. {ao_reference}</p>
    <table class="meta-table">
      <tr><td>Autorité contractante</td><td>{autorite}</td></tr>
      <tr><td>Date limite</td><td class="urgent-val"><strong>{date_cloture}</strong></td></tr>
      <tr><td>Jours restants</td><td class="urgent-val"><strong>{jours_restants} jour(s)</strong></td></tr>
    </table>
    <a href="{ao_url}" class="cta-btn">Ouvrir la fiche AO →</a>
    <p style="font-size:12px;color:#64748B;">
      Désactive ce rappel depuis <a href="https://gov.netsync.bf/alertes">mes alertes</a>
      si tu ne veux plus recevoir les notifications J-3.
    </p>
    """
    subject = f"[NetSync Gov] ⏰ Rappel clôture J-{jours_restants} — {ao_titre[:60]}"
    return subject, _base_layout(content, preview_text=f"Clôture dans {jours_restants} jour(s) : {ao_titre[:80]}")


def render_bienvenue(prenom: str, plan: str,
                     secteurs: list) -> tuple[str, str]:
    """
    Template email : Bienvenue après inscription.
    Returns: (subject, html_body)
    """
    plan_label = {"gratuit": "Plan Gratuit", "pro": "Plan Pro", "equipe": "Plan Équipe"}.get(plan, plan)
    secteurs_txt = ", ".join(secteurs) if secteurs else "Tous les secteurs"
    content = f"""
    <div class="tag">🎉 Bienvenue sur NetSync Gov</div>
    <h1>Ton compte est activé, {prenom} !</h1>
    <p style="font-size:14px;color:#4A5568;margin:0 0 20px;line-height:1.6;">
      Tu recevras tes premières alertes <strong>demain matin à 07h00</strong>,
      directement dans ta boite email et sur WhatsApp.
    </p>
    <table class="meta-table">
      <tr><td>Plan actif</td><td><strong>{plan_label}</strong></td></tr>
      <tr><td>Secteurs surveillés</td><td>{secteurs_txt}</td></tr>
      <tr><td>Heure d'envoi</td><td>07h00, chaque matin (Lun–Ven)</td></tr>
      <tr><td>Sources</td><td>DGCMEF, UNDP, Banque Mondiale</td></tr>
    </table>
    <a href="https://gov.netsync.bf/dashboard" class="cta-btn">Accéder à mon tableau de bord →</a>
    <p style="font-size:12px;color:#64748B;margin:0;">
      Configure tes alertes et secteurs depuis
      <a href="https://gov.netsync.bf/alertes">mes alertes</a>.
    </p>
    """
    subject = f"Bienvenue sur NetSync Gov, {prenom} — tes alertes AO sont activées !"
    return subject, _base_layout(content, preview_text="Ton compte est activé. Premier AO demain à 07h00.")
