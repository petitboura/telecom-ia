"""
Charge et met en cache le comportement de l'IA depuis Supabase.
Rechargement hebdomadaire automatique.
"""

import os
import time
from supabase import create_client


def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.environ.get(key)


SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_SECRET = get_secret("SUPABASE_SECRET")

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET)

# Cache en mémoire
_cache = {
    "behavior": None,
    "timestamp": 0
}

# Une semaine en secondes
CACHE_DUREE = 7 * 24 * 60 * 60


def _cache_expire():
    # timestamp == 0 -> jamais chargé, donc considéré comme expiré
    return _cache["timestamp"] == 0 or time.time() - _cache["timestamp"] > CACHE_DUREE


def _charger_depuis_supabase():
    behavior = supabase.table("behavior").select("contenu").limit(1).execute()
    _cache["behavior"] = behavior.data[0]["contenu"] if behavior.data else ""
    _cache["timestamp"] = time.time()


def get_behavior():
    if _cache_expire():
        _charger_depuis_supabase()
    return _cache["behavior"]
