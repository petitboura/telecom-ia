"""
Indexation de la Page 1 Notion (Base de connaissance) vers Supabase pgvector.
Table cible : knowledge_chunks
Logique incrémentale : on ne réindexe que les pages modifiées depuis la dernière indexation.
Lancé via GitHub Action quotidienne.
"""

import os
import requests
from supabase import create_client
from google import genai

def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except:
        return os.environ.get(key)

NOTION_TOKEN = get_secret("NOTION_TOKEN")
NOTION_PAGE_KNOWLEDGE_ID = get_secret("NOTION_PAGE_KNOWLEDGE_ID")
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_SECRET = get_secret("SUPABASE_SECRET")
GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET)
client_google = genai.Client(api_key=GOOGLE_API_KEY)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28"
}

TABLE = "knowledge_chunks"

def get_page_metadata(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    last_edited = data.get("last_edited_time")
    titre = "Sans titre"
    for prop in data.get("properties", {}).values():
        if prop.get("type") == "title":
            morceaux = prop.get("title", [])
            if morceaux:
                titre = morceaux[0].get("plain_text", "Sans titre")
    return titre, last_edited

def get_texte_et_sous_pages(block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
    response = requests.get(url, headers=HEADERS)
    blocks = response.json().get("results", [])
    texte = ""
    sous_pages = []
    for block in blocks:
        type_block = block.get("type")
        if type_block in ["paragraph", "bulleted_list_item", "numbered_list_item",
                          "heading_1", "heading_2", "heading_3"]:
            rich_text = block[type_block].get("rich_text", [])
            for t in rich_text:
                texte += t.get("plain_text", "") + "\n"
        elif type_block == "child_page":
            sous_pages.append(block["id"])
        elif type_block == "child_database":
            sous_pages.extend(get_lignes_database(block["id"]))
    return texte.strip(), sous_pages

def get_lignes_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=HEADERS, json={"page_size": 100})
    resultats = response.json().get("results", [])
    return [r["id"] for r in resultats]

def get_last_edited_stocke(page_id):
    result = supabase.table(TABLE).select("last_edited_time").eq("page_id", page_id).limit(1).execute()
    if result.data:
        return result.data[0]["last_edited_time"]
    return None

def creer_embedding(texte):
    response = client_google.models.embed_content(
        model="gemini-embedding-001",
        contents=texte
    )
    return response.embeddings[0].values

def decouper_texte(texte, taille=500):
    mots = texte.split()
    return [" ".join(mots[i:i + taille]) for i in range(0, len(mots), taille)] or [""]

def indexer_page(page_id, nom_page, last_edited_time):
    supabase.table(TABLE).delete().eq("page_id", page_id).execute()
    texte, _ = get_texte_et_sous_pages(page_id)
    if not texte:
        print(f"  -> '{nom_page}' vide, rien à indexer.")
        return
    morceaux = decouper_texte(texte)
    for morceau in morceaux:
        embedding = creer_embedding(morceau)
        supabase.table(TABLE).insert({
            "page_id": page_id,
            "nom_page": nom_page,
            "contenu": morceau,
            "embedding": embedding,
            "last_edited_time": last_edited_time
        }).execute()
    print(f"  -> '{nom_page}' indexée ({len(morceaux)} morceaux).")

def parcourir_et_indexer(page_id, profondeur=0):
    nom_page, last_edited_actuel = get_page_metadata(page_id)
    prefixe = "  " * profondeur
    last_edited_stocke = get_last_edited_stocke(page_id)
    if last_edited_stocke == last_edited_actuel:
        print(f"{prefixe}'{nom_page}' inchangée, ignorée.")
    else:
        print(f"{prefixe}'{nom_page}' modifiée ou nouvelle, indexation...")
        indexer_page(page_id, nom_page, last_edited_actuel)
    _, sous_pages = get_texte_et_sous_pages(page_id)
    for sous_page_id in sous_pages:
        parcourir_et_indexer(sous_page_id, profondeur + 1)

if __name__ == "__main__":
    print("Indexation base de connaissance Notion -> Supabase...")
    parcourir_et_indexer(NOTION_PAGE_KNOWLEDGE_ID)
    print("Terminé.")
