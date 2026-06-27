"""
Face agent — interface Streamlit pour les employés de l'opérateur télécom.
- Même style que la face client (bulles, streaming, point rouge)
- Sidebar pour actions admin
- Validation des articles en attente
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
NOTION_PAGE_KNOWLEDGE_ID = get_secret("NOTION_PAGE_KNOWLEDGE_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET)
MODEL = "meta-llama/llama-3.3-70b-instruct"

st.set_page_config(page_title="Espace Agent", page_icon="🛠️", layout="wide")

st.markdown("""
    <style>
    .message-user {
        background-color: rgba(100, 100, 100, 0.15);
        padding: 12px 18px;
        border-radius: 18px;
        margin: 8px 0;
        display: inline-block;
        max-width: 75%;
        float: right;
        text-align: right;
        border: 1px solid rgba(128,128,128,0.2);
    }
    .message-assistant {
        padding: 10px 4px;
        margin: 8px 0;
        max-width: 85%;
        line-height: 1.7;
    }
    .clearfix { clear: both; }

    .point-rouge {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #e00;
        border-radius: 50%;
        margin-left: 4px;
        vertical-align: middle;
        animation: pulse 0.9s infinite;
    }
    @keyframes pulse {
        0%   { opacity: 1;   transform: scale(1); }
        50%  { opacity: 0.3; transform: scale(0.7); }
        100% { opacity: 1;   transform: scale(1); }
    }
    </style>
""", unsafe_allow_html=True)

# --- Session state ---
if "messages_agent" not in st.session_state:
    st.session_state.messages_agent = []

# --- Sidebar ---
with st.sidebar:
    st.title("🛠️ Espace Agent")
    st.markdown("---")

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

    st.subheader("Comportement et capacités")
    if st.button("🔁 Forcer le rechargement", use_container_width=True):
        with st.spinner("Rechargement..."):
            try:
                forcer_rechargement()
                st.success("Comportement et capacités rechargés.")
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.markdown("---")

    st.subheader("Articles à valider")
    pending = supabase.table("pending_articles").select("*").eq("statut", "brouillon").execute()
    nb_pending = len(pending.data) if pending.data else 0
    st.metric("En attente", nb_pending)

# --- Tabs ---
tab_chat, tab_validation = st.tabs(["💬 Chat", "✅ Validation articles"])

# -----------------------------------------------------------------------
# TAB 1 — Chat agent
# -----------------------------------------------------------------------
with tab_chat:

    if len(st.session_state.messages_agent) == 0:
        st.title("🛠️ Espace Agent")
        st.caption("Gérez la base de connaissance en chattant.")

    # Affichage historique
    for message in st.session_state.messages_agent:
        if message["role"] == "user":
            st.markdown(
                f'<div class="message-user">{message["content"]}</div><div class="clearfix"></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="message-assistant">{message["content"]}</div><div class="clearfix"></div>',
                unsafe_allow_html=True
            )

    if prompt := st.chat_input("Votre instruction..."):
        st.session_state.messages_agent.append({"role": "user", "content": prompt})
        st.markdown(
            f'<div class="message-user">{prompt}</div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )

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

        placeholder = st.empty()
        reponse_complete = ""
        buffer = ""
        est_json = False
        premier_chunk = True

        # Point rouge pendant le chargement
        placeholder.markdown(
            '<div class="message-assistant"><span class="point-rouge"></span></div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"model": MODEL, "messages": messages, "stream": True},
            stream=True
        )

        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    token = chunk["choices"][0]["delta"].get("content", "")
                    if not token:
                        continue

                    buffer += token

                    if premier_chunk:
                        premier_chunk = False
                        if buffer.strip().startswith("{"):
                            est_json = True

                    if not est_json:
                        reponse_complete += token
                        placeholder.markdown(
                            f'<div class="message-assistant">{reponse_complete}<span class="point-rouge"></span></div><div class="clearfix"></div>',
                            unsafe_allow_html=True
                        )

                except (json.JSONDecodeError, KeyError):
                    continue

        # Traitement final
        if est_json:
            try:
                parsed = json.loads(buffer.strip())
                if parsed.get("type") == "article":
                    supabase.table("pending_articles").insert({
                        "categorie": parsed.get("categorie"),
                        "question": parsed.get("question"),
                        "reponse": parsed.get("reponse"),
                        "statut": "brouillon",
                        "source": "agent"
                    }).execute()
                    reponse_complete = f"✅ Article créé en brouillon.\n\n**Question :** {parsed.get('question')}\n\n**Réponse :** {parsed.get('reponse')}\n\nVa dans l'onglet **Validation articles** pour le publier."
                else:
                    reponse_complete = buffer.strip()
            except json.JSONDecodeError:
                reponse_complete = buffer.strip()

        placeholder.markdown(
            f'<div class="message-assistant">{reponse_complete}</div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )

        st.session_state.messages_agent.append({
            "role": "assistant",
            "content": reponse_complete
        })

# -----------------------------------------------------------------------
# TAB 2 — Validation articles
# -----------------------------------------------------------------------
with tab_validation:
    st.markdown("### Articles en attente de validation")
    st.caption("Articles générés automatiquement ou créés via le chat agent.")

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
