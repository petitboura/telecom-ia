"""
Face client — interface Streamlit pour les clients de l'opérateur télécom.
Style : identique au coach maths — bulles à droite, Lora pour l'assistant, point rouge animé.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

import html
import streamlit as st
from main import chat

st.set_page_config(page_title="Support Client", page_icon="📞", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;500;600&display=swap');

    /* Masquer tous les éléments natifs du chat Streamlit */
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

    /* Bulle utilisateur — droite */
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

    /* Réponse assistant — gauche, police Lora */
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
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- En-tête ---
if len(st.session_state.messages) == 0:
    st.title("📞 Support Client")
    st.caption("Bonjour, comment puis-je vous aider ?")

# --- Affichage historique ---
for message in st.session_state.messages:
    contenu = html.escape(message["content"])
    if message["role"] == "user":
        st.markdown(
            f'<div class="message-user">{contenu}</div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="message-assistant">{contenu}</div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )

# --- Input client ---
if prompt := st.chat_input("Posez votre question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(
        f'<div class="message-user">{html.escape(prompt)}</div><div class="clearfix"></div>',
        unsafe_allow_html=True
    )

    historique = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ]

    reponse_complete = ""

    placeholder = st.empty()
    placeholder.markdown(
        '<div class="message-assistant"><span class="point-rouge"></span></div><div class="clearfix"></div>',
        unsafe_allow_html=True
    )

    for token in chat(prompt, historique):
        reponse_complete += token
        placeholder.markdown(
            f'<div class="message-assistant">{html.escape(reponse_complete)}<span class="point-rouge"></span></div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )

    placeholder.markdown(
        f'<div class="message-assistant">{html.escape(reponse_complete)}</div><div class="clearfix"></div>',
        unsafe_allow_html=True
    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": reponse_complete
    })
