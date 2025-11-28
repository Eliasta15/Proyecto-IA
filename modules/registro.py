from flask import Blueprint, request, jsonify, render_template
import psycopg2
import secrets
import smtplib
import hashlib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
import requests

load_dotenv()
registro_bp = Blueprint('registro', __name__)

BACKEND_URL = os.getenv('BACKEND_URL')

def enviar_codigo_email(email, codigo):
    try:
        mensaje = MIMEText(f"""
        ¡Bienvenido al Amigo Secreto!
        
        Tu código de acceso es: {codigo}
        
        Guarda este código para acceder a tu panel personal.
        """)
        mensaje['Subject'] = 'Código de Acceso - Amigo Secreto'
        mensaje['From'] = 'amigosecreto@empresa.com'
        mensaje['To'] = email
        
        # Por ahora solo muestra en consola (lo configuramos después)
        print(f"📧 Código para {email}: {codigo}")
        return True
    except Exception as e:
        print(f"Error en email: {e}")
        return False

@registro_bp.route('/registro')
def formulario_registro():
    return render_template('registro.html', backend_url=BACKEND_URL)

@registro_bp.route('/registro', methods=['POST'])
def registrar_participante():
    try:            
        # ✅ FORMA CORRECTA - elige una:
        data = request.get_json()  # Opción 1
        # data = request.json       # Opción 2
        
        # VERIFICAR QUE LAS CLAVES COINCIDAN
        clave = data.get('clave')
        confirmar_clave = data.get('confirmar_clave')
        
        if not clave or not confirmar_clave:
            return jsonify({'error': 'Debe ingresar y confirmar la clave'}), 400
        
        if clave != confirmar_clave:
            return jsonify({'error': 'Las claves no coinciden'}), 400
        
        if len(clave) < 8:
            return jsonify({'error': 'La clave debe tener al menos 8 caracteres'}), 400
        
        clave = hashlib.sha256(clave.encode())
        clave = clave.hexdigest() 
        
        send_data = {
            "nombre": data.get('nombre'),
            "email": data.get('email'),
            "departamento": data.get('departamento'),
            "codigo_acceso": clave,
            "gustos": data.get('gustos'),
            "talla_camisa": data.get('talla_camisa'),
            "talla_pantalon": data.get('talla_pantalon'),
            "talla_zapato": data.get('talla_zapato'),
            "color_favorito": data.get('color_favorito'),
            "regalo_deseado": data.get('regalo_deseado'),
            "participo_sorteo": True
        }
        
        backend_response = requests.post(
            f"{BACKEND_URL}auth",
            json=send_data,
            timeout=300
        )
        backend_data = backend_response.json()
        if backend_data["code"] > 300:         
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
        return jsonify(backend_data["data"]), backend_response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Error conectando con el backend: {str(e)}'}), 500