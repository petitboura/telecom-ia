"""
Moteur principal de chat — face client uniquement.
- Charge le comportement depuis configuration.py
- Cherche dans la base de connaissance via retriever.py
- Stream la réponse texte token par token, dès qu'elle arrive
"""

import os
import json
import requests
from configuration import get_behavior
from retriever import chercher_knowledge


def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.environ.get(key)


OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")
MODEL = "meta-llama/llama-3.1-8b-instruct"

MESSAGE_ERREUR = "Désolé, je rencontre un souci technique pour répondre. Merci de réessayer dans un instant."


def _appel_llm(messages):
    return requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": messages,
            "stream": True
        },
        stream=True,
        timeout=30
    )


def chat(message_utilisateur, historique=None):
    """
    Générateur principal côté client.
    Yield les tokens texte au fur et à mesure qu'ils arrivent du LLM (vrai streaming).
    """
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
        response = _appel_llm(messages)
        response.raise_for_status()
    except requests.RequestException:
        yield MESSAGE_ERREUR
        return

    try:
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                token = chunk["choices"][0]["delta"].get("content", "")
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
            if token:
                yield token
    except requests.RequestException:
        yield MESSAGE_ERREUR
