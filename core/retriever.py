"""
Recherche sémantique dans la table knowledge_chunks de Supabase.
Vectorise la question du client et retourne les chunks les plus pertinents.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from supabase import create_client
import openai


def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except:
        return os.environ.get(key)


SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_SECRET = get_secret("SUPABASE_SECRET")
OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET)
client = openai.OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")


def vectoriser(texte):
    response = client.embeddings.create(model="text-embedding-ada-002", input=texte)
    return response.data[0].embedding


def chercher_knowledge(question, nb_resultats=3):
    """
    Vectorise la question et retourne les chunks les plus pertinents
    depuis la base de connaissance.
    """
    vecteur = vectoriser(question)

    resultats = supabase.rpc("recherche_knowledge", {
        "query_embedding": vecteur,
        "match_count": nb_resultats
    }).execute()

    return [r["contenu"] for r in resultats.data]
