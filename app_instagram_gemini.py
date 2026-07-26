"""
Bot de Instagram (Mensajes Directos) + Gemini (100% gratuito)
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

conversaciones = {}


@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Token de verificación inválido", 403


@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    data = request.get_json()
    print("PAYLOAD RECIBIDO:", data)  # línea temporal de depuración
    try:
        for entry in data.get("entry", []):
            for evento in entry.get("messaging", []):
                remitente = evento["sender"]["id"]
                if "message" not in evento or "text" not in evento["message"]:
                    continue
                if evento["message"].get("is_echo"):
                    continue
                texto_usuario = evento["message"]["text"]
                respuesta = preguntar_a_gemini(remitente, texto_usuario)
                enviar_instagram(remitente, respuesta)
    except (KeyError, IndexError) as e:
        print("ERROR AL PROCESAR:", e)

    return jsonify({"status": "ok"}), 200


def preguntar_a_gemini(usuario_id, texto_usuario):
    historial = conversaciones.get(usuario_id, [])
    historial.append({"role": "user", "parts": [texto_usuario]})
    chat = modelo.start_chat(history=historial[:-1])
    respuesta = chat.send_message(
        texto_usuario,
        generation_config={"max_output_tokens": 300},
    )
    texto_respuesta = respuesta.text
    historial.append({"role": "model", "parts": [texto_respuesta]})
    conversaciones[usuario_id] = historial[-10:]
    return texto_respuesta


def enviar_instagram(destinatario_id, mensaje):
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


@app.route("/privacy", methods=["GET"])
def privacy():
    return """
    <html><head><meta charset="UTF-8"><title>Política de Privacidad</title></head>
    <body style="font-family:Arial,sans-serif;max-width:700px;margin:40px auto;padding:0 20px;line-height:1.6;">
    <h1>Política de Privacidad</h1>
    <p>Última actualización: 26 de julio de 2026</p>
    <p>Esta política describe cómo el bot de mensajería automática de Instagram
    asociado a la cuenta @elpajaroduran maneja la información de los usuarios
    que interactúan con él.</p>
    <h2>Información que recopilamos</h2>
    <p>El bot procesa únicamente el contenido de los mensajes directos (DM)
    que los usuarios envían voluntariamente a la cuenta de Instagram, con el
    fin de generar una respuesta automática.</p>
    <h2>Uso de la información</h2>
    <p>Los mensajes se utilizan exclusivamente para generar una respuesta
    automática mediante inteligencia artificial. No se comparte, vende ni
    cede esta información a terceros.</p>
    <h2>Almacenamiento</h2>
    <p>El historial de conversación se guarda temporalmente en la memoria
    del servidor para dar contexto a la respuesta, y se elimina
    automáticamente cuando el servidor se reinicia.</p>
    <h2>Contacto</h2>
    <p>Ante cualquier consulta, podés escribir a la cuenta de Instagram
    @elpajaroduran.</p>
    </body></html>
    """


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
