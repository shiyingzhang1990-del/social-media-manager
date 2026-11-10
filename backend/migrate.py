"""Migration helper for upgrading existing database to new schema."""
import logging
from backend.database import get_db_sync, Account
from backend.crypto import encrypt_credentials

logger = logging.getLogger("migrate")


def run_migration():
    """Migrate existing accounts: encrypt cookies and set credential_type."""
    db = get_db_sync()
    try:
        accounts = db.query(Account).all()
        migrated = 0
        for acc in accounts:
            if acc.credential_type == "cookie" and acc.cookies_encrypted and not acc.credentials_encrypted:
                try:
                    import json as _json
                    raw = _json.loads(acc.cookies_encrypted)
                    acc.credentials_encrypted = encrypt_credentials(raw)
                    migrated += 1
                except Exception:
                    pass
        if migrated > 0:
            db.commit()
            logger.info(f"Migrated {migrated} accounts to encrypted credential storage")
        db.close()
    except Exception as e:
        logger.warning(f"Migration skipped or partial: {e}")
