"""
Charge et met en cache le comportement (page 2) et les capacités (page 3)
depuis Supabase. Rechargement hebdomadaire automatique ou forçage manuel.
"""

import os
import time
from supabase import create_client


def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except:
        return os.environ.get(key)


SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_SECRET = get_secret("SUPABASE_SECRET")

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET)

# Cache en mémoire
_cache = {
    "behavior": None,
    "capabilities": None,
    "timestamp": 0
}

# Une semaine en secondes
CACHE_DUREE = 7 * 24 * 60 * 60


def _cache_expire():
    return time.time() - _cache["timestamp"] > CACHE_DUREE


def _charger_depuis_supabase():
    behavior = supabase.table("behavior").select("contenu").limit(1).execute()
    capabilities = supabase.table("capabilities").select("contenu").limit(1).execute()

    _cache["behavior"] = behavior.data[0]["contenu"] if behavior.data else ""
    _cache["capabilities"] = capabilities.data[0]["contenu"] if capabilities.data else ""
    _cache["timestamp"] = time.time()

    print("Configuration rechargée depuis Supabase.")


def get_behavior():
    if not _cache["behavior"] or _cache_expire():
        _charger_depuis_supabase()
    return _cache["behavior"]


def get_capabilities():
    if not _cache["capabilities"] or _cache_expire():
        _charger_depuis_supabase()
    return _cache["capabilities"]


def forcer_rechargement():
    """Appelé manuellement depuis la face agent pour forcer la mise à jour."""
    _charger_depuis_supabase()
