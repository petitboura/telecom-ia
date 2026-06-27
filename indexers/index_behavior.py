"""
Récupère la Page 2 Notion (Comportement) et la stocke dans Supabase.
Table cible : behavior
Pas de vectorisation — texte brut chargé comme system prompt.
Lancé via GitHub Action hebdomadaire.
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
NOTION_PAGE_BEHAVIOR_ID = get_secret("NOTION_PAGE_BEHAVIOR_ID")
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
                          "heading_1", "heading_2", "heading_3",
                          "toggle", "quote", "callout"]:
            rich_text = block[type_block].get("rich_text", [])
            for t in rich_text:
                texte += t.get("plain_text", "") + "\n"
        elif type_block == "code":
            rich_text = block[type_block].get("rich_text", [])
            for t in rich_text:
                texte += t.get("plain_text", "") + "\n"

    return texte.strip()


def get_last_edited(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    response = requests.get(url, headers=HEADERS)
    return response.json().get("last_edited_time")


if __name__ == "__main__":
    print("Chargement du comportement Notion -> Supabase...")

    last_edited = get_last_edited(NOTION_PAGE_BEHAVIOR_ID)
    texte = get_texte_page(NOTION_PAGE_BEHAVIOR_ID)

    if not texte:
        print("Page comportement vide, rien à faire.")
    else:
        # On supprime l'ancienne version et on insère la nouvelle
        supabase.table("behavior").delete().neq("id", 0).execute()
        supabase.table("behavior").insert({
            "contenu": texte,
            "last_edited_time": last_edited
        }).execute()
        print("Comportement mis à jour dans Supabase.")
