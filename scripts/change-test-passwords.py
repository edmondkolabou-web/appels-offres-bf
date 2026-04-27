#!/usr/bin/env python3
import sys; sys.path.insert(0,'.')
from backend.database import get_db
from backend.security import hash_password
from sqlalchemy import text
db = next(get_db())
db.execute(text("UPDATE abonnes SET password_hash = :h WHERE email = :e"), {"h": hash_password("RzsVK1AIn!lw9bNU"), "e": "test@netsync.bf"})
db.execute(text("UPDATE abonnes SET password_hash = :h WHERE email = :e"), {"h": hash_password("2u9ax8ucc96UMWPo"), "e": "test2@netsync.bf"})
db.commit()
print("Mots de passe changés :")
print(f"  test@netsync.bf  → RzsVK1AIn!lw9bNU")
print(f"  test2@netsync.bf → 2u9ax8ucc96UMWPo")
print("NOTEZ-LES — non récupérables.")
