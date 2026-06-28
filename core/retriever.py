"""
Recherche sémantique dans la table knowledge_chunks de Supabase.
"""
import os
from supabase import create_client
from google import genai

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
client_google = genai.Client(api_key=GOOGLE_API_KEY)

def vectoriser(texte):
    response = client_google.models.embed_content(
        model="gemini-embedding-001",
        contents=texte
    )
    return response.embeddings[0].values
    return response.embeddings[0].values

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
