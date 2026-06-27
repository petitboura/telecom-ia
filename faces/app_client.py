"""
Face client — interface Streamlit pour les clients de l'opérateur télécom.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

import streamlit as st
from main import chat
from actions import executer_action
from supabase import create_client
import json

def get_secret(key):
    try:
        return st.secrets[key]
    except:
        return os.environ.get(key)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_SECRET = get_secret("SUPABASE_SECRET")
supabase = create_client(SUPABASE_URL, SUPABASE_SECRET)

st.set_page_config(page_title="Support Client", page_icon="📞", layout="centered")

st.markdown("""
    <style>
    /* Cacher les avatars */
    [data-testid="chatAvatarIcon-user"],
    [data-testid="chatAvatarIcon-assistant"] {
        display: none !important;
    }
    /* Bulle utilisateur */
    [data-testid="chat-message-container"]:has([data-testid="chatAvatarIcon-user"]),
    div[class*="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
        display: flex;
        justify-content: flex-end;
    }
    .stChatMessage {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    div[data-testid="stChatMessageContent"] p {
        margin: 0;
    }
    /* Point rouge */
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
if "messages" not in st.session_state:
    st.session_state.messages = []
if "action_en_attente" not in st.session_state:
    st.session_state.action_en_attente = None
if "ia_a_echoue" not in st.session_state:
    st.session_state.ia_a_echoue = False
if "conversation_sauvegardee" not in st.session_state:
    st.session_state.conversation_sauvegardee = False

# --- En-tête ---
if len(st.session_state.messages) == 0:
    st.title("📞 Support Client")
    st.caption("Bonjour, comment puis-je vous aider ?")

# --- Affichage historique ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# --- Bouton contacter un agent ---
if st.session_state.ia_a_echoue and not st.session_state.conversation_sauvegardee:
    if st.button("👤 Contacter un agent", type="primary"):
        conversation_texte = "\n".join([
            f"{'Client' if m['role'] == 'user' else 'IA'} : {m['content']}"
            for m in st.session_state.messages
        ])
        supabase.table("unanswered_questions").insert({
            "conversation": conversation_texte,
            "statut": "en_attente",
            "traite": False
        }).execute()
        st.session_state.conversation_sauvegardee = True
        st.success("Un agent va vous répondre prochainement.")
        st.rerun()

# --- Bouton de confirmation d'action en attente ---
if st.session_state.action_en_attente:
    action_data = st.session_state.action_en_attente
    st.info(action_data["message"])
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button(action_data["bouton_label"], type="primary"):
            resultat = executer_action(action_data["action"], action_data.get("params", {}))
            st.session_state.messages.append({
                "role": "assistant",
                "content": resultat["message"]
            })
            st.session_state.action_en_attente = None
            st.rerun()
    with col2:
        if st.button("Annuler"):
            st.session_state.action_en_attente = None
            st.rerun()

# --- Input client ---
elif not st.session_state.conversation_sauvegardee:
    if prompt := st.chat_input("Posez votre question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        historique = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]

        reponse_complete = ""
        action_detectee = None

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown('<span class="point-rouge"></span>', unsafe_allow_html=True)

            for token in chat(prompt, historique):
                if isinstance(token, dict):
                    action_detectee = token
                    break
                reponse_complete += token
                placeholder.markdown(
                    f'{reponse_complete}<span class="point-rouge"></span>',
                    unsafe_allow_html=True
                )

            if not action_detectee:
                placeholder.write(reponse_complete)

        if action_detectee:
            st.session_state.action_en_attente = action_detectee
            st.rerun()
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": reponse_complete
            })
            mots_echec = ["je ne sais pas", "je n'ai pas", "je ne peux pas répondre", "contactez un agent"]
            if any(mot in reponse_complete.lower() for mot in mots_echec):
                st.session_state.ia_a_echoue = True
            st.rerun()
