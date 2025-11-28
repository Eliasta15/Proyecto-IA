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

""" @app.route('/api/debug/usuario/<int:usuario_id>')
def debug_usuario(usuario_id):
    conn = conectar_db()
    if not conn:
        return jsonify({'error': 'Sin conexión a BD'})
        
    cur = conn.cursor()
    
    try:
        # Verificar usuario
        cur.execute("SELECT id, nombre FROM ia.tb_participantes_ai WHERE id = %s", (usuario_id,))
        usuario = cur.fetchone()
        
        # Verificar asignaciones
        cur.execute("SELECT COUNT(*) FROM ia.tb_asignaciones_ai WHERE dador_id = %s", (usuario_id,))
        asignacion_count = cur.fetchone()[0]
        
        # Verificar configuración
        cur.execute("SELECT COUNT(*) FROM ia.tb_configuracion_ai")
        config_count = cur.fetchone()[0]
        
        # Verificar conversaciones
        cur.execute("SELECT COUNT(*) FROM ia.tb_conversaciones_ai WHERE usuario_id = %s", (usuario_id,))
        conversaciones_count = cur.fetchone()[0]
        
        return jsonify({
            'usuario_existe': bool(usuario),
            'usuario': {'id': usuario[0], 'nombre': usuario[1]} if usuario else None,
            'tiene_asignacion': asignacion_count > 0,
            'configuracion_existe': config_count > 0,
            'conversaciones_previas': conversaciones_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        cur.close()
        conn.close() """

@app.route('/')
def pagina_principal():
    return redirect('/login')

if __name__ == '__main__': 
    app.run(debug=True, port=5001)