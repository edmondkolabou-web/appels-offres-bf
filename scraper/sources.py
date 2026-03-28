"""
Scrapers par source — Appels Offres BF
Fonctions : scraper_lesaffairesbf(), scraper_arcop(),
            scraper_joffres(), scraper_dgcmef(), scraper_pnud()
Chaque fonction retourne une liste de dicts :
  {titre, date_pub, date_limite, secteur, organisme,
   localisation, type_offre, lien, source}
"""

import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}
TIMEOUT = 15  # secondes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(url: str) -> BeautifulSoup | None:
    """Effectue un GET et retourne un BeautifulSoup, ou None en cas d'erreur."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.exceptions.HTTPError as e:
        print(f"  [ERREUR HTTP] {url} → {e}")
    except requests.exceptions.ConnectionError:
        print(f"  [ERREUR CONNEXION] Impossible de joindre {url}")
    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] {url}")
    except Exception as e:
        print(f"  [ERREUR] {url} → {e}")
    return None


def _extraire_date_limite(texte: str) -> str | None:
    """
    Cherche une date limite dans un texte libre.
    Patterns reconnus :
      - "Date limite : 15 avril 2025"
      - "avant le 15/04/2025"
      - "clôture le 15-04-2025"
    """
    patterns = [
        r"(?:date\s+limite|clôture|avant\s+le|jusqu['\u2019]au)\s*[:\s]*"
        r"(\d{1,2}[\s/\-]\w+[\s/\-]\d{2,4})",
        r"(\d{1,2}/\d{2}/\d{2,4})",
        r"(\d{1,2}-\d{2}-\d{2,4})",
    ]
    for pat in patterns:
        m = re.search(pat, texte, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# 1. lesaffairesbf.com
# ---------------------------------------------------------------------------

URL_LESAFFAIRES = "https://www.lesaffairesbf.com/category/appels-doffres/"


def scraper_lesaffairesbf(max_pages: int = 1) -> list[dict]:
    """
    Scrape les appels d'offres de lesaffairesbf.com.

    Structure réelle observée (widget WordPress "Newest Posts") :
      - Chaque entrée : <li> contenant <div class="newest-posts-text">
      - Titre + lien  : <a class="newest-posts-title">
      - Date pub      : <span class="date">  (ex: "Mar 26, 2026")
      - Extrait       : <div class="newest-posts-content">
      - Pagination    : .../page/N/  (175 pages disponibles)

    date_limite et secteur absents du listing — disponibles uniquement
    en visitant chaque article individuellement.
    """
    offres = []

    for page in range(1, max_pages + 1):
        url = URL_LESAFFAIRES if page == 1 else f"{URL_LESAFFAIRES}page/{page}/"
        print(f"  [lesaffairesbf] Page {page}/{max_pages} → {url}")

        soup = _get(url)
        if soup is None:
            break

        entries = [li for li in soup.select("li") if li.select_one(".newest-posts-text")]
        if not entries:
            print(f"  [lesaffairesbf] Aucune entrée trouvée page {page}, arrêt.")
            break

        for entry in entries:
            try:
                lien_tag = entry.select_one("a.newest-posts-title, h2 a")
                if not lien_tag:
                    continue
                titre = lien_tag.get_text(strip=True)
                lien = lien_tag.get("href", "").strip()

                date_tag = entry.select_one("span.date")
                date_pub = date_tag.get_text(strip=True) if date_tag else None

                extrait_tag = entry.select_one(".newest-posts-content")
                extrait = extrait_tag.get_text(" ", strip=True) if extrait_tag else ""
                date_limite = _extraire_date_limite(extrait)

                offres.append({
                    "titre": titre,
                    "date_pub": date_pub,
                    "date_limite": date_limite,
                    "secteur": None,  # absent du listing
                    "lien": lien,
                    "source": "lesaffairesbf",
                })

            except Exception as e:
                print(f"  [lesaffairesbf] Erreur entrée : {e}")
                continue

        if page < max_pages:
            time.sleep(2)

    return offres


# ---------------------------------------------------------------------------
# 2. arcop.bf  (remplace cci.bf — inaccessible)
# ---------------------------------------------------------------------------

URL_ARCOP = "https://www.arcop.bf/appels-doffres/"


def scraper_arcop(max_pages: int = 2) -> list[dict]:
    """
    Scrape les appels d'offres de l'ARCOP (Autorité de Régulation
    de la Commande Publique du Burkina Faso).
    URL : https://www.arcop.bf/appels-doffres/

    Structure réelle observée :
      - Tableau HTML unique par page
      - Titre : <div id="doc-title"> dans chaque <td>
      - Lien  : <a class="attachment-link" href=".../telechargement/ID">
                 → lien vers le PDF de l'avis (utilisé comme url_source)
      - Pas de date publiée dans le listing (dates parfois dans le titre)
      - Pagination WordPress : .../page/N/  (2 pages, ~17 offres au total)

    date_pub et date_limite sont extraits du titre quand disponibles.
    """
    offres = []

    for page in range(1, max_pages + 1):
        url = URL_ARCOP if page == 1 else f"{URL_ARCOP}page/{page}/"
        print(f"  [arcop] Page {page}/{max_pages} → {url}")

        soup = _get(url)
        if soup is None:
            break

        rows = soup.select("table tr")[1:]  # skip header
        if not rows:
            print(f"  [arcop] Aucune ligne trouvée page {page}, arrêt.")
            break

        for row in rows:
            try:
                titre_tag = row.select_one("div#doc-title")
                if not titre_tag:
                    continue
                titre = titre_tag.get_text(strip=True)
                if not titre:
                    continue

                lien_tag = row.select_one("a.attachment-link")
                lien = lien_tag.get("href", "").strip() if lien_tag else url

                # Extraire dates depuis le titre (ex: "... du 02 décembre 2025")
                texte_complet = row.get_text(" ", strip=True)
                date_pub = _extraire_date_dans_titre(titre)
                date_limite = _extraire_date_limite(texte_complet)

                offres.append({
                    "titre": titre,
                    "date_pub": date_pub,
                    "date_limite": date_limite,
                    "secteur": None,
                    "lien": lien,
                    "source": "arcop",
                })

            except Exception as e:
                print(f"  [arcop] Erreur ligne : {e}")
                continue

        if page < max_pages:
            time.sleep(2)

    return offres


def _extraire_date_dans_titre(titre: str) -> str | None:
    """
    Extrait une date de publication depuis un titre d'avis ARCOP.
    Exemples : "... du 02 décembre 2025 ..."
               "... N°2026-01/ARCOP/... du 2 décembre 2025 ..."
    """
    m = re.search(
        r"\b(\d{1,2}\s+"
        r"(?:janvier|février|mars|avril|mai|juin|juillet|"
        r"août|septembre|octobre|novembre|décembre)"
        r"\s+\d{4})\b",
        titre,
        re.IGNORECASE,
    )
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# 3. joffres.net
# ---------------------------------------------------------------------------

URL_JOFFRES_PUBLICS = "https://www.joffres.net/appel-offres-publics"
URL_JOFFRES_PRIVES  = "https://www.joffres.net/appel-offres-priv%C3%A9s"


def scraper_joffres(max_pages: int = 2) -> list[dict]:
    """
    Scrape les appels d'offres de joffres.net (public + privé).

    Structure réelle observée :
      - Chaque offre : <div class="job" href="...">
      - Titre + lien  : <a class="job-title">
      - Localisation  : <small class="offre-localisation"> (ville/région)
      - Secteur       : <a class="text-danger"><small>...</small></a>
      - Organisme     : <small class="societe"> après <i class="fa-building">
      - Date limite   : <small class="expire-date"> → "Expire le JJ-MM-AAAA"
      - Date pub      : absente du listing (juste "il y a N jour(s)")
      - Type          : déterminé par la page scrapée (public/privé)
      - Pagination    : ?page=N (10 offres par page)
    """
    offres = []

    sources = [
        (URL_JOFFRES_PUBLICS, "public"),
        (URL_JOFFRES_PRIVES,  "prive"),
    ]

    for base_url, type_offre in sources:
        for page in range(1, max_pages + 1):
            url = base_url if page == 1 else f"{base_url}?page={page}"
            print(f"  [joffres] {type_offre} page {page} → {url}")

            soup = _get(url)
            if soup is None:
                break

            jobs = soup.select("div.job")
            if not jobs:
                print(f"  [joffres] Aucune offre page {page}, arrêt.")
                break

            for job in jobs:
                try:
                    # Titre + lien
                    titre_tag = job.select_one("a.job-title")
                    if not titre_tag:
                        continue
                    titre = titre_tag.get_text(separator=" ", strip=True)
                    # Retirer le texte du span.tag éventuel (vide)
                    tag_span = titre_tag.select_one("span.tag")
                    if tag_span:
                        titre = titre.replace(tag_span.get_text(), "").strip()
                    lien = titre_tag.get("href", "").strip()

                    # Localisation (région/ville)
                    loc_tag = job.select_one("small.offre-localisation")
                    localisation = None
                    if loc_tag:
                        # Supprimer le contenu de l'icône <i>
                        for i in loc_tag.select("i"):
                            i.decompose()
                        localisation = loc_tag.get_text(strip=True) or None

                    # Secteur
                    secteur_tag = job.select_one("a.text-danger small")
                    secteur = secteur_tag.get_text(strip=True) if secteur_tag else None

                    # Organisme (premier .societe avec .fa-building)
                    organisme = None
                    for sm in job.select("small.societe"):
                        if sm.select_one(".fa-building"):
                            for i in sm.select("i"):
                                i.decompose()
                            organisme = sm.get_text(strip=True) or None
                            break

                    # Date limite : "Expire le JJ-MM-AAAA"
                    expire_tag = job.select_one("small.expire-date")
                    date_limite = None
                    if expire_tag:
                        texte_expire = expire_tag.get_text(strip=True)
                        m = re.search(r"(\d{2}-\d{2}-\d{4})", texte_expire)
                        date_limite = m.group(1) if m else texte_expire or None

                    offres.append({
                        "titre":       titre,
                        "date_pub":    None,   # absent du listing
                        "date_limite": date_limite,
                        "secteur":     secteur,
                        "organisme":   organisme,
                        "localisation": localisation,
                        "type_offre":  type_offre,
                        "lien":        lien,
                        "source":      "joffres",
                    })

                except Exception as e:
                    print(f"  [joffres] Erreur entrée : {e}")
                    continue

            if page < max_pages:
                time.sleep(2)

        time.sleep(2)  # entre public et privé

    return offres


# ---------------------------------------------------------------------------
# 4. dgcmef.gov.bf
# ---------------------------------------------------------------------------

URL_DGCMEF = "https://dgcmef.gov.bf/fr/appels-d-offre"
BASE_DGCMEF = "https://dgcmef.gov.bf"


def scraper_dgcmef() -> list[dict]:
    """
    Scrape les appels d'offres du site officiel DGCMEF
    (Direction Générale du Contrôle des Marchés et des Engagements Financiers).
    URL : https://dgcmef.gov.bf/fr/appels-d-offre

    Structure réelle observée (Drupal CMS) :
      - Tableau de quotidiens : <table> avec lignes <tr class="block block-title">
      - Titre + lien interne : <td class="views-field-title"> <a href="/fr/node/XXXX">
      - Lien vers PDF : <td class="views-field-field-fichier"> <a>
      - Pas de date, secteur ni organisme dans le listing (publiés en PDF)
    """
    offres = []

    print(f"  [dgcmef] → {URL_DGCMEF}")
    soup = _get(URL_DGCMEF)
    if soup is None:
        return []

    # Table des quotidiens d'appels d'offres
    rows = soup.select("table tr.block")
    if not rows:
        # Essayer sans classe
        rows = soup.select("table tr")[1:]   # skip header

    if not rows:
        print("  [dgcmef] Aucune ligne trouvée.")
        return []

    for row in rows:
        try:
            # Titre + lien interne
            titre_cell = row.select_one("td.views-field-title a, td a")
            if not titre_cell:
                continue
            titre = titre_cell.get_text(strip=True)
            lien_relatif = titre_cell.get("href", "")
            lien = (BASE_DGCMEF + lien_relatif) if lien_relatif.startswith("/") else lien_relatif

            # Lien vers le PDF (si présent)
            pdf_cell = row.select_one("td.views-field-field-fichier a")
            if pdf_cell:
                pdf_href = pdf_cell.get("href", "")
                if pdf_href and not pdf_href.startswith("http"):
                    pdf_href = BASE_DGCMEF + pdf_href
                # Préférer le PDF comme lien si disponible
                lien = pdf_href or lien

            # Date de publication extraite du titre
            # ex: "quotidien n°4364 du mercredi 25 mars 2026"
            date_pub = _extraire_date_dans_titre(titre)

            offres.append({
                "titre":       titre,
                "date_pub":    date_pub,
                "date_limite": None,
                "secteur":     None,
                "organisme":   "DGCMEF",
                "localisation": "Burkina Faso",
                "type_offre":  "public",
                "lien":        lien,
                "source":      "dgcmef",
            })

        except Exception as e:
            print(f"  [dgcmef] Erreur ligne : {e}")
            continue

    return offres


# ---------------------------------------------------------------------------
# 5. procurement-notices.undp.org (PNUD — Burkina Faso)
# ---------------------------------------------------------------------------

URL_PNUD = "https://procurement-notices.undp.org/?country=BF"
BASE_PNUD = "https://procurement-notices.undp.org/"


def scraper_pnud() -> list[dict]:
    """
    Scrape les avis de marchés PNUD pour le Burkina Faso.
    URL : https://procurement-notices.undp.org/?country=BF

    Structure réelle observée :
      - Toutes les lignes (~512) sont dans le HTML, filtrage côté client
      - Les lignes BF ont la classe CSS 'country_5' (= UNDP-BFA/Burkina Faso)
        Confirmé par présence de "BFA" / "BURKINA" dans le contenu
      - Chaque ligne : <a class="vacanciesTableLink country_5" href="view_negotiation.cfm?...">
      - Cellules : <div class="vacanciesTable__cell">
          - Cell 0 : Title
          - Cell 1 : Ref No
          - Cell 2 : UNDP Office/Country
          - Cell 3 : Process (type de marché)
          - Cell 4 : Deadline  "JJ-Mon-AA HH:MM..."
          - Cell 5 : Posted    "JJ-Mon-AA"
    """
    offres = []

    print(f"  [pnud] → {URL_PNUD}")
    soup = _get(URL_PNUD)
    if soup is None:
        return []

    # Toutes les lignes de type BF : class country_5 ET contiennent BFA/BURKINA
    candidats = soup.select("a.vacanciesTableLink.country_5, a.vacanciesTable__row.country_5")
    bf_rows = [r for r in candidats if "BFA" in r.get_text() or "BURKINA" in r.get_text().upper()]

    if not bf_rows:
        # Fallback : chercher toutes les lignes BFA dans le texte
        bf_rows = [
            r for r in soup.select("a.vacanciesTableLink, a.vacanciesTable__row")
            if "BFA" in r.get_text() or "BURKINA FASO" in r.get_text().upper()
        ]

    print(f"  [pnud] {len(bf_rows)} offre(s) BF trouvée(s)")

    for row in bf_rows:
        try:
            cells = row.select(".vacanciesTable__cell")
            if len(cells) < 4:
                continue

            def cell_val(idx):
                if idx >= len(cells):
                    return None
                label = cells[idx].select_one(".vacanciesTable__cell__label")
                span  = cells[idx].select_one("span")
                if label:
                    label.decompose()
                return (span.get_text(strip=True) if span
                        else cells[idx].get_text(strip=True)) or None

            titre      = cell_val(0)
            ref_no     = cell_val(1)
            organisme  = cell_val(2)   # ex: "UNDP-BFA/BURKINA FASO"
            process    = cell_val(3)   # ex: "RFQ - Request for quotation"
            deadline   = cell_val(4)   # ex: "08-Apr-2609:03 AM (New York time)"
            date_pub   = cell_val(5)   # ex: "27-Mar-26"

            if not titre:
                continue

            # Nettoyer la deadline : garder uniquement la date
            # Format source : "08-Apr-2609:03 AM (New York time)"
            # L'année est sur 2 chiffres, immédiatement suivie de l'heure HH:MM
            date_limite = None
            if deadline:
                m = re.match(r"(\d{2}-\w{3}-\d{2})(?=\d{2}:\d{2}|\s|$)", deadline)
                date_limite = m.group(1) if m else deadline[:9]

            href = row.get("href", "")
            lien = (BASE_PNUD + href) if href and not href.startswith("http") else href

            offres.append({
                "titre":        titre,
                "date_pub":     date_pub,
                "date_limite":  date_limite,
                "secteur":      process,
                "organisme":    organisme,
                "localisation": "Burkina Faso",
                "type_offre":   "public",
                "lien":         lien,
                "source":       "pnud",
            })

        except Exception as e:
            print(f"  [pnud] Erreur ligne : {e}")
            continue

    return offres


# ---------------------------------------------------------------------------
# Test direct
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 62)
    print("  TEST — Scrapers Appels Offres BF (5 sources)")
    print("=" * 62)

    resultats = {}

    for nom, fn, kwargs in [
        ("lesaffairesbf.com", scraper_lesaffairesbf, {"max_pages": 1}),
        ("arcop.bf",          scraper_arcop,          {"max_pages": 2}),
        ("joffres.net",       scraper_joffres,        {"max_pages": 1}),
        ("dgcmef.gov.bf",     scraper_dgcmef,         {}),
        ("pnud",              scraper_pnud,            {}),
    ]:
        print(f"\n[{len(resultats)+1}/5] {nom} ...")
        offres = fn(**kwargs)
        resultats[nom] = offres
        print(f"  → {len(offres)} offre(s)")
        for o in offres[:2]:
            print(f"    • {o['titre'][:65]}")
            print(f"      Org: {o.get('organisme','—')}  |  Limite: {o.get('date_limite','—')}")
        if len(resultats) < 5:
            time.sleep(2)

    total = sum(len(v) for v in resultats.values())
    print("\n" + "=" * 62)
    for nom, offres in resultats.items():
        print(f"  {nom:<22} : {len(offres):>3} offre(s)")
    print(f"  {'TOTAL':<22} : {total:>3} offre(s)")
    print("=" * 62 + "\n")
