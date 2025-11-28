from flask import Flask, jsonify, request, render_template, session, redirect, url_for
import os
import psycopg2
import requests
import json
from datetime import datetime
import random
import decimal
from modules.registro import registro_bp
from modules.auth import auth_bp
from modules.usuario import usuario_bp
from modules.admin import admin_bp
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
app.register_blueprint(registro_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(usuario_bp)
app.register_blueprint(admin_bp)



@app.route('/')
def pagina_principal():
    return redirect('/login')

if __name__ == '__main__': 
    app.run(debug=True, port=5001)