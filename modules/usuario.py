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
    """Chat con IA que mantiene el anonimato del DADOR pero revela el RECEPTOR"""
    data = request.json
    pregunta = data.get('pregunta')
    usuario_id = session['usuario_id']
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Obtener info del amigo secreto (RECEPTOR - a quien el usuario regala)
        cur.execute("""
            SELECT p.nombre, p.gustos, p.color_favorito, p.regalo_deseado,
                   p.talla_camisa, p.talla_pantalon, p.talla_zapato
            FROM ia.tb_asignaciones_ai a
            JOIN ia.tb_participantes_ai p ON a.receptor_id = p.id
            WHERE a.dador_id = %s
        """, (usuario_id,))
        
        amigo_secreto = cur.fetchone()
        
        if not amigo_secreto:
            return jsonify({
                'respuesta': 'Aún no se ha realizado el sorteo. No tienes amigo secreto asignado.'
            })
        
        # 1. VALIDAR PREGUNTAS PROHIBIDAS - sobre QUIÉN REGALA
        pregunta_lower = pregunta.lower()
        
        # Preguntas sobre QUIÉN LE REGALA AL USUARIO
        preguntas_prohibidas_usuario = [
            'quien me regala', 'quién me regala', 'me regala', 'me toco', 'me tocó',
            'sexo de quien me regala', 'género de quien me regala', 'dador',
            'persona que me regala', 'identidad de mi dador', 'quien me tiene',
            'saber quien me regala', 'descubrir quien me regala', 'quien me da'
        ]
        
        # Preguntas sobre QUIÉN LE REGALA A OTRAS PERSONAS
        preguntas_prohibidas_otros = [
            'quien le regala a', 'quién le regala a', 'le regala a', 'le toco a', 'le tocó a',
            'saber quien le regala a', 'descubrir quien le regala a', 'quien le da a'
        ]
        
        # Verificar si pregunta sobre QUIÉN LE REGALA AL USUARIO
        if any(prohibida in pregunta_lower for prohibida in preguntas_prohibidas_usuario):
            return jsonify({
                'respuesta': '🤫 ¡Esa es la magia del Amigo Secreto! No puedo revelar quién te regalará a ti. La sorpresa es parte de la diversión. ¿Por qué no mejor me cuidas qué ideas tienes para el regalo de tu amigo secreto?'
            })
        
        # Verificar si pregunta sobre QUIÉN LE REGALA A OTRA PERSONA
        if any(prohibida in pregunta_lower for prohibida in preguntas_prohibidas_otros):
            return jsonify({
                'respuesta': '🔒 El anonimato es para todos los participantes. No puedo revelar información sobre las asignaciones de otras personas. ¿Puedo ayudarte con ideas para tu propio amigo secreto?'
            })
        
        # 2. PROMPT INTELIGENTE - Con información del receptor pero protegiendo anonimato
        contexto = f"""
Eres un asistente especializado en juegos de Amigo Secreto.

🎁 INFORMACIÓN DEL AMIGO SECRETO DEL USUARIO (a quien debe regalar):
- Nombre: {amigo_secreto[0]}
- Gustos: {amigo_secreto[1] or 'No especificado'}
- Color favorito: {amigo_secreto[2] or 'No especificado'}
- Regalo deseado: {amigo_secreto[3] or 'No especificado'}
- Tallas: Camisa {amigo_secreto[4] or 'N/A'}, Pantalón {amigo_secreto[5] or 'N/A'}, Zapato {amigo_secreto[6] or 'N/A'}

🚫 INFORMACIÓN PROHIBIDA (NUNCA REVELAR):
- Quién le regala al usuario actual
- Quién le regala a cualquier otra persona
- Asignaciones de otros participantes

📝 PREGUNTA DEL USUARIO: "{pregunta}"

💡 INSTRUCCIONES DE RESPUESTA:
- Si pregunta sobre QUIÉN REGALA AL USUARIO: Responde manteniendo el misterio
- Si pregunta sobre QUIÉN REGALA A OTROS: Protege el anonimato de todos
- Si pregunta sobre REGALOS para SU amigo secreto: Da ideas creativas
- MANTÉN un tono amigable y divertido, redirigiendo hacia ideas de regalos

RESPONDE DE MANERA ÚTIL Y DIVERTIDA:
"""
        
        # Llamar a Ollama
        respuesta_ia = consultar_ollama(contexto)
        
        # 3. VALIDACIÓN EXTRA - Verificar que la IA no se haya "escapado"
        respuesta_lower = respuesta_ia.lower()
        if any(fuga in respuesta_lower for fuga in ['te regala', 'tu dador', 'te toco', 'le regala a', 'le toco a']):
            respuesta_ia = "🎁 ¡La magia del Amigo Secreto está en el misterio! Mejor hablemos de ideas creativas para tu regalo. ¿Qué te parece algo relacionado con los gustos de tu amigo secreto?"
        
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