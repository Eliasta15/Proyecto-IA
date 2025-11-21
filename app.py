from flask import Flask, jsonify, request, render_template, session, redirect
import psycopg2
import requests
import json
from flask import render_template
from datetime import datetime
import random
import decimal
from modules.registro import registro_bp
from modules.auth import auth_bp
from modules.usuario import usuario_bp
from modules.admin import admin_bp

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # ← IMPORTANTE para sessions
# Registra el blueprint del registro
app.register_blueprint(registro_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(usuario_bp)
app.register_blueprint(admin_bp)


#Configuracion de bd
DB_CONFIG = {
    'host': '159.203.41.84',
    'port': '6432',
    'database': 'REGISTROS',
    'user': 'consulta_psuv',
    'password': 'NovieNTorISE'
}

def conectar_db():
    """Conectar a PostgreSQL con manejo de errores"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Error de conexión a BD: {e}")
        return None

# Ruta para agregar participantes - MEJORADA
@app.route('/api/participantes-old', methods=['POST'])
def agregar_participante_old():
    # Verificar que lleguen datos JSON
    if not request.is_json:
        return jsonify({'error': 'Se esperaba JSON'}), 400
    
    data = request.get_json()
    
    # Validar campos obligatorios
    if not data or 'nombre' not in data:
        return jsonify({'error': 'El campo nombre es obligatorio'}), 400
    
    # Extraer datos con valores por defecto
    nombre = data.get('nombre', '').strip()
    email = data.get('email', '').strip()
    departamento = data.get('departamento', '').strip()
    gustos = data.get('gustos', '').strip()
    
    # Validar nombre no vacío
    if not nombre:
        return jsonify({'error': 'El nombre no puede estar vacío'}), 400
    
    conn = conectar_db()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
    cur = conn.cursor()
    
    try:
        # INSERT con manejo de errores
        cur.execute("""
            INSERT INTO ia.tb_participantes_ai (nombre, email, departamento, gustos, creado_en) 
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (nombre, email, departamento, gustos, datetime.now()))
        
        participante_id = cur.fetchone()[0]
        conn.commit()
        
        return jsonify({
            'mensaje': 'Participante agregado exitosamente', 
            'id': participante_id,
            'nombre': nombre
        })
    
    except psycopg2.IntegrityError as e:
        conn.rollback()
        return jsonify({'error': 'Error de integridad en la base de datos'}), 400
    except Exception as e:
        conn.rollback()
        print(f"❌ Error en agregar_participante: {e}")
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500
    finally:
        cur.close()
        conn.close()

# Ruta para generar ideas - MEJORADA
@app.route('/api/ideas', methods=['POST'])
def obtener_ideas():
    if not request.is_json:
        return jsonify({'error': 'Se esperaba JSON'}), 400
    
    data = request.get_json()
    gustos = data.get('gustos', '')
    monto = data.get('monto', 10)
    
    # Función de IA con Ollama - MEJORADA
    def generar_ideas_amigo_secreto(gustos, monto):
        prompt = f"""
        Eres un asistente creativo para un Amigo Secreto en Venezuela.
        Presupuesto: {monto}$.
        Gustos de la persona: {gustos}
        
        Genera 3 ideas de regalo creativas, prácticas y apropiadas para una oficina:
        """
        
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "mistral:7b-instruct",
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json().get("response", "No se pudieron generar ideas en este momento.")
            else:
                return f"Error en la conexión con IA: {response.status_code}"
        except requests.exceptions.ConnectionError:
            return "❌ Error: No se puede conectar con Ollama. Verifica que esté ejecutándose."
        except Exception as e:
            return f"Error inesperado: {str(e)}"
    
    ideas = generar_ideas_amigo_secreto(gustos, monto)
    return jsonify({'ideas': ideas})

# Ruta para el sorteo - MEJORADA
@app.route('/api/sorteo', methods=['POST'])
def realizar_sorteo():
    conn = conectar_db()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
    cur = conn.cursor()
    
    try:
        # Verificar que hay participantes
        cur.execute("SELECT COUNT(*) FROM ia.tb_participantes_ai")
        count = cur.fetchone()[0]
        
        if count < 2:
            return jsonify({'error': 'Se necesitan al menos 2 participantes para el sorteo'}), 400
        
        # Obtener todos los participantes
        cur.execute("SELECT id FROM ia.tb_participantes_ai")
        participantes = [row[0] for row in cur.fetchall()]
        
        # Algoritmo de sorteo mejorado
        import random
        random.shuffle(participantes)
        
        # Limpiar asignaciones anteriores
        cur.execute("DELETE FROM ia.tb_asignaciones_ai")
        
        # Crear nuevas asignaciones
        asignaciones = []
        for i in range(len(participantes)):
            dador = participantes[i]
            receptor = participantes[(i + 1) % len(participantes)]
            
            cur.execute("""
                INSERT INTO ia.tb_asignaciones_ai (dador_id, receptor_id, creado_en) 
                VALUES (%s, %s, %s)
            """, (dador, receptor, datetime.now()))
            
            # Obtener nombres para la respuesta
            cur.execute("SELECT nombre FROM ia.tb_participantes_ai WHERE id = %s", (dador,))
            nombre_dador = cur.fetchone()[0]
            
            cur.execute("SELECT nombre FROM ia.tb_participantes_ai WHERE id = %s", (receptor,))
            nombre_receptor = cur.fetchone()[0]
            
            asignaciones.append({
                'dador': nombre_dador,
                'receptor': nombre_receptor
            })
        
        conn.commit()
        return jsonify({
            'mensaje': f'Sorteo realizado exitosamente para {count} participantes',
            'asignaciones': asignaciones
        })
    
    except Exception as e:
        conn.rollback()
        print(f"❌ Error en realizar_sorteo: {e}")
        return jsonify({'error': f'Error en el sorteo: {str(e)}'}), 500
    finally:
        cur.close()
        conn.close()

# Ruta para ver participantes
@app.route('/api/participantes', methods=['GET'])
def listar_participantes():
    conn = conectar_db()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id, nombre, email, departamento, gustos FROM ia.tb_participantes_ai ORDER BY nombre")
        participantes = []
        for row in cur.fetchall():
            participantes.append({
                'id': row[0],
                'nombre': row[1],
                'email': row[2],
                'departamento': row[3],
                'gustos': row[4]
            })
        
        return jsonify({'participantes': participantes})
    
    except Exception as e:
        print(f"❌ Error en listar_participantes: {e}")
        return jsonify({'error': f'Error al listar participantes: {str(e)}'}), 500
    finally:
        cur.close()
        conn.close()

# FUNCIONES AUXILIARES PARA EL ASISTENTE
def obtener_contexto_usuario(usuario_id):
    """Obtiene toda la información relevante de un usuario para el contexto de IA"""
    conn = conectar_db()
    if not conn:
        print("❌ No hay conexión a la base de datos")
        return None
        
    cur = conn.cursor()
    
    try:
        print(f"🔍 Buscando usuario ID: {usuario_id}")
        
        # 1. Verificar que el usuario existe
        cur.execute("SELECT id, nombre, email, departamento, gustos FROM ia.tb_participantes_ai WHERE id = %s", (usuario_id,))
        usuario_data = cur.fetchone()
        
        if not usuario_data:
            print(f"❌ Usuario con ID {usuario_id} no encontrado")
            return None
            
        usuario = {
            'id': usuario_data[0],
            'nombre': usuario_data[1] or 'Sin nombre',
            'email': usuario_data[2] or 'Sin email', 
            'departamento': usuario_data[3] or 'Sin departamento',
            'gustos': usuario_data[4] or 'Sin gustos especificados'
        }

        print(f"✅ Usuario encontrado: {usuario['nombre']}")

        # 2. Información de la asignación (amigo secreto)
        amigo_secreto = None
        cur.execute("""
            SELECT p.id, p.nombre, p.gustos, p.departamento
            FROM ia.tb_asignaciones_ai a
            JOIN ia.tb_participantes_ai p ON a.receptor_id = p.id
            WHERE a.dador_id = %s
        """, (usuario_id,))
        
        amigo_data = cur.fetchone()
        if amigo_data:
            amigo_secreto = {
                'id': amigo_data[0],
                'nombre': amigo_data[1] or 'Sin nombre',
                'gustos': amigo_data[2] or 'Sin gustos especificados',
                'departamento': amigo_data[3] or 'Sin departamento'
            }
            print(f"✅ Amigo secreto encontrado: {amigo_secreto['nombre']}")
        else:
            print(f"❌ Usuario {usuario_id} no tiene amigo secreto asignado")

        # 3. Configuración del juego - CON MANEJO MEJORADO DE ERRORES
        config = {
            'monto_maximo': 20.00,
            'fecha_intercambio': '15 de Diciembre 2024',
            'lugar': 'Oficina Principal'
        }
        
        try:
            cur.execute("SELECT monto_maximo, fecha_intercambio, lugar FROM ia.tb_configuracion_ai ORDER BY id DESC LIMIT 1")
            config_data = cur.fetchone()
            if config_data:
                # CONVERTIR Decimal a float para serialización JSON
                monto = float(config_data[0]) if config_data[0] else 20.00
                fecha = config_data[1].strftime('%d de %B %Y') if config_data[1] else '15 de Diciembre 2024'
                config = {
                    'monto_maximo': monto,
                    'fecha_intercambio': fecha,
                    'lugar': config_data[2] or 'Oficina Principal'
                }
                print(f"✅ Configuración cargada: ${monto} - {fecha}")
            else:
                print("⚠️ No hay configuración, usando valores por defecto")
        except Exception as e:
            print(f"⚠️ Error cargando configuración, usando valores por defecto: {e}")

        # 4. Lista de participantes
        participantes = []
        try:
            cur.execute("SELECT nombre, departamento FROM ia.tb_participantes_ai ORDER BY nombre")
            for row in cur.fetchall():
                participantes.append({
                    'nombre': row[0] or 'Sin nombre',
                    'departamento': row[1] or 'Sin departamento'
                })
            print(f"✅ {len(participantes)} participantes cargados")
        except Exception as e:
            print(f"⚠️ Error cargando participantes: {e}")

        contexto = {
            'usuario': usuario,
            'amigo_secreto': amigo_secreto,
            'configuracion': config,
            'participantes': participantes,
            'total_participantes': len(participantes)
        }
        
        print(f"🎯 Contexto COMPLETO obtenido para {usuario['nombre']}")
        return contexto
        
    except Exception as e:
        print(f"❌ Error crítico obteniendo contexto: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def asistente_inteligente(pregunta, contexto_usuario):
    """Versión MEJORADA con manejo robusto de Ollama"""
    
    if not contexto_usuario:
        return "❌ No puedo acceder a la información del juego en este momento."
    
    # Primero intentar con Ollama
    respuesta_ollama = obtener_respuesta_ollama(pregunta, contexto_usuario)
    
    # Si Ollama falla, usar respuestas predefinidas inteligentes
    if respuesta_ollama and not any(error in respuesta_ollama for error in ['Error', 'error', '❌', '⚠️']):
        return respuesta_ollama
    else:
        print("🔄 Ollama falló, usando respuestas predefinidas...")
        return generar_respuesta_inteligente(pregunta, contexto_usuario)

def obtener_respuesta_ollama(pregunta, contexto):
    """Intenta obtener respuesta de Ollama con manejo robusto de errores"""
    try:
        prompt = crear_prompt_inteligente(pregunta, contexto)
        
        payload = {
            "model": "mistral:7b-instruct",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 300  # Más corto para menos RAM
            }
        }
        
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",  #http://localhost:11434/api/generate
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            return None
            
    except Exception as e:
        print(f"⚠️ Ollama no disponible: {e}")
        return None

def crear_prompt_inteligente(pregunta, contexto):
    """Crea un prompt más eficiente para Ollama"""
    return f"""
Responde como asistente de Amigo Secreto. Sé breve y útil.

Información:
- Usuario: {contexto['usuario']['nombre']}
- Amigo secreto: {contexto['amigo_secreto']['nombre'] if contexto['amigo_secreto'] else 'No asignado'}
- Gustos del amigo: {contexto['amigo_secreto']['gustos'] if contexto['amigo_secreto'] else 'No especificados'}
- Presupuesto: ${contexto['configuracion']['monto_maximo']}
- Fecha: {contexto['configuracion']['fecha_intercambio']}

Pregunta: {pregunta}

Respuesta breve y práctica:
"""

def generar_respuesta_inteligente(pregunta, contexto):
    """Genera respuestas inteligentes cuando Ollama falla"""
    
    usuario = contexto['usuario']['nombre']
    amigo = contexto['amigo_secreto']
    monto = contexto['configuracion']['monto_maximo']
    fecha = contexto['configuracion']['fecha_intercambio']
    
    pregunta = pregunta.lower()
    
    if any(p in pregunta for p in ['quién', 'quien', 'amigo secreto']):
        if amigo:
            return f"🎅 ¡Hola {usuario}! Tu amigo secreto es **{amigo['nombre']}**.\n\nSus gustos: {amigo['gustos']}\n\n💡 ¿Necesitas ideas de regalo?"
        return "❌ Aún no tienes amigo secreto asignado."
    
    elif any(p in pregunta for p in ['regalar', 'idea', 'comprar']):
        if amigo:
            ideas = generar_ideas_creativas(amigo['gustos'], monto)
            return f"🎁 **Ideas para {amigo['nombre']}** (${monto}):\n\n{ideas}\n\n✨ ¿Te gustaría más ideas específicas?"
        return "🤔 Primero necesito saber quién es tu amigo secreto."
    
    elif any(p in pregunta for p in ['cuándo', 'cuando', 'fecha']):
        return f"📅 **Fecha del intercambio:** {fecha}\n\n¡No olvides preparar tu regalo!"
    
    elif any(p in pregunta for p in ['monto', 'precio', 'valor', 'cuánto']):
        return f"💰 **Presupuesto máximo:** ${monto}\n\n💎 La creatividad vale más que el precio."
    
    elif any(p in pregunta for p in ['hola', 'hi', 'hello', 'buenas']):
        return f"👋 ¡Hola {usuario}! Soy tu asistente de Amigo Secreto.\n\nPuedo ayudarte con:\n• Tu amigo secreto 🎅\n• Ideas de regalos 🎁\n• Fechas y montos 📅\n• Cualquier duda del juego"
    
    elif any(p in pregunta for p in ['gracias', 'thanks', 'bye']):
        return "¡De nada! 🎄 Que tengas un maravilloso amigo secreto."
    
    else:
        return f"🤔 No estoy seguro de entender '{pregunta}'.\n\nPuedo ayudarte con:\n• ¿Quién es mi amigo secreto?\n• Ideas de regalos creativas\n• Fecha del intercambio\n• Monto del regalo\n\n¿En qué más puedo ayudarte?"

def generar_ideas_creativas(gustos, monto):
    """Genera ideas de regalo creativas y contextuales"""
    
    base_ideas = [
        "📚 **Libro temático** - Relacionado con sus intereses",
        "🎧 **Accesorios audio** - Audífonos o altavoz portátil",
        "☕ **Kit café premium** - Con taza personalizada",
        "🌿 **Planta escritorio** - Purifica el aire de la oficina",
        "💡 **Lámpara LED** - Moderna y eficiente",
        "🖋️ **Set escritura** - Bolígrafo y cuaderno elegante",
        "🎯 **Juego de mesa** - Para divertirse en breaks",
        "🧴 **Kit cuidado personal** - Productos premium",
        "🔋 **Power bank** - Nunca se quede sin batería",
        "🎨 **Kit manualidades** - Para desarrollar creatividad"
    ]
    
    # Ideas específicas por gustos
    gustos_lower = gustos.lower()
    ideas_especificas = []
    
    if any(g in gustos_lower for g in ['café', 'cafe', 'té', 'te']):
        ideas_especificas.extend([
            "☕ **Café de especialidad** - De diferentes regiones",
            "🍵 **Tetera elegante** - Para disfrutar en oficina",
            "🥄 **Set cucharas miel** - Con miel artesanal"
        ])
    
    if any(g in gustos_lower for g in ['música', 'musica', 'sonido']):
        ideas_especificas.extend([
            "🎵 **Suscripción streaming** - Spotify/Apple Music",
            "🎶 **Vinilo decorativo** - De su artista favorito",
            "🎤 **Micrófono karaoke** - Para divertirse"
        ])
    
    if any(g in gustos_lower for g in ['tecnología', 'tech', 'gadget']):
        ideas_especificas.extend([
            "📱 **Soporte celular** - Para videollamadas",
            "💻 **Organizador cables** - Mantiene ordenado el espacio",
            "⌨️ **Teclado mecánico** - Mejora experiencia typing"
        ])
    
    if any(g in gustos_lower for g in ['deporte', 'ejercicio', 'gym']):
        ideas_especificas.extend([
            "💪 **Bandas resistencia** - Ejercicio en oficina",
            "🥤 **Botella inteligente** - Recordatorio de hidratación",
            "🧘 **Mat de yoga** - Para breaks activos"
        ])
    
    # Combinar y seleccionar ideas
    todas_ideas = ideas_especificas + base_ideas
    seleccionadas = random.sample(todas_ideas, min(4, len(todas_ideas)))
    
    return "\n".join(seleccionadas) + f"\n\n💡 **Presupuesto:** ${monto} - ¡Sé creativo!"

def guardar_conversacion(usuario_id, pregunta, respuesta, contexto):
    """Guarda el historial de conversaciones con manejo mejorado de JSON"""
    conn = conectar_db()
    if not conn:
        print("❌ No hay conexión para guardar conversación")
        return
        
    cur = conn.cursor()
    
    try:
        # Función para serializar objetos complejos
        def json_serializable(obj):
            if hasattr(obj, 'isoformat'):  # Para datetime
                return obj.isoformat()
            elif hasattr(obj, '__float__'):  # Para Decimal
                return float(obj)
            else:
                return str(obj)  # Para cualquier otro tipo
        
        # Convertir contexto a JSON seguro
        contexto_seguro = json.loads(json.dumps(contexto, default=json_serializable))
        
        cur.execute("""
            INSERT INTO ia.tb_conversaciones_ai (usuario_id, pregunta, respuesta, contexto)
            VALUES (%s, %s, %s, %s)
        """, (usuario_id, pregunta, respuesta, json.dumps(contexto_seguro)))
        
        conn.commit()
        print(f"✅ Conversación guardada para usuario {usuario_id}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error guardando conversación: {e}")
        
        # Intentar guardar sin contexto si falla
        try:
            cur.execute("""
                INSERT INTO ia.tb_conversaciones_ai (usuario_id, pregunta, respuesta)
                VALUES (%s, %s, %s)
            """, (usuario_id, pregunta, respuesta))
            conn.commit()
            print("✅ Conversación guardada sin contexto")
        except Exception as e2:
            print(f"❌ Error crítico guardando conversación: {e2}")
            
    finally:
        cur.close()
        conn.close()

def guardar_conversacion_simple(usuario_id, pregunta, respuesta):
    """Guarda conversación de forma simple"""
    conn = conectar_db()
    if not conn: return
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ia.tb_conversaciones_ai (usuario_id, pregunta, respuesta)
            VALUES (%s, %s, %s)
        """, (usuario_id, pregunta, respuesta))
        conn.commit()
    except Exception as e:
        print(f"⚠️ No se pudo guardar conversación: {e}")
    finally:
        cur.close()
        conn.close()        

# RUTA DEL ASISTENTE INTELIGENTE
@app.route('/api/chat', methods=['POST'])
def chat_amigo_secreto():
    """Endpoint del chat - Versión robusta"""
    try:
        data = request.get_json()
        pregunta = data.get('pregunta', '').strip()
        usuario_id = data.get('usuario_id')
        
        if not pregunta or not usuario_id:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        # Obtener contexto
        contexto = obtener_contexto_usuario(usuario_id)
        if not contexto:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Generar respuesta
        respuesta = asistente_inteligente(pregunta, contexto)
        
        # Guardar en historial
        guardar_conversacion_simple(usuario_id, pregunta, respuesta)
        
        return jsonify({'respuesta': respuesta})
        
    except Exception as e:
        print(f"❌ Error en chat: {e}")
        return jsonify({'error': 'Error interno'}), 500

# Ruta para obtener historial de conversación
@app.route('/api/chat/historial/<int:usuario_id>', methods=['GET'])
def obtener_historial_chat(usuario_id):
    """Obtiene el historial de conversaciones de un usuario"""
    conn = conectar_db()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT pregunta, respuesta, creado_en 
            FROM ia.tb_conversaciones_ai 
            WHERE usuario_id = %s 
            ORDER BY creado_en DESC 
            LIMIT 10
        """, (usuario_id,))
        
        conversaciones = []
        for row in cur.fetchall():
            conversaciones.append({
                'pregunta': row[0],
                'respuesta': row[1],
                'fecha': row[2].strftime('%d/%m/%Y %H:%M')
            })
        
        return jsonify({'historial': conversaciones})
    
    except Exception as e:
        print(f"❌ Error obteniendo historial: {e}")
        return jsonify({'error': f'Error al obtener historial: {str(e)}'}), 500
    finally:
        cur.close()
        conn.close()

# Ruta de diagnóstico - AGREGAR ESTO TEMPORALMENTE
@app.route('/api/debug/usuario/<int:usuario_id>')
def debug_usuario(usuario_id):
    """Ruta temporal para diagnosticar problemas de usuario"""
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
        conn.close()


@app.route('/')
def pagina_principal():
    return redirect('/login')

if __name__ == '__main__': 
    app.run(debug=True, port=5000)