"""
Moteur principal de chat — face client uniquement.
- Charge le comportement depuis configuration.py
- Cherche dans la base de connaissance via retriever.py
- Stream la réponse texte token par token, dès qu'elle arrive
"""
import os
import logging
from groq import Groq
from configuration import get_behavior
from retriever import chercher_knowledge

def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.environ.get(key)

MODEL = "openai/gpt-oss-120b"
MESSAGE_ERREUR = "Désolé, je rencontre un souci technique pour répondre. Merci de réessayer dans un instant."

def chat(message_utilisateur, historique=None):
    if historique is None:
        historique = []

    behavior = get_behavior()
    knowledge = chercher_knowledge(message_utilisateur)
    contexte_knowledge = "\n".join(knowledge)
    system_prompt = f"{behavior}\n\n{contexte_knowledge}" if contexte_knowledge else behavior

    messages = [{"role": "system", "content": system_prompt}]
    messages += historique
    messages.append({"role": "user", "content": message_utilisateur})

    try:
        client = Groq(api_key=get_secret("GROQ_API_KEY"))
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_completion_tokens=1024,
            stream=True
        )
        for chunk in completion:
            token = chunk.choices[0].delta.content or ""
            if token:
                yield token
    except Exception as e:
        logging.error(f"ERREUR API: {e}")
        yield MESSAGE_ERREUR
