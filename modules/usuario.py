from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
import psycopg2
import os
import requests
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv('BACKEND_URL')

usuario_bp = Blueprint('usuario', __name__)

# Middleware para verificar si el usuario está logueado
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('auth.formulario_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@usuario_bp.route('/usuario')
@login_required
def panel_usuario():
    return render_template('usuario_panel.html')

@usuario_bp.route('/usuario/mi-amigo-secreto')
@login_required
def obtener_amigo_secreto():
    try:
        usuario_id = session['usuario_id']    
        backend_response = requests.get(
            f"{BACKEND_URL}users/secret-friend/{usuario_id}",
            timeout=300
        )
        backend_data = backend_response.json()
        if backend_data["code"] > 300:         
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
        
        if backend_data["data"]:
            return jsonify(backend_data["data"])
        else:
            return jsonify({
                'mensaje': 'Aún no se ha realizado el sorteo o no tienes amigo secreto asignado'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@usuario_bp.route('/usuario/chat-ia', methods=['POST'])
@login_required
def chat_ia_personalizado():
    try:
        data = request.json
        pregunta = data.get('pregunta')
        usuario_id = session['usuario_id']
        data_send = {
            "pregunta": pregunta,
            "usuario_id": int(usuario_id)
        }
        backend_response = requests.post(
            f"{BACKEND_URL}users/chat-ia",
            json=data_send,
            timeout=300
        )
        backend_data = backend_response.json()
        if backend_data["code"] > 300:
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
        
        data = backend_data["data"]
        
        return jsonify({'respuesta': data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@usuario_bp.route('/usuario/historial-chat', methods=['GET'])
@login_required
def historial_chat():
    try:
        usuario_id = session['usuario_id']
        backend_response = requests.get(
            f"{BACKEND_URL}users/historial-chat/{usuario_id}",
            timeout=300
        )
        backend_data = backend_response.json()
        if backend_data["code"] > 300:
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
        
        data = backend_data["data"]        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500