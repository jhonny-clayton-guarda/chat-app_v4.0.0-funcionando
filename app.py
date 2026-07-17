from gevent import monkey
monkey.patch_all()

import os
import json
import io
from flask import Flask, render_template, request as flask_request, send_from_directory
from flask_socketio import SocketIO, emit
from datetime import datetime
import pytz
from dotenv import load_dotenv
from markupsafe import escape
import threading
import requests
import time

import firebase_admin
from firebase_admin import credentials, messaging

load_dotenv()

GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not GOOGLE_CREDENTIALS_JSON:
    raise RuntimeError("❌ Variável de ambiente 'GOOGLE_CREDENTIALS_JSON' não encontrada.")

FIREBASE_CREDENTIALS_INFO = json.loads(GOOGLE_CREDENTIALS_JSON)
firebase_admin.initialize_app(credentials.Certificate(FIREBASE_CREDENTIALS_INFO))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "supersecret")
socketio = SocketIO(app, cors_allowed_origins="*")

# --- ROTA CRÍTICA PARA NOTIFICAÇÕES ---
@app.route('/firebase-messaging-sw.js')
def serve_sw():
    return send_from_directory(os.getcwd(), 'firebase-messaging-sw.js', mimetype='application/javascript')

# Google Drive Setup
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
DRIVE_FILE_NAME = "historico_chat.json"
SERVICE_ACCOUNT_INFO = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO,
    scopes=["https://www.googleapis.com/auth/drive"]
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
drive_service = build("drive", "v3", credentials=creds)

def get_or_create_drive_file():
    try:
        query = f"name='{DRIVE_FILE_NAME}' and '{DRIVE_FOLDER_ID}' in parents and trashed=false"
        results = drive_service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        items = results.get("files", [])
        if items: return items[0]["id"]
        file_metadata = {"name": DRIVE_FILE_NAME, "parents": [DRIVE_FOLDER_ID], "mimeType": "application/json"}
        empty_stream = io.BytesIO(json.dumps([], ensure_ascii=False, indent=2).encode("utf-8"))
        media = MediaIoBaseUpload(empty_stream, mimetype="application/json")
        file = drive_service.files().create(body=file_metadata, media_body=media).execute()
        return file["id"]
    except Exception as e:
        print(f"❌ Erro Drive: {e}")
        return None

FILE_ID = get_or_create_drive_file()

def get_drive_history():
    try:
        if not FILE_ID: return []
        download_request = drive_service.files().get_media(fileId=FILE_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, download_request)
        done = False
        while not done: _, done = downloader.next_chunk()
        return json.loads(fh.getvalue().decode("utf-8"))
    except Exception as e: return []

def update_drive_history(messages):
    try:
        if not FILE_ID: return False
        media_body = io.BytesIO(json.dumps(messages, ensure_ascii=False, indent=2).encode("utf-8"))
        media = MediaIoBaseUpload(media_body, mimetype="application/json")
        drive_service.files().update(fileId=FILE_ID, media_body=media).execute()
        return True
    except Exception as e: return False

online_users = {}

def get_local_time():
    return datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")

def send_push_notification(title, message_body, token):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=message_body
            ),
            data={
                "title": title,
                "body": message_body
            },
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    priority='high',
                    visibility='public'
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound='default', content_available=True)
                ),
            ),
            token=token,
        )
        response = messaging.send(message)
        print(f"Push enviado: {response}")
    except Exception as e:
        print(f"❌ Erro Push: {e}")

@app.route("/")
def index(): return render_template("index.html")

@socketio.on("connect")
def handle_connect():
    emit("load_messages", get_drive_history())
    emit("load_users", [user for user in online_users.values() if user["online"]])

@socketio.on("user_online")
def handle_user_online(data):
    nome = escape(data.get("nome", "Anônimo").strip())[:30]
    push_token = data.get("push_token")
    agora = get_local_time()
    online_users[flask_request.sid] = {
        "nome": nome, "online": True, "ultima_atividade": agora,
        "hora_entrada": agora, "push_token": push_token
    }
    emit("load_users", [user for user in online_users.values() if user["online"]], broadcast=True)

@socketio.on("register_push_token")
def handle_register_push_token(data):
    if flask_request.sid in online_users:
        online_users[flask_request.sid]["push_token"] = data.get("token")

@socketio.on("message")
def handle_message(data):
    try:
        nome = escape(data.get("nome", "Anônimo").strip())[:30]
        msg = data.get("mensagem", "").strip()
        if not msg: return
        horario = get_local_time()
        nova_msg = {"nome": nome, "mensagem": msg, "horario": horario}
        
        hist = get_drive_history()
        hist.append(nova_msg)
        update_drive_history(hist)
        
        emit("response", nova_msg, broadcast=True)
        
        for sid, user in online_users.items():
            if sid != flask_request.sid and user.get("push_token"):
                send_push_notification("Nova Mensagem", f"{nome}: {msg}", user["push_token"])
    except Exception as e: print(f"❌ Erro Msg: {e}")

@socketio.on("disconnect")
def handle_disconnect():
    if flask_request.sid in online_users:
        online_users[flask_request.sid]["online"] = False
        emit("load_users", [user for user in online_users.values() if user["online"]], broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)

