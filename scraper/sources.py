"""
Scrapers par source — Appels Offres BF
Fonctions : scraper_lesaffairesbf(), scraper_arcop()
Chaque fonction retourne une liste de dicts :
  {titre, date_pub, date_limite, secteur, lien, source}
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
# Test direct
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 58)
    print("  TEST — Scrapers Appels Offres BF")
    print("=" * 58)

    print("\n[1/2] Scraping lesaffairesbf.com (1 page) ...")
    offres_lesaffaires = scraper_lesaffairesbf(max_pages=1)
    print(f"\n  → {len(offres_lesaffaires)} offre(s)")
    for o in offres_lesaffaires[:3]:
        print(f"    • {o['titre'][:65]}")
        print(f"      Pub: {o['date_pub']}  |  {o['lien'][:55]}")

    time.sleep(2)

    print("\n[2/2] Scraping arcop.bf (toutes les pages) ...")
    offres_arcop = scraper_arcop(max_pages=2)
    print(f"\n  → {len(offres_arcop)} offre(s)")
    for o in offres_arcop[:3]:
        print(f"    • {o['titre'][:65]}")
        print(f"      Pub: {o['date_pub']}  |  {o['lien'][:55]}")

    print("\n" + "=" * 58)
    print(f"  lesaffairesbf.com : {len(offres_lesaffaires):>3} offre(s)")
    print(f"  arcop.bf          : {len(offres_arcop):>3} offre(s)")
    print(f"  TOTAL             : {len(offres_lesaffaires) + len(offres_arcop):>3} offre(s)")
    print("=" * 58 + "\n")
