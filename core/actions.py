"""
Registre générique des actions que l'IA peut déclencher.
Pour ajouter une nouvelle action : ajouter une ligne dans le registre.
Le backend exécute toujours via ce fichier, jamais directement.
"""

import os


def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except:
        return os.environ.get(key)


# ---------------------------------------------------------------------------
# Handlers — une fonction par action
# Chaque fonction reçoit un dict params et retourne un dict résultat
# ---------------------------------------------------------------------------

def activer_roaming(params):
    # TODO : connecter à l'API télécom
    return {"statut": "succès", "message": "Roaming activé sur votre ligne."}


def desactiver_roaming(params):
    # TODO : connecter à l'API télécom
    return {"statut": "succès", "message": "Roaming désactivé sur votre ligne."}


def consulter_facture(params):
    # TODO : connecter à l'API facturation
    return {"statut": "succès", "message": "Votre dernière facture est de 29.99 DT."}


def consulter_consommation(params):
    # TODO : connecter à l'API facturation
    return {"statut": "succès", "message": "Vous avez consommé 12 Go sur 20 Go ce mois."}


def creer_ticket(params):
    # TODO : connecter à l'API ticketing (ServiceNow, Jira, etc.)
    return {"statut": "succès", "message": "Votre ticket a été créé. Référence : TK-00123."}


def verifier_panne(params):
    # TODO : connecter à l'API réseau
    return {"statut": "succès", "message": "Aucune panne signalée dans votre zone."}


def reinitialiser_mot_de_passe(params):
    # TODO : connecter au système d'authentification
    return {"statut": "succès", "message": "Un email de réinitialisation vous a été envoyé."}


def transferer_agent(params):
    return {"statut": "transfert", "message": "Je vous transfère vers un agent disponible."}


# ---------------------------------------------------------------------------
# Registre — ajouter une ligne ici pour chaque nouvelle action
# ---------------------------------------------------------------------------

REGISTRE = {
    "activer_roaming": activer_roaming,
    "desactiver_roaming": desactiver_roaming,
    "consulter_facture": consulter_facture,
    "consulter_consommation": consulter_consommation,
    "creer_ticket": creer_ticket,
    "verifier_panne": verifier_panne,
    "reinitialiser_mot_de_passe": reinitialiser_mot_de_passe,
    "transferer_agent": transferer_agent,
}


# ---------------------------------------------------------------------------
# Point d'entrée unique
# ---------------------------------------------------------------------------

def executer_action(action, params):
    handler = REGISTRE.get(action)
    if not handler:
        return {"statut": "erreur", "message": f"Action '{action}' inconnue."}
    try:
        return handler(params)
    except Exception as e:
        return {"statut": "erreur", "message": str(e)}
