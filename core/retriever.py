"""
Recherche sémantique dans la table knowledge_chunks de Supabase.
"""
import os
from supabase import create_client
import google.generativeai as genai

def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except:
        return os.environ.get(key)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_SECRET = get_secret("SUPABASE_SECRET")
GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET)
genai.configure(api_key=GOOGLE_API_KEY)

def vectoriser(texte):
    response = genai.embed_content(
        model="models/text-embedding-004",
        content=texte
    )
    return response["embedding"]

def chercher_knowledge(question, nb_resultats=3):
    try:
        vecteur = vectoriser(question)
    except Exception:
        return []
    try:
        resultats = supabase.rpc("recherche_knowledge", {
            "query_embedding": vecteur,
            "match_count": nb_resultats
        }).execute()
    except Exception:
        return []
    return [r["contenu"] for r in (resultats.data or [])]
