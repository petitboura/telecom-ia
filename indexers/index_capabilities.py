"""
Récupère la Page 3 Notion (Capacités) et la stocke dans Supabase.
Table cible : capabilities
Pas de vectorisation — texte structuré stocké tel quel.
Lancé via GitHub Action hebdomadaire, en même temps que index_behavior.py.
"""

import os
import requests
from supabase import create_client


def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except:
        return os.environ.get(key)


NOTION_TOKEN = get_secret("NOTION_TOKEN")
NOTION_PAGE_CAPABILITIES_ID = get_secret("NOTION_PAGE_CAPABILITIES_ID")
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_SECRET = get_secret("SUPABASE_SECRET")

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28"
}


def get_texte_page(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
    response = requests.get(url, headers=HEADERS)
    blocks = response.json().get("results", [])

    texte = ""
    for block in blocks:
        type_block = block.get("type")
        if type_block in ["paragraph", "bulleted_list_item", "numbered_list_item",
                          "heading_1", "heading_2", "heading_3"]:
            rich_text = block[type_block].get("rich_text", [])
            for t in rich_text:
                texte += t.get("plain_text", "") + "\n"

    return texte.strip()


def get_last_edited(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    response = requests.get(url, headers=HEADERS)
    return response.json().get("last_edited_time")


if __name__ == "__main__":
    print("Chargement des capacités Notion -> Supabase...")

    last_edited = get_last_edited(NOTION_PAGE_CAPABILITIES_ID)
    texte = get_texte_page(NOTION_PAGE_CAPABILITIES_ID)

    if not texte:
        print("Page capacités vide, rien à faire.")
    else:
        # On supprime l'ancienne version et on insère la nouvelle
        supabase.table("capabilities").delete().neq("id", 0).execute()
        supabase.table("capabilities").insert({
            "contenu": texte,
            "last_edited_time": last_edited
        }).execute()
        print("Capacités mises à jour dans Supabase.")
