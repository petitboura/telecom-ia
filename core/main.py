import os
import logging
from groq import Groq
from google import genai
from google.genai import types
from configuration import get_behavior
from retriever import chercher_knowledge

logging.basicConfig(level=logging.INFO)

def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.environ.get(key)

GROQ_PRIMARY = "openai/gpt-oss-120b"
GOOGLE_MODEL = "gemini-2.5-flash"
GROQ_FALLBACKS = [
    "qwen/qwen3.6-27b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.3-70b-versatile",
]
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

    client_groq = Groq(api_key=get_secret("GROQ_API_KEY"))

    # 1. GPT-OSS 120B
    try:
        completion = client_groq.chat.completions.create(
            model=GROQ_PRIMARY,
            messages=messages,
            max_completion_tokens=1024,
            stream=True,
            timeout=120
        )
        for chunk in completion:
            token = chunk.choices[0].delta.content or ""
            if token:
                yield token
        logging.info(f"Réponse via GROQ: {GROQ_PRIMARY}")
        return
    except Exception as e:
        if "timeout" not in str(e).lower():
            logging.error(f"ERREUR GROQ {GROQ_PRIMARY}: {e}")

    # 2. Gemini 2.5 Flash
    try:
        client_google = genai.Client(api_key=get_secret("GOOGLE_API_KEY"))
        gemini_messages = [
            {"role": "user" if m["role"] != "assistant" else "model", "parts": [{"text": m["content"]}]}
            for m in messages if m["role"] != "system"
        ]
        response = client_google.models.generate_content_stream(
            model=GOOGLE_MODEL,
            contents=gemini_messages,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=1024
            )
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
        logging.info("Réponse via GEMINI")
        return
    except Exception as e:
        logging.error(f"ERREUR GEMINI: {e}")

    # 3-6. Fallbacks Groq
    for model in GROQ_FALLBACKS:
        try:
            completion = client_groq.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=1024,
                stream=True,
                timeout=120,
                reasoning_effort="none"
            )
            for chunk in completion:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield token
            logging.info(f"Réponse via GROQ fallback: {model}")
            return
        except Exception as e:
            if "timeout" not in str(e).lower():
                logging.error(f"ERREUR GROQ {model}: {e}")
            continue

    yield MESSAGE_ERREUR
