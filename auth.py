"""Single-owner access with PBKDF2 and a shared, persistent login throttle."""
import hashlib
import time
from uuid import uuid4

import streamlit as st
from sqlalchemy import delete, func, insert, select

from inventory import ROOT, auth_attempts, verify_password


def configured_hash(config, production):
    encoded = config("ADMIN_PASSWORD_HASH", "")
    if not encoded and not production:
        path = ROOT / "data/admin_password.hash"
        if path.exists():
            encoded = path.read_text(encoding="utf-8").strip()
    return encoded


def authenticated(encoded):
    session = st.session_state.get("auth", {})
    fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
    return bool(encoded and session.get("fingerprint") == fingerprint and session.get("until", 0) > time.time())


def login(db, password, encoded):
    timestamp = int(time.time())
    with db.engine.begin() as conn:
        conn.execute(delete(auth_attempts).where(auth_attempts.c.at < timestamp - 300))
        failures = conn.execute(select(func.count()).select_from(auth_attempts)).scalar_one()
        if failures >= 20:
            return "Hay demasiados intentos. Espera 5 minutos antes de volver a entrar."
        # Count before verifying, so attempts across concurrent sessions share a budget.
        attempt_id = str(uuid4())
        conn.execute(insert(auth_attempts).values(id=attempt_id, at=timestamp))
    if not verify_password(password, encoded):
        return "Contraseña incorrecta."
    with db.engine.begin() as conn:
        conn.execute(delete(auth_attempts).where(auth_attempts.c.id == attempt_id))
    st.session_state["auth"] = {"fingerprint": hashlib.sha256(encoded.encode()).hexdigest(),
                                "until": time.time() + 12 * 3600}
    return None


def logout():
    for key in list(st.session_state):
        del st.session_state[key]
