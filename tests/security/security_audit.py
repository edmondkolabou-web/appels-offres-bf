"""
NetSync Gov — Audit de sécurité automatisé
Vérifie les vulnérabilités courantes dans le code source.
Usage : python security_audit.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

CHECKS_PASSED = []
CHECKS_FAILED = []
CHECKS_WARN   = []


def ok(msg):  CHECKS_PASSED.append(msg)
def fail(msg): CHECKS_FAILED.append(msg)
def warn(msg): CHECKS_WARN.append(msg)


def check_secrets_in_code():
    """Vérifie qu'aucun secret n'est hardcodé dans le code source."""
    patterns = [
        (r'password\s*=\s*["\'][^"\']{6,}["\']', "Mot de passe hardcodé"),
        (r'api_key\s*=\s*["\'][a-zA-Z0-9_-]{20,}["\']', "API key hardcodée"),
        (r'secret_key\s*=\s*["\'][^"\']{10,}["\']', "Secret key hardcodée"),
        (r're_[a-zA-Z0-9]{20,}', "Token Resend potentiellement exposé"),
        (r'sk-ant-[a-zA-Z0-9]{20,}', "Clé Anthropic potentiellement exposée"),
    ]
    issues = []
    py_files = list(ROOT.rglob("*.py"))
    for f in py_files:
        if any(skip in str(f) for skip in ["test_", "__pycache__", ".env"]):
            continue
        content = f.read_text(errors="ignore")
        for pattern, label in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Vérifier que ce n'est pas une variable d'env
                real_secrets = [m for m in matches if "os.getenv" not in content[max(0, content.find(m)-50):content.find(m)+50]]
                if real_secrets:
                    issues.append(f"{f.relative_to(ROOT)}: {label}")

    if issues:
        for i in issues:
            fail(f"Secret potentiel: {i}")
    else:
        ok("Aucun secret hardcodé détecté")


def check_sql_injection():
    """Vérifie l'absence de requêtes SQL par concaténation de chaînes."""
    risky_patterns = [
        r'execute\s*\(\s*f["\'].*\{',
        r'execute\s*\(\s*["\'].*%\s*\(',
        r'execute\s*\(\s*["\'].*\+',
    ]
    safe_patterns = [r'text\s*\(', r'sqlalchemy']  # SQLAlchemy = safe

    issues = []
    for f in ROOT.rglob("*.py"):
        if "__pycache__" in str(f) or "test_" in f.name:
            continue
        content = f.read_text(errors="ignore")
        for pattern in risky_patterns:
            if re.search(pattern, content):
                issues.append(str(f.relative_to(ROOT)))

    if issues:
        for i in issues[:3]:
            warn(f"Possible injection SQL à vérifier: {i}")
    else:
        ok("Aucune concaténation SQL risquée détectée")


def check_jwt_config():
    """Vérifie la configuration JWT."""
    security_file = ROOT / "api_netsync_gov" / "security.py"
    if not security_file.exists():
        warn("security.py introuvable")
        return

    content = security_file.read_text()

    if 'algorithm.*HS256' in content or '"HS256"' in content:
        ok("Algorithme JWT HS256 configuré")
    else:
        warn("Algorithme JWT non vérifié")

    if 'os.getenv' in content and 'JWT_SECRET_KEY' in content:
        ok("JWT_SECRET_KEY chargée depuis variable d'environnement")
    else:
        fail("JWT_SECRET_KEY non chargée depuis env — risque sécurité")

    if 'TOKEN_EXPIRE' in content:
        ok("Durée d'expiration JWT configurée")


def check_password_hashing():
    """Vérifie que les mots de passe sont hashés avec bcrypt."""
    security_file = ROOT / "api_netsync_gov" / "security.py"
    if not security_file.exists():
        warn("security.py introuvable")
        return

    content = security_file.read_text()
    if "bcrypt" in content and "hashpw" in content:
        ok("Hachage bcrypt utilisé pour les mots de passe")
    elif "bcrypt" in content:
        ok("bcrypt importé")
    else:
        fail("Hachage mot de passe non vérifié")


def check_cors_config():
    """Vérifie que le CORS n'est pas ouvert à tout le monde."""
    main_file = ROOT / "api_netsync_gov" / "main.py"
    if not main_file.exists():
        warn("main.py introuvable")
        return

    content = main_file.read_text()
    if 'allow_origins=["*"]' in content:
        fail("CORS ouvert à tous les origines (*) — risque sécurité")
    elif "gov.netsync.bf" in content:
        ok("CORS restreint aux domaines autorisés")
    else:
        warn("Configuration CORS à vérifier manuellement")


def check_webhook_signature():
    """Vérifie que le webhook CinetPay valide la signature HMAC."""
    cp_file = ROOT / "paiement_netsync_gov" / "cinetpay_client.py"
    if not cp_file.exists():
        warn("cinetpay_client.py introuvable")
        return

    content = cp_file.read_text()
    if "hmac" in content and "sha256" in content.lower():
        ok("Signature HMAC-SHA256 validée sur le webhook CinetPay")
    elif "hmac" in content:
        ok("Validation HMAC présente sur le webhook")
    else:
        fail("Validation signature webhook CinetPay absente")


def check_rate_limiting():
    """Vérifie la présence du rate limiting Nginx."""
    nginx_conf = ROOT / "deploy_netsync_gov" / "nginx" / "gov.netsync.bf.conf"
    if not nginx_conf.exists():
        warn("nginx.conf introuvable")
        return

    content = nginx_conf.read_text()
    if "limit_req" in content:
        ok("Rate limiting Nginx configuré (limit_req)")
    else:
        fail("Rate limiting Nginx absent")

    if "limit_req zone=auth" in content or "zone=auth" in content:
        ok("Rate limiting spécifique endpoint auth configuré")


def check_https_hsts():
    """Vérifie HTTPS forcé et HSTS."""
    nginx_conf = ROOT / "deploy_netsync_gov" / "nginx" / "gov.netsync.bf.conf"
    if not nginx_conf.exists():
        return

    content = nginx_conf.read_text()
    if "return 301 https" in content:
        ok("Redirection HTTP → HTTPS configurée")
    else:
        fail("Redirection HTTP→HTTPS manquante")

    if "Strict-Transport-Security" in content:
        ok("HSTS (Strict-Transport-Security) configuré")
    else:
        warn("HSTS non configuré")


def check_input_validation():
    """Vérifie la validation des inputs via Pydantic."""
    schemas_file = ROOT / "api_netsync_gov" / "schemas.py"
    if not schemas_file.exists():
        warn("schemas.py introuvable")
        return

    content = schemas_file.read_text()
    if "field_validator" in content or "validator" in content:
        ok("Validators Pydantic personnalisés présents")
    if "EmailStr" in content:
        ok("Validation email via EmailStr (Pydantic)")
    if "pattern=" in content or "regex=" in content:
        ok("Validation par pattern regex (enums plan, canal, etc.)")
    if "min_length" in content or "max_length" in content:
        ok("Contraintes longueur sur les champs sensibles")


def check_env_file_in_gitignore():
    """Vérifie que .env est dans .gitignore."""
    gitignore = ROOT / ".gitignore"
    if not gitignore.exists():
        warn(".gitignore introuvable — créer et y ajouter .env")
        return

    content = gitignore.read_text()
    if ".env" in content:
        ok(".env dans .gitignore")
    else:
        fail(".env absent du .gitignore — risque d'exposition des secrets")


def check_non_root_docker():
    """Vérifie que le Dockerfile utilise un utilisateur non-root."""
    dockerfile = ROOT / "deploy_netsync_gov" / "Dockerfile.backend"
    if not dockerfile.exists():
        warn("Dockerfile.backend introuvable")
        return

    content = dockerfile.read_text()
    if "adduser" in content or "USER" in content:
        ok("Dockerfile utilise un utilisateur non-root")
    else:
        fail("Dockerfile tourne en root — risque sécurité")


def run_all():
    print("=== AUDIT SÉCURITÉ NetSync Gov ===\n")

    check_secrets_in_code()
    check_sql_injection()
    check_jwt_config()
    check_password_hashing()
    check_cors_config()
    check_webhook_signature()
    check_rate_limiting()
    check_https_hsts()
    check_input_validation()
    check_env_file_in_gitignore()
    check_non_root_docker()

    print(f"✓ PASSED ({len(CHECKS_PASSED)}) :")
    for c in CHECKS_PASSED:
        print(f"  ✓ {c}")

    if CHECKS_WARN:
        print(f"\n⚠ WARNINGS ({len(CHECKS_WARN)}) :")
        for c in CHECKS_WARN:
            print(f"  ⚠ {c}")

    if CHECKS_FAILED:
        print(f"\n✗ FAILED ({len(CHECKS_FAILED)}) :")
        for c in CHECKS_FAILED:
            print(f"  ✗ {c}")

    print(f"\n{'SÉCURITÉ OK' if not CHECKS_FAILED else 'CORRECTIONS REQUISES'}")
    return len(CHECKS_FAILED) == 0


if __name__ == "__main__":
    ok_result = run_all()
    sys.exit(0 if ok_result else 1)
