from gevent import monkey
monkey.patch_all()

import os
import json
import io
from flask import Flask, render_template, request as flask_request
from flask_socketio import SocketIO, emit
from datetime import datetime
import pytz  # Importação do pytz para manipulação de fuso horário
from dotenv import load_dotenv
from markupsafe import escape

# Google Drive
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

import firebase_admin
from firebase_admin import credentials, messaging
load_dotenv()

GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not GOOGLE_CREDENTIALS_JSON:
    raise RuntimeError("❌ Variável de ambiente 'GOOGLE_CREDENTIALS_JSON' não encontrada.")

FIREBASE_CREDENTIALS_INFO = json.loads(GOOGLE_CREDENTIALS_JSON)
firebase_admin.initialize_app(credentials.Certificate(FIREBASE_CREDENTIALS_INFO))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecret')
socketio = SocketIO(app, cors_allowed_origins="*")

DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
DRIVE_FILE_NAME = "historico_chat.json"
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not GOOGLE_CREDENTIALS_JSON:
    raise RuntimeError("❌ Variável de ambiente 'GOOGLE_CREDENTIALS_JSON' não encontrada.")

SERVICE_ACCOUNT_INFO = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO,
    scopes=['https://www.googleapis.com/auth/drive']
)
drive_service = build('drive', 'v3', credentials=creds)

def get_or_create_drive_file():
    try:
        query = f"name='{DRIVE_FILE_NAME}' and '{DRIVE_FOLDER_ID}' in parents and trashed=false"
        results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])

        if items:
            return items[0]['id']

        file_metadata = {
            'name': DRIVE_FILE_NAME,
            'parents': [DRIVE_FOLDER_ID],
            'mimeType': 'application/json'
        }
        empty_stream = io.BytesIO(json.dumps([], ensure_ascii=False, indent=2).encode('utf-8'))
        media = MediaIoBaseUpload(empty_stream, mimetype='application/json')
        file = drive_service.files().create(body=file_metadata, media_body=media).execute()
        return file['id']

    except HttpError as error:
        print(f"❌ Erro ao acessar/criar arquivo no Drive: {error}")
        return None

FILE_ID = get_or_create_drive_file()

def get_drive_history():
    try:
        if not FILE_ID:
            return []

        download_request = drive_service.files().get_media(fileId=FILE_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, download_request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        content = fh.getvalue().decode('utf-8')
        return json.loads(content)

    except Exception as e:
        print("❌ Erro ao obter histórico do Drive:", str(e))
        return []

def update_drive_history(messages):
    try:
        if not FILE_ID:
            return False

        media_body = io.BytesIO(json.dumps(messages, ensure_ascii=False, indent=2).encode('utf-8'))
        media = MediaIoBaseUpload(media_body, mimetype='application/json')
        drive_service.files().update(fileId=FILE_ID, media_body=media).execute()
        return True

    except Exception as e:
        print("❌ Erro ao atualizar histórico no Drive:", str(e))
        return False

# Usuários online com controle de atividade
online_users = {}

# Função para obter a hora local ajustada para GMT-3
def get_local_time():
    # Define o fuso horário de São Paulo (GMT-3)
    local_tz = pytz.timezone('America/Sao_Paulo')
    return datetime.now(local_tz).strftime('%d/%m/%Y %H:%M')

# Função para enviar notificação push para o Firebase Cloud Messaging
def send_push_notification(title, message, token):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=message
            ),
            token=token,
        )
        response = messaging.send(message)
        print(f"Push notification sent successfully: {response}")
    except Exception as e:
        print(f"❌ Erro ao enviar notificação push: {str(e)}")

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    mensagens = get_drive_history()
    emit('load_messages', mensagens)
    emit('load_users', list(online_users.values()))  # Envia todos os usuários (online/offline)

@socketio.on('user_online')
def handle_user_online(nome):
    nome = escape(nome.strip())[:30] or "Anônimo"  # Sanitização e tamanho máx
    agora = get_local_time()  # Usando a função para obter o horário correto

    # Adiciona o usuário à lista de online_users com a hora de entrada
    online_users[flask_request.sid] = {
        "nome": nome,
        "online": True,
        "ultima_atividade": agora,
        "hora_entrada": agora  # Hora de quando o usuário entrou
    }

    print(f"[✔] {nome} está online")
    emit('load_users', list(online_users.values()), broadcast=True)

@socketio.on('message')
def handle_message(data):
    try:
        nome = escape(data.get('nome', 'Anônimo').strip())[:30]
        msg = data.get('mensagem', '').strip()
        horario = get_local_time()  # Usando a função para obter o horário correto

        if not msg:
            return

        nova_mensagem = {
            "nome": nome,
            "mensagem": msg,
            "horario": horario
        }

        mensagens = get_drive_history()
        mensagens.append(nova_mensagem)

        update_drive_history(mensagens)
        emit('response', nova_mensagem, broadcast=True)

        # Envia uma notificação push para todos os usuários conectados
        for sid, usuario in online_users.items():
            if usuario.get('push_token'):
                send_push_notification("Nova Mensagem", msg, usuario['push_token'])

        # Atualiza timestamp de atividade do remetente
        if flask_request.sid in online_users:
            online_users[flask_request.sid]["ultima_atividade"] = horario

    except Exception as e:
        print("❌ Erro no envio da mensagem:", str(e))

@socketio.on('disconnect')
def handle_disconnect():
    sid = flask_request.sid
    if sid in online_users:
        usuario = online_users[sid]
        usuario["online"] = False
        usuario["ultima_atividade"] = get_local_time()  # Atualiza a última atividade com o horário atual
        print(f"[✔] {usuario['nome']} desconectado")
    emit('load_users', list(online_users.values()), broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
