"""
Orchestrateur principal — Appels Offres BF
Lance tous les scrapers, déduplique et sauvegarde en base SQLite.
"""

import sys
import os
import time

# Accès au module database depuis le dossier parent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.database import get_connection, init_db
from scraper.sources import (
    scraper_lesaffairesbf,
    scraper_arcop,
    scraper_joffres,
    scraper_dgcmef,
    scraper_pnud,
)


# ---------------------------------------------------------------------------
# Persistance
# ---------------------------------------------------------------------------

def sauvegarder_offres(offres: list[dict]) -> tuple[int, int]:
    """
    Insère les offres dans la table `offres`.
    Déduplique sur url_source (contrainte UNIQUE).

    Retourne (nouvelles, doublons).
    """
    nouvelles = 0
    doublons = 0
    conn = get_connection()

    for o in offres:
        try:
            conn.execute(
                """
                INSERT INTO offres
                    (titre, source, url_source, type_offre,
                     secteur, date_publication, date_limite, statut)
                VALUES (?, ?, ?, 'public', ?, ?, ?, 'ouvert')
                """,
                (
                    o.get("titre"),
                    o.get("source"),
                    o.get("lien") or "",
                    o.get("secteur"),
                    o.get("date_pub"),
                    o.get("date_limite"),
                ),
            )
            nouvelles += 1
        except Exception as e:
            # UNIQUE constraint failed → doublon
            if "UNIQUE" in str(e):
                doublons += 1
            else:
                print(f"  [DB] Erreur insertion : {e}")

    conn.commit()
    conn.close()
    return nouvelles, doublons


# ---------------------------------------------------------------------------
# Orchestrateur
# ---------------------------------------------------------------------------

def lancer_scraping():
    """Lance tous les scrapers et sauvegarde les résultats en base."""

    print("\n" + "=" * 60)
    print("  Appels Offres BF — Scraping")
    print("=" * 60)

    # S'assurer que la BDD existe
    init_db()

    resultats = []

    # --- lesaffairesbf.com : 3 premières pages ---
    print("\n[1/5] lesaffairesbf.com (3 pages) ...")
    resultats.append(("lesaffairesbf.com", scraper_lesaffairesbf(max_pages=3)))
    time.sleep(2)

    # --- arcop.bf : 2 pages disponibles ---
    print("\n[2/5] arcop.bf (2 pages) ...")
    resultats.append(("arcop.bf", scraper_arcop(max_pages=2)))
    time.sleep(2)

    # --- joffres.net : 2 premières pages (public + privé) ---
    print("\n[3/5] joffres.net (2 pages public + privé) ...")
    resultats.append(("joffres.net", scraper_joffres(max_pages=2)))
    time.sleep(2)

    # --- dgcmef.gov.bf : tableau de quotidiens ---
    print("\n[4/5] dgcmef.gov.bf ...")
    resultats.append(("dgcmef.gov.bf", scraper_dgcmef()))
    time.sleep(2)

    # --- PNUD Burkina Faso ---
    print("\n[5/5] procurement-notices.undp.org (BF) ...")
    resultats.append(("pnud", scraper_pnud()))

    # --- Sauvegarde ---
    print("\n" + "-" * 60)
    print("  Sauvegarde en base SQLite ...")
    print("-" * 60)

    total_trouvees = 0
    total_nouvelles = 0
    total_doublons = 0

    for source, offres in resultats:
        n, d = sauvegarder_offres(offres)
        total_trouvees += len(offres)
        total_nouvelles += n
        total_doublons += d
        print(f"  {source:<22} {len(offres):>3} trouvées  "
              f"{n:>3} nouvelles  {d:>3} doublons")

    # --- Résumé global ---
    print("\n" + "=" * 60)
    print(f"  TOTAL trouvées  : {total_trouvees}")
    print(f"  Nouvelles en BDD: {total_nouvelles}")
    print(f"  Doublons ignorés: {total_doublons}")
    print("=" * 60)

    # --- Aperçu des offres en base ---
    _afficher_offres_en_base()


def _afficher_offres_en_base():
    """Affiche les 10 dernières offres insérées en base."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, source, titre, date_publication, date_limite, statut
        FROM offres
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM offres").fetchone()[0]
    conn.close()

    print(f"\n  Base de données — {total} offre(s) au total")
    print(f"  {'─' * 56}")
    print(f"  {'ID':<5} {'Source':<16} {'Titre':<35} {'Pub':<12}")
    print(f"  {'─' * 56}")
    for row in rows:
        titre_court = (row["titre"] or "")[:33]
        if len(row["titre"] or "") > 33:
            titre_court += ".."
        print(
            f"  {row['id']:<5} {row['source']:<16} "
            f"{titre_court:<35} {row['date_publication'] or '—':<12}"
        )
    print(f"  {'─' * 56}\n")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    lancer_scraping()
