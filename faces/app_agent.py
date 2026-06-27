"""
Face agent — interface Streamlit pour les employés de l'opérateur télécom.
Style : identique à app_client.py — Lora, bulles à droite, point rouge animé.
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
from main import generer_articles_depuis_conversation

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
MODEL = "meta-llama/llama-3.3-70b-instruct"

st.set_page_config(page_title="Espace Agent", page_icon="🛠️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;500;600&display=swap');

    /* Masquer avatars Streamlit */
    [data-testid="chatAvatarIcon-user"],
    [data-testid="chatAvatarIcon-assistant"],
    [data-testid="stChatMessageAvatarContainer"] {
        display: none !important;
    }
    .stChatMessage {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    /* Bulle agent — droite */
    .message-user {
        background-color: rgba(100, 100, 100, 0.2);
        color: inherit;
        padding: 12px 18px;
        border-radius: 18px;
        margin: 8px 0;
        display: inline-block;
        max-width: 75%;
        float: right;
        text-align: right;
        border: 1px solid rgba(128,128,128,0.3);
    }

    /* Réponse IA — gauche, Lora */
    .message-assistant {
        font-family: 'Lora', serif;
        color: inherit;
        padding: 10px 4px;
        margin: 8px 0;
        max-width: 85%;
        line-height: 1.7;
    }

    .clearfix { clear: both; }

    /* Point rouge animé */
    .point-rouge {
        display: inline-block;
        width: 9px;
        height: 9px;
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
    pending_count = supabase.table("pending_articles").select("*").eq("statut", "brouillon").execute()
    nb_pending = len(pending_count.data) if pending_count.data else 0
    st.metric("En attente", nb_pending)

    st.markdown("---")

    st.subheader("Conversations en attente")
    conv_count = supabase.table("unanswered_questions").select("*").eq("statut", "en_attente").execute()
    nb_conv = len(conv_count.data) if conv_count.data else 0
    st.metric("En attente", nb_conv)

# --- Tabs ---
tab_chat, tab_conversations, tab_validation = st.tabs(["💬 Chat", "👤 Conversations en attente", "✅ Validation articles"])

# -----------------------------------------------------------------------
# TAB 1 — Chat agent
# -----------------------------------------------------------------------
with tab_chat:
    if len(st.session_state.messages_agent) == 0:
        st.title("🛠️ Espace Agent")
        st.caption("Gérez la base de connaissance en chattant.")

    # Champ de saisie en premier dans le code pour qu'il soit capté
    prompt = st.chat_input("Votre instruction...")

    # Affichage historique dans un conteneur scrollable
    chat_container = st.container()
    with chat_container:
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

    if prompt:
        st.session_state.messages_agent.append({"role": "user", "content": prompt})
        st.markdown(
            f'<div class="message-user">{prompt}</div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )

        system_agent = """Tu es un assistant interne Ooredoo.
Tu travailles avec les agents pour gérer la base de connaissance de l'IA client.
Tu réponds précisément à ce qu'on te demande, rien de plus.
Tu parles à un collègue, pas à un client — sois direct et efficace.

Quand tu dois créer ou modifier un article, retourne uniquement ce JSON sans texte autour :
{
  "type": "article",
  "action": "creer",
  "categorie": "la catégorie",
  "question": "la question",
  "reponse": "la réponse complète",
  "statut": "brouillon"
}"""

        messages = [{"role": "system", "content": system_agent}]
        messages += st.session_state.messages_agent[:-1]
        messages.append({"role": "user", "content": prompt})

        buffer = ""
        reponse_complete = ""
        est_json = False
        premier_chunk = True

        placeholder = st.empty()
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
# TAB 2 — Conversations en attente
# -----------------------------------------------------------------------
with tab_conversations:
    st.markdown("### Conversations clients en attente")
    st.caption("Le client n'a pas eu de réponse satisfaisante. Répondez directement ici.")

    conversations = supabase.table("unanswered_questions").select("*").eq("statut", "en_attente").order("created_at", desc=True).execute()

    if not conversations.data:
        st.info("Aucune conversation en attente.")
    else:
        for conv in conversations.data:
            with st.expander(f"💬 Conversation #{conv['id']} — {conv['created_at'][:16]}"):
                st.markdown("**Historique :**")
                st.text(conv["conversation"])
                st.markdown("---")

                reponse_agent = st.text_input(
                    "Votre réponse au client :",
                    key=f"reponse_{conv['id']}",
                    placeholder="Tapez votre réponse ici..."
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Envoyer et clore", key=f"send_{conv['id']}"):
                        if reponse_agent.strip():
                            conversation_complete = conv["conversation"] + f"\nAgent : {reponse_agent}"
                            supabase.table("unanswered_questions").update({
                                "reponse_agent": reponse_agent,
                                "statut": "traite",
                                "traite": True
                            }).eq("id", conv["id"]).execute()

                            with st.spinner("Analyse de la conversation..."):
                                articles = generer_articles_depuis_conversation(conversation_complete)
                                for article in articles.get("articles", []):
                                    supabase.table("pending_articles").insert({
                                        "categorie": article.get("categorie"),
                                        "question": article.get("question"),
                                        "reponse": article.get("reponse"),
                                        "statut": "brouillon",
                                        "source": "conversation"
                                    }).execute()

                            st.success(f"Réponse envoyée. {len(articles.get('articles', []))} article(s) générés pour validation.")
                            st.rerun()
                        else:
                            st.warning("Tapez une réponse avant d'envoyer.")
                with col2:
                    if st.button("🗑️ Ignorer", key=f"ignore_{conv['id']}"):
                        supabase.table("unanswered_questions").update({
                            "statut": "traite",
                            "traite": True
                        }).eq("id", conv["id"]).execute()
                        st.rerun()

# -----------------------------------------------------------------------
# TAB 3 — Validation articles
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
