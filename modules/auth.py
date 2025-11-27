from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
import psycopg2
import os
from dotenv import load_dotenv
import requests
import hashlib

auth_bp = Blueprint('auth', __name__)
BACKEND_URL = os.getenv('BACKEND_URL')

@auth_bp.route('/login')
def formulario_login():
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@auth_bp.route('/login', methods=['POST'])
def login_usuario():
    try:
        email = request.form.get('email')
        password = request.form.get('password')

        password = hashlib.sha256(password.encode())
        password = password.hexdigest()        
        backend_response = requests.post(
            f"{BACKEND_URL}auth/sing-in/",
            json={"email": email, "password": password},
            timeout=300
        )

        backend_data = backend_response.json()
        if backend_data["code"] > 300:         
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
        
        data = backend_data["data"]
        if data.get("is_admin"):
            session['es_administrador'] = True
            session['admin_usuario'] = email
            print("✅ DEBUG: Login exitoso como administrador")
            return redirect('/admin')
        
                
        
        session['usuario_id'] = data.get("id")
        session['usuario_nombre'] = data.get("nombre")
        session['usuario_email'] = data.get("email")
        print("✅ DEBUG: Login exitoso como usuario normal")
        return redirect('/usuario')
               
    except Exception as e:
        print(f"❌ DEBUG: Error en login: {str(e)}")
        return render_template('login.html', error='Error del sistema')