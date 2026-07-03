"""
Face client — interface Streamlit pour les clients de l'opérateur télécom.
Style : identique au coach maths — bulles à droite, Lora pour l'assistant, point rouge animé.
"""

import sys
import os
import re
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

import html
import streamlit as st
import streamlit.components.v1 as components
from main import chat

st.set_page_config(page_title="Support Client", page_icon="📞", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    /* ── Couleurs Ooredoo ──────────────────────────────────────────
       Rouge principal : #D40000
       Blanc          : #FFFFFF
       Gris foncé     : #494848
       Gris clair bg  : #F5F5F5
    ──────────────────────────────────────────────────────────────── */

    /* Fond général */
    .stApp {
        background-color: #F5F5F5;
        font-family: 'Inter', sans-serif;
    }

    /* Header / titre */
    h1 {
        color: #D40000 !important;
        font-family: 'Lora', serif;
        font-weight: 600 !important;
    }

    /* Sous-titre */
    .stCaption {
        color: #494848 !important;
    }

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

    /* Bulle utilisateur — droite, rouge Ooredoo */
    .message-user {
        background-color: #D40000;
        color: #FFFFFF;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        display: inline-block;
        max-width: 75%;
        float: right;
        text-align: right;
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
    }

    /* Réponse assistant — gauche, blanc avec bordure subtile */
    .message-assistant {
        font-family: 'Lora', serif;
        color: #494848;
        background-color: #FFFFFF;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 85%;
        line-height: 1.7;
        font-size: 1.05rem;
        border-left: 3px solid #D40000;
        box-shadow: 0 2px 6px rgba(0,0,0,0.07);
    }

    .clearfix { clear: both; }

    /* Zone de saisie */
.    stChatInput textarea {
        border: 2px solid #D40000 !important;
        border-radius: 12px !important;
        font-family: 'Inter', sans-serif !important;
        outline: none !important;
}
.stChatInput textarea:focus {
    box-shadow: none !important;
    outline: none !important;
}

    /* Bouton envoi */
    .stChatInput button {
        background-color: #D40000 !important;
        border-radius: 8px !important;
    }
    .stChatInput button:hover {
        background-color: #aa0000 !important;
    }

    /* Point rouge animé (typing indicator) */
    .point-rouge {
        display: inline-block;
        width: 9px;
        height: 9px;
        background-color: #D40000;
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


def _normaliser_latex(texte):
    """
    Le moteur Markdown de Streamlit traite `\\(`, `\\)`, `\\[`, `\\]` comme des
    caractères échappés et supprime le backslash avant même que MathJax ne
    voie le texte. On convertit donc ces délimiteurs LaTeX vers `$ $` et
    `$$ $$`, que Markdown laisse intacts (le `$` n'a pas de sens spécial
    pour lui).
    """
    texte = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', texte, flags=re.DOTALL)
    texte = re.sub(r'\\\((.*?)\\\)', r'$\1$', texte, flags=re.DOTALL)
    return texte


def _typeset_mathjax():
    """
    Les <script> injectés via st.markdown(unsafe_allow_html=True) ne
    s'exécutent JAMAIS (limitation du DOM : les scripts insérés via
    innerHTML ne sont pas exécutés par le navigateur). On passe donc par
    un composant Streamlit (rendu dans une vraie page HTML, où les
    scripts s'exécutent normalement) qui va lui-même injecter MathJax
    dans la page PARENTE (window.parent), puis demander le rendu des
    formules déjà présentes dans le DOM.
    """
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            const win = window.parent;

            function typeset() {
                if (win.MathJax && win.MathJax.typesetPromise) {
                    win.MathJax.typesetPromise();
                }
            }

            if (!win.MathJax) {
                win.MathJax = {
                    tex: {
                        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
                    },
                    svg: { fontCache: 'global' },
                    startup: {
                        ready: function() {
                            MathJax.startup.defaultReady();
                            MathJax.startup.promise.then(typeset);
                        }
                    }
                };
                const script = doc.createElement('script');
                script.src = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js";
                script.async = true;
                doc.head.appendChild(script);
            } else {
                typeset();
            }
        })();
        </script>
        """,
        height=0,
        width=0,
    )


# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- En-tête ---
if len(st.session_state.messages) == 0:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:4px;">
            <span style="font-size:2rem;">📞</span>
            <span style="font-size:1.8rem; font-weight:700; color:#D40000; font-family:'Inter',sans-serif;">
                Support Client <span style="color:#494848;">Ooredoo</span>
            </span>
        </div>
        <p style="color:#494848; font-family:'Inter',sans-serif; margin-top:0;">
            Bonjour ! Comment puis-je vous aider aujourd'hui ?
        </p>
        <hr style="border:none; border-top:2px solid #D40000; margin-bottom:16px;">
    """, unsafe_allow_html=True)

# --- Affichage historique ---
for message in st.session_state.messages:
    if message["role"] == "user":
        contenu = html.escape(message["content"])
        st.markdown(
            f'<div class="message-user">{contenu}</div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )
    else:
        contenu = _normaliser_latex(html.escape(message["content"]))
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
        contenu_affiche = _normaliser_latex(html.escape(reponse_complete))
        placeholder.markdown(
            f'<div class="message-assistant">{contenu_affiche}<span class="point-rouge"></span></div><div class="clearfix"></div>',
            unsafe_allow_html=True
        )

    contenu_affiche = _normaliser_latex(html.escape(reponse_complete))
    placeholder.markdown(
        f'<div class="message-assistant">{contenu_affiche}</div><div class="clearfix"></div>',
        unsafe_allow_html=True
    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": reponse_complete
    })

# Toujours en dernier : (re)déclenche le rendu MathJax sur tout ce qui
# vient d'être affiché (historique + nouvelle réponse le cas échéant).
_typeset_mathjax()
