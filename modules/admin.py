from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
import psycopg2
import random
from datetime import datetime
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv('BACKEND_URL')

admin_bp = Blueprint('admin', __name__)

# Middleware para verificar si es administrador CON AUTENTICACIÓN prueba
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not session.get('es_administrador'):
            return redirect(url_for('auth.formulario_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/admin')
@admin_required
def panel_admin():
    return render_template('admin_panel.html')

@admin_bp.route('/admin/participantes')
@admin_required
def obtener_participantes():    
    try:
        backend_response = requests.get(
            f"{BACKEND_URL}users/participants",
            timeout=300
        )

        backend_data = backend_response.json()
        if backend_data["code"] > 300:         
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
        
        participantes = []
        for part in backend_data["data"]:
            participantes.append({
                'id': part['id'],
                'nombre': part['nombre'],
                'email': part['email'],
                'departamento': part['departamento'],
                'gustos': part['gustos'],
                'talla_camisa': part['talla_camisa'],
                'talla_pantalon': part['talla_pantalon'],
                'talla_zapato': part['talla_zapato'],
                'color_favorito': part['color_favorito'],
                'regalo_deseado': part['regalo_deseado']
            })
        
        return jsonify({'participantes': participantes})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/realizar-sorteo', methods=['POST'])
@admin_required
def realizar_sorteo():    
    try:
        data = request.json
        if not data.get('confirmado'):
            return jsonify({
                'necesita_confirmacion': True,
                'mensaje': '⚠️ Esta acción eliminará TODAS las asignaciones existentes. ¿Estás seguro?',
                'detalles': 'Se realizará un nuevo sorteo con TODOS los participantes.'
            }), 400
        
        asignaciones = []
        backend_response = requests.post(
            f"{BACKEND_URL}users/run-giveaway",
            timeout=300
        )

        backend_data = backend_response.json()
        if backend_data["code"] > 300:         
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
        
        return jsonify({
            'success': True,
            'mensaje': f'✅ Sorteo realizado para {len(backend_data["data"])} participantes',
            'total_participantes': len(backend_data["data"]),
            'tipo_sorteo': 'nuevos',
            'asignaciones': backend_data["data"]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/asignaciones')
@admin_required
def obtener_asignaciones():    
    try:
        backend_response = requests.get(
            f"{BACKEND_URL}users/asignaciones",
            timeout=300
        )

        backend_data = backend_response.json()
        if backend_data["code"] > 300:         
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
            
        asignaciones = backend_data["data"]        
        return jsonify({'asignaciones': asignaciones})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/buscar-participantes')
@admin_required
def buscar_participantes():
    try:
        busqueda = request.args.get('q', '').strip()
        backend_response = requests.get(
            f"{BACKEND_URL}users/participants-query",
            params={"query": busqueda if busqueda != '' else None},
            timeout=300
        )
        backend_data = backend_response.json()
        if backend_data["code"] > 300:         
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
               
        participantes = backend_data["data"]        
        return jsonify(participantes)        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/estadisticas')
@admin_required
def obtener_estadisticas():    
    try:
        backend_response = requests.get(
            f"{BACKEND_URL}users/statics",
            timeout=300
        )
        backend_data = backend_response.json()
        if backend_data["code"] > 300:         
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
        
        data = backend_data["data"]        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/detalles-participante/<int:participante_id>')
@admin_required
def detalles_participante(participante_id):    
    try:        
        backend_response = requests.get(
            f"{BACKEND_URL}users/user/{participante_id}",
            timeout=300
        )
        backend_data = backend_response.json()
        if backend_data["code"] > 300:         
            return jsonify({'error': backend_data["message"]}), backend_data["code"]
        
        data = backend_data["data"]
        
        if data is None:
            return jsonify({'error': 'Participante no encontrado'}), 404        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

""" Por hacer """    
""" @admin_bp.route('/admin/reiniciar-todo', methods=['POST'])
@admin_required
def reiniciar_todo():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # CONFIRMACIÓN EXTRA desde el frontend
        data = request.json
        if not data.get('confirmado'):
            return jsonify({
                'necesita_confirmacion': True,
                'mensaje': '⚠️ Esta acción ELIMINARÁ TODAS las asignaciones existentes. ¿Estás seguro?',
                'detalles': 'Se eliminarán todas las asignaciones y los participantes podrán volver a consultar.'
            }), 400

        # 1. ELIMINAR todas las asignaciones
        cur.execute("DELETE FROM ia.tb_asignaciones_ai")
        
        # 2. RESETEAR flag de participación de TODOS los participantes
        cur.execute("UPDATE ia.tb_participantes_ai SET participo_sorteo = FALSE")
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'mensaje': '✅ Sistema reiniciado completamente',
            'detalles': 'Todas las asignaciones han sido eliminadas. Los participantes pueden volver a consultar.'
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close() """

@admin_bp.route('/admin-logout') 
def logout_admin():
    session.clear()
    return redirect('/login')