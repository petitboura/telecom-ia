"""
Face agent — interface Streamlit pour les employés de l'opérateur télécom.
- Modifier la base de connaissance en chattant
- Publier et synchroniser via bouton
- Valider les articles générés automatiquement depuis les conversations ratées
- Forcer le rechargement du comportement et des capacités
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'indexers'))

import json
import streamlit as st
import requests
from configuration import get_behavior, forcer_rechargement
from supabase import create_client

def get_secret(key):
    try:
        return st.secrets[key]
    except:
        return os.environ.get(key)

OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_SECRET = get_secret("SUPABASE_SECRET")
NOTION_TOKEN = get_secret("NOTION_TOKEN")
NOTION_PAGE_KNOWLEDGE_ID = get_secret("NOTION_PAGE_KNOWLEDGE_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET)
MODEL = "meta-llama/llama-3.1-8b-instruct"

st.set_page_config(page_title="Espace Agent", page_icon="🛠️", layout="wide")

# --- Session state ---
if "messages_agent" not in st.session_state:
    st.session_state.messages_agent = []

# --- Sidebar ---
with st.sidebar:
    st.title("🛠️ Espace Agent")
    st.markdown("---")

    # Publier et synchroniser la base de connaissance
    st.subheader("Base de connaissance")
    if st.button("🔄 Publier et synchroniser", type="primary", use_container_width=True):
        with st.spinner("Synchronisation en cours..."):
            try:
                from index_knowledge import parcourir_et_indexer
                parcourir_et_indexer(NOTION_PAGE_KNOWLEDGE_ID)
                st.success("Base de connaissance synchronisée.")
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.markdown("---")

    # Forcer rechargement comportement et capacités
    st.subheader("Comportement et capacités")
    if st.button("🔁 Forcer le rechargement", use_container_width=True):
        with st.spinner("Rechargement..."):
            try:
                forcer_rechargement()
                st.success("Comportement et capacités rechargés.")
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.markdown("---")

    # Articles en attente de validation
    st.subheader("Articles à valider")
    pending = supabase.table("pending_articles").select("*").execute()
    nb_pending = len(pending.data) if pending.data else 0
    st.metric("En attente", nb_pending)

# --- Tabs ---
tab_chat, tab_validation = st.tabs(["💬 Chat agent", "✅ Validation articles"])

# -----------------------------------------------------------------------
# TAB 1 — Chat agent
# -----------------------------------------------------------------------
with tab_chat:
    st.markdown("### Gérez la base de connaissance en chattant")
    st.caption("Exemples : 'Ajoute un article sur la résiliation', 'Modifie le délai de portabilité à 5 jours', 'Montre-moi les articles sur la facturation'")

    # Affichage historique
    for message in st.session_state.messages_agent:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])

    if prompt := st.chat_input("Votre instruction..."):
        st.session_state.messages_agent.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        # System prompt agent
        system_agent = f"""Tu es un assistant interne pour les agents d'un opérateur télécom.
Tu gères la base de connaissance de l'IA client.

Tu peux :
- Ajouter un article : créer une nouvelle entrée dans la base
- Modifier un article : mettre à jour une entrée existante
- Archiver un article : le marquer comme obsolète
- Lister les articles : montrer ce qui existe dans une catégorie
- Répondre à une question sur la base de connaissance existante

Quand tu dois créer ou modifier un article, retourne un JSON avec ce format exact sans texte autour :
{{
  "type": "article",
  "action": "creer" ou "modifier" ou "archiver",
  "categorie": "la catégorie",
  "question": "la question",
  "reponse": "la réponse complète",
  "statut": "brouillon"
}}

Sinon réponds normalement en texte.

Comportement actuel de l'IA client :
{get_behavior()}"""

        messages = [{"role": "system", "content": system_agent}]
        messages += st.session_state.messages_agent[:-1]
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"model": MODEL, "messages": messages, "stream": False}
        )

        data = response.json()
        reponse = data["choices"][0]["message"]["content"].strip()

        # Détecter si c'est un article à créer
        if reponse.startswith("{"):
            try:
                parsed = json.loads(reponse)
                if parsed.get("type") == "article":
                    supabase.table("pending_articles").insert({
                        "categorie": parsed.get("categorie"),
                        "question": parsed.get("question"),
                        "reponse": parsed.get("reponse"),
                        "statut": "brouillon",
                        "source": "agent"
                    }).execute()
                    reponse_affichee = f"✅ Article créé en brouillon.\n\n**Question :** {parsed.get('question')}\n\n**Réponse :** {parsed.get('reponse')}\n\nVa dans l'onglet **Validation articles** pour le publier."
                else:
                    reponse_affichee = reponse
            except json.JSONDecodeError:
                reponse_affichee = reponse
        else:
            reponse_affichee = reponse

        st.chat_message("assistant").write(reponse_affichee)
        st.session_state.messages_agent.append({
            "role": "assistant",
            "content": reponse_affichee
        })

# -----------------------------------------------------------------------
# TAB 2 — Validation articles
# -----------------------------------------------------------------------
with tab_validation:
    st.markdown("### Articles en attente de validation")
    st.caption("Ces articles ont été générés automatiquement depuis des conversations ratées ou créés via le chat agent.")

    pending = supabase.table("pending_articles").select("*").eq("statut", "brouillon").execute()

    if not pending.data:
        st.info("Aucun article en attente.")
    else:
        for article in pending.data:
            with st.expander(f"📄 {article.get('question', 'Sans titre')} — {article.get('categorie', '')}"):
                st.markdown(f"**Catégorie :** {article.get('categorie')}")
                st.markdown(f"**Question :** {article.get('question')}")
                st.markdown(f"**Réponse :** {article.get('reponse')}")
                st.markdown(f"**Source :** {article.get('source', 'inconnue')}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Publier", key=f"pub_{article['id']}"):
                        supabase.table("pending_articles").update(
                            {"statut": "publié"}
                        ).eq("id", article["id"]).execute()
                        st.success("Article publié. Lance une synchronisation pour l'activer.")
                        st.rerun()
                with col2:
                    if st.button("🗑️ Rejeter", key=f"rej_{article['id']}"):
                        supabase.table("pending_articles").delete().eq("id", article["id"]).execute()
                        st.warning("Article rejeté.")
                        st.rerun()
