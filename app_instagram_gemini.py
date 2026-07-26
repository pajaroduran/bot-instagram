"""
Bot de Instagram (Mensajes Directos) + Gemini (100% gratuito)
--------------------------------------------------------------
Responde automáticamente todos los DMs de Instagram usando Google Gemini
(tiene un nivel gratuito, no requiere tarjeta de crédito para empezar).

Requisitos:
- Cuenta de Instagram profesional vinculada a una Página de Facebook (ya lo tenés)
- App en Meta Developers con el caso de uso de Instagram configurado (ya lo tenés)
- API key GRATIS de Google Gemini (https://aistudio.google.com/apikey)
- Alojar esto en un servicio gratuito como Render

Variables de entorno necesarias:
- IG_TOKEN            -> Tu token de acceso de Instagram (el que ya generaste)
- IG_BUSINESS_ID       -> 17841449642430261 (el que ya tenés)
- VERIFY_TOKEN         -> Un texto que vos inventes, para verificar el webhook
- GEMINI_API_KEY       -> Tu API key gratuita de Google Gemini
"""

import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

IG_TOKEN = os.environ.get("IG_TOKEN")
IG_BUSINESS_ID = os.environ.get("IG_BUSINESS_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mi_token_secreto")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
modelo = genai.GenerativeModel("gemini-flash-latest")

# Memoria simple en RAM por usuario (se pierde si el server reinicia)
conversaciones = {}


@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    """Meta llama a este endpoint una vez para verificar que el webhook es tuyo."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Token de verificación inválido", 403


@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    """Meta envía aquí cada DM nuevo que llega a tu cuenta de Instagram."""
    data = request.get_json()

    try:
        for entry in data.get("entry", []):
            for evento in entry.get("messaging", []):
                remitente = evento["sender"]["id"]

                # Ignorar eventos que no traen texto (ej. "seen", reacciones, etc.)
                if "message" not in evento or "text" not in evento["message"]:
                    continue

                # Evitar responderse a sí mismo (eco de mensajes enviados por la propia cuenta)
                if evento["message"].get("is_echo"):
                    continue

                texto_usuario = evento["message"]["text"]

                respuesta = preguntar_a_gemini(remitente, texto_usuario)
                enviar_instagram(remitente, respuesta)

    except (KeyError, IndexError):
        pass

    return jsonify({"status": "ok"}), 200


def preguntar_a_gemini(usuario_id, texto_usuario):
    """Envía el mensaje del usuario a Gemini y guarda historial básico."""
    historial = conversaciones.get(usuario_id, [])
    historial.append({"role": "user", "parts": [texto_usuario]})

    chat = modelo.start_chat(history=historial[:-1])
    respuesta = chat.send_message(
        texto_usuario,
        generation_config={"max_output_tokens": 300},
    )

    texto_respuesta = respuesta.text
    historial.append({"role": "model", "parts": [texto_respuesta]})

    # Limitar historial para no gastar de más
    conversaciones[usuario_id] = historial[-10:]

    return texto_respuesta


def enviar_instagram(destinatario_id, mensaje):
    """Envía un mensaje de vuelta al usuario usando la API de Instagram Messaging."""
    url = f"https://graph.facebook.com/v20.0/{IG_BUSINESS_ID}/messages"
    headers = {
        "Authorization": f"Bearer {IG_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "recipient": {"id": destinatario_id},
        "message": {"text": mensaje},
    }
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()


@app.route("/", methods=["GET"])
def home():
    return "Bot de Instagram + Gemini funcionando ✅"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
