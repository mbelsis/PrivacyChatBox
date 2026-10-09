"""
Secure data written by earlier versions.

* Encrypts plaintext conversation titles, message content and file names when
  ``DATA_ENCRYPTION_KEY`` is set, and re-encrypts existing values with the primary key
  (run after prepending a new key to rotate).
* Masks the raw sensitive values that older versions stored in privacy-detection logs.

The script is idempotent and safe to run on every start-up.
"""

import sys

import sqlalchemy as sa

import database
from data_protection import encryption_enabled, mask_detected_patterns, rotate_value

ENCRYPTED_COLUMNS = [
    ("conversations", "title"),
    ("messages", "content"),
    ("files", "original_name"),
]
BATCH_SIZE = 500


def _encrypt_table(conn, table: str, column: str) -> int:
    """Encrypt or re-key every value, paging by primary key to bound memory use.

    Table and column names come from the constant ENCRYPTED_COLUMNS list.
    """
    changed = 0
    last_id = 0
    while True:
        rows = conn.execute(
            sa.text(
                f"SELECT id, {column} FROM {table} "
                f"WHERE {column} IS NOT NULL AND id > :last_id ORDER BY id LIMIT :limit"
            ),
            {"last_id": last_id, "limit": BATCH_SIZE},
        ).fetchall()
        if not rows:
            return changed
        for row_id, value in rows:
            new_value = rotate_value(value)
            if new_value != value:
                conn.execute(sa.text(f"UPDATE {table} SET {column} = :value WHERE id = :id"), {"value": new_value, "id": row_id})
                changed += 1
            last_id = row_id


def _mask_detection_events(session) -> int:
    from models import DetectionEvent

    changed = 0
    events = session.query(DetectionEvent).filter(DetectionEvent.action.in_(["scan", "anonymize"])).all()
    for event in events:
        current = event.get_detected_patterns()
        masked = mask_detected_patterns(current)
        if masked != current:
            event.detected_patterns = masked
            changed += 1
    return changed


def run_migration() -> bool:
    if not database.init_db():
        print("Unable to initialize database connection for migration.")
        return False

    try:
        if encryption_enabled():
            with database.engine.begin() as conn:
                inspector = sa.inspect(conn)
                for table, column in ENCRYPTED_COLUMNS:
                    if inspector.has_table(table):
                        count = _encrypt_table(conn, table, column)
                        print(f"Encrypted/rotated {count} value(s) in {table}.{column}")
        else:
            print("DATA_ENCRYPTION_KEY not set: skipping encryption of existing data.")

        with database.session_scope() as session:
            print(f"Masked sensitive values in {_mask_detection_events(session)} detection event(s)")
        return True
    except Exception as exc:
        print(f"Error securing existing data: {exc}")
        return False


if __name__ == "__main__":
    sys.exit(0 if run_migration() else 1)
