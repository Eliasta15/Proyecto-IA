from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
import psycopg2
import requests

DB_CONFIG = {
    'host': '159.203.41.84',
    'port': '6432',
    'database': 'REGISTROS',
    'user': 'consulta_psuv',
    'password': 'NovieNTorISE'
}

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

@usuario_bp.route('/api/mi-amigo-secreto')
@login_required
def obtener_amigo_secreto():
    """Obtiene la información del amigo secreto asignado al usuario logueado"""
    usuario_id = session['usuario_id']
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Buscar el amigo secreto asignado a este usuario
        cur.execute("""
            SELECT p.nombre, p.gustos, p.color_favorito, p.regalo_deseado,
                   p.talla_camisa, p.talla_pantalon, p.talla_zapato
            FROM ia.tb_asignaciones_ai a
            JOIN ia.tb_participantes_ai p ON a.receptor_id = p.id
            WHERE a.dador_id = %s
        """, (usuario_id,))
        
        amigo = cur.fetchone()
        
        if amigo:
            return jsonify({
                'amigo_secreto': {
                    'nombre': amigo[0],
                    'gustos': amigo[1],
                    'color_favorito': amigo[2],
                    'regalo_deseado': amigo[3],
                    'talla_camisa': amigo[4],
                    'talla_pantalon': amigo[5],
                    'talla_zapato': amigo[6]
                }
            })
        else:
            return jsonify({
                'mensaje': 'Aún no se ha realizado el sorteo o no tienes amigo secreto asignado'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@usuario_bp.route('/api/chat-ia', methods=['POST'])
@login_required
def chat_ia_personalizado():
    """Chat con IA que conoce la identidad del usuario y su amigo secreto"""
    data = request.json
    pregunta = data.get('pregunta')
    usuario_id = session['usuario_id']
    
    # Primero obtener información del amigo secreto
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Obtener info del amigo secreto
        cur.execute("""
            SELECT p.nombre, p.gustos, p.color_favorito, p.regalo_deseado,
                   p.talla_camisa, p.talla_pantalon, p.talla_zapato
            FROM ia.tb_asignaciones_ai a
            JOIN ia.tb_participantes_ai p ON a.receptor_id = p.id
            WHERE a.dador_id = %s
        """, (usuario_id,))
        
        amigo = cur.fetchone()
        
        if not amigo:
            return jsonify({
                'respuesta': 'Aún no se ha realizado el sorteo. No tienes amigo secreto asignado.'
            })
        
        # Construir contexto personalizado para la IA
        contexto = f"""
        Eres un asistente para un juego de Amigo Secreto.
        
        INFORMACIÓN DEL AMIGO SECRETO:
        - Nombre: {amigo[0]}
        - Gustos: {amigo[1]}
        - Color favorito: {amigo[2]}
        - Regalo deseado: {amigo[3]}
        - Talla camisa: {amigo[4]}
        - Talla pantalón: {amigo[5]}
        - Talla zapato: {amigo[6]}
        
        El usuario actual ({session['usuario_nombre']}) te hace esta pregunta:
        "{pregunta}"
        
        Responde de manera útil y mantén la confidencialidad. No reveles el nombre del amigo secreto directamente a menos que sea necesario para la respuesta.
        """
        
        # Llamar a Ollama
        respuesta_ia = consultar_ollama(contexto)
        return jsonify({'respuesta': respuesta_ia})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

def consultar_ollama(prompt):
    """Función para consultar la IA local (Ollama)"""
    try:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "mistral:7b-instruct",
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(url, json=payload)
        return response.json()["response"]
    except Exception as e:
        return f"🤖 Error consultando IA: {str(e)}"