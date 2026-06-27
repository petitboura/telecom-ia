"""
Face client — interface Streamlit pour les clients de l'opérateur télécom.
- Répond aux questions depuis la base de connaissance
- Streaming token par token avec point rouge clignotant
- Détecte les actions et affiche un bouton de confirmation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

import streamlit as st
from main import chat
from actions import executer_action

st.set_page_config(page_title="Support Client", page_icon="📞", layout="centered")

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
if "messages" not in st.session_state:
    st.session_state.messages = []

if "action_en_attente" not in st.session_state:
    st.session_state.action_en_attente = None

if "ia_a_echoue" not in st.session_state:
    st.session_state.ia_a_echoue = False

# --- En-tête ---
if len(st.session_state.messages) == 0:
    st.title("📞 Support Client")
    st.caption("Bonjour, comment puis-je vous aider ?")

# --- Affichage de l'historique ---
for message in st.session_state.messages:
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
elif prompt := st.chat_input("Posez votre question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(
        f'<div class="message-user">{prompt}</div><div class="clearfix"></div>',
        unsafe_allow_html=True
    )

    historique = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ]

    placeholder = st.empty()
    reponse_complete = ""
    action_detectee = None

    # Afficher le point rouge pendant le chargement
    placeholder.markdown(
        '<div class="message-assistant"><span class="point-rouge"></span></div><div class="clearfix"></div>',
        unsafe_allow_html=True
    )

    for token in chat(prompt, historique):
        # Si c'est un dict, c'est une action
        if isinstance(token, dict):
            action_detectee = token
            break
        reponse_complete += token
        # Streaming token par token avec point rouge à la fin
        placeholder.markdown(
            f'<div class="message-assistant">{reponse_complete}<span class="point-rouge"></span></div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )

    if action_detectee:
        placeholder.empty()
        st.session_state.action_en_attente = action_detectee
        st.rerun()
    else:
        # Réponse finale sans point rouge
        placeholder.markdown(
            f'<div class="message-assistant">{reponse_complete}</div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )
        st.session_state.messages.append({
            "role": "assistant",
            "content": reponse_complete
        })

        # Marquer comme échec si l'IA dit qu'elle ne sait pas
        mots_echec = ["je ne sais pas", "je n'ai pas", "je ne peux pas répondre", "contactez un agent"]
        if any(mot in reponse_complete.lower() for mot in mots_echec):
            st.session_state.ia_a_echoue = True
