"""
Base de données SQLite — Appels Offres BF
Tables : offres, utilisateurs, alertes, favoris
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "appels_offres.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        -- -------------------------------------------------------
        -- Table : offres
        -- -------------------------------------------------------
        CREATE TABLE IF NOT EXISTS offres (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            titre           TEXT    NOT NULL,
            description     TEXT,
            source          TEXT    NOT NULL,          -- joffres | lesaffairesbf | cci
            url_source      TEXT    UNIQUE NOT NULL,   -- lien original (clé de dédup)
            type_offre      TEXT    NOT NULL DEFAULT 'public',  -- public | prive
            secteur         TEXT,                      -- BTP, IT, Santé, ...
            montant_estime  REAL,                      -- en FCFA, peut être NULL
            date_publication TEXT,                     -- ISO 8601
            date_limite     TEXT,                      -- date de clôture ISO 8601
            organisme       TEXT,                      -- maître d'ouvrage
            localisation    TEXT,                      -- région / ville
            statut          TEXT    NOT NULL DEFAULT 'ouvert',  -- ouvert | clos | annule
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_offres_source      ON offres(source);
        CREATE INDEX IF NOT EXISTS idx_offres_secteur     ON offres(secteur);
        CREATE INDEX IF NOT EXISTS idx_offres_statut      ON offres(statut);
        CREATE INDEX IF NOT EXISTS idx_offres_date_limite ON offres(date_limite);

        -- -------------------------------------------------------
        -- Table : utilisateurs
        -- -------------------------------------------------------
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nom             TEXT    NOT NULL,
            prenom          TEXT,
            email           TEXT    UNIQUE NOT NULL,
            telephone       TEXT,
            mot_de_passe    TEXT    NOT NULL,          -- hash bcrypt
            entreprise      TEXT,
            secteurs_interet TEXT,                     -- JSON array ex: ["BTP","IT"]
            type_compte     TEXT    NOT NULL DEFAULT 'gratuit',  -- gratuit | premium
            actif           INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            last_login      TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_utilisateurs_email ON utilisateurs(email);

        -- -------------------------------------------------------
        -- Table : alertes
        -- -------------------------------------------------------
        CREATE TABLE IF NOT EXISTS alertes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id  INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
            nom_alerte      TEXT    NOT NULL,
            mots_cles       TEXT,                      -- JSON array ex: ["fournitures","bureau"]
            secteur         TEXT,
            montant_min     REAL,
            montant_max     REAL,
            type_offre      TEXT,                      -- public | prive | NULL = tous
            canal           TEXT    NOT NULL DEFAULT 'email',  -- email | sms | les deux
            frequence       TEXT    NOT NULL DEFAULT 'instantane',  -- instantane | quotidien | hebdo
            actif           INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_alertes_utilisateur ON alertes(utilisateur_id);

        -- -------------------------------------------------------
        -- Table : favoris
        -- -------------------------------------------------------
        CREATE TABLE IF NOT EXISTS favoris (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id  INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
            offre_id        INTEGER NOT NULL REFERENCES offres(id) ON DELETE CASCADE,
            note            TEXT,                      -- commentaire libre
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(utilisateur_id, offre_id)
        );

        CREATE INDEX IF NOT EXISTS idx_favoris_utilisateur ON favoris(utilisateur_id);
        CREATE INDEX IF NOT EXISTS idx_favoris_offre       ON favoris(offre_id);
    """)

    conn.commit()
    conn.close()


def resume_db():
    """Affiche un résumé de l'état de la base de données."""
    conn = get_connection()
    cur = conn.cursor()

    tables = ["offres", "utilisateurs", "alertes", "favoris"]

    print("\n" + "=" * 50)
    print("  Appels Offres BF — Base de données SQLite")
    print("=" * 50)
    print(f"  Fichier : {DB_PATH}\n")

    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]

        cur.execute(f"PRAGMA table_info({table})")
        colonnes = [row["name"] for row in cur.fetchall()]

        print(f"  [{table}]")
        print(f"    Lignes   : {count}")
        print(f"    Colonnes : {', '.join(colonnes)}")
        print()

    conn.close()
    print("=" * 50)
    print("  Base initialisée avec succès.")
    print("=" * 50 + "\n")


def inscrire_utilisateur(
    nom: str,
    email: str,
    secteurs: list[str] | None = None,
    prenom: str | None = None,
    telephone: str | None = None,
    entreprise: str | None = None,
) -> int:
    """
    Crée un utilisateur et ses alertes par secteur.

    - Un utilisateur est créé avec mot_de_passe vide (à définir via l'API).
    - Pour chaque secteur fourni, une alerte email instantanée est créée.
    - Si l'email existe déjà, retourne l'id existant sans modification.

    Retourne l'id de l'utilisateur créé (ou existant).
    """
    import json as _json

    conn = get_connection()

    # Vérifier si l'email existe déjà
    existing = conn.execute(
        "SELECT id FROM utilisateurs WHERE email = ?", (email,)
    ).fetchone()
    if existing:
        conn.close()
        return existing["id"]

    secteurs_json = _json.dumps(secteurs or [], ensure_ascii=False)

    cur = conn.execute(
        """
        INSERT INTO utilisateurs
            (nom, prenom, email, telephone, entreprise,
             mot_de_passe, secteurs_interet, type_compte, actif)
        VALUES (?, ?, ?, ?, ?, '', ?, 'gratuit', 1)
        """,
        (nom, prenom, email, telephone, entreprise, secteurs_json),
    )
    user_id = cur.lastrowid

    # Créer une alerte par secteur
    for secteur in (secteurs or []):
        conn.execute(
            """
            INSERT INTO alertes
                (utilisateur_id, nom_alerte, secteur, canal, frequence, actif)
            VALUES (?, ?, ?, 'email', 'instantane', 1)
            """,
            (user_id, f"Alerte {secteur}", secteur),
        )

    # Si aucun secteur : créer une alerte générale (toutes offres)
    if not secteurs:
        conn.execute(
            """
            INSERT INTO alertes
                (utilisateur_id, nom_alerte, canal, frequence, actif)
            VALUES (?, 'Toutes les offres', 'email', 'instantane', 1)
            """,
            (user_id,),
        )

    conn.commit()
    conn.close()
    return user_id


if __name__ == "__main__":
    init_db()
    resume_db()
