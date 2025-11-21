from flask import Blueprint, request, jsonify, render_template
import psycopg2
import secrets
import smtplib
import hashlib
from email.mime.text import MIMEText  # ← CORREGIDO

# Usa la misma configuración de DB que tienes en app.py
DB_CONFIG = {
    'host': '159.203.41.84',
    'port': '6432',
    'database': 'REGISTROS',
    'user': 'consulta_psuv', 
    'password': 'NovieNTorISE'
}

registro_bp = Blueprint('registro', __name__)

def generar_codigo_acceso():
    return secrets.token_hex(3).upper()

def enviar_codigo_email(email, codigo):
    try:
        mensaje = MIMEText(f"""  # ← CORREGIDO
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
    return render_template('registro.html')

@registro_bp.route('/api/registro', methods=['POST'])
def registrar_participante():
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
    
    if len(clave) < 4:
        return jsonify({'error': 'La clave debe tener al menos 4 caracteres'}), 400
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # VERIFICAR SI EL EMAIL YA EXISTE
        cur.execute("SELECT id FROM ia.tb_participantes_ai WHERE email = %s", (data['email'],))
        if cur.fetchone():
            return jsonify({'error': 'Este email ya está registrado'}), 400
        
        # INSERTAR con la clave proporcionada por el usuario
        cur.execute("""
            INSERT INTO ia.tb_participantes_ai 
            (nombre, email, departamento, gustos, talla_camisa, talla_pantalon, 
             talla_zapato, color_favorito, regalo_deseado, codigo_acceso, participo_sorteo) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
            RETURNING id
        """, (
            data['nombre'], data['email'], data['departamento'], data['gustos'],
            data.get('talla_camisa'), data.get('talla_pantalon'), data.get('talla_zapato'),
            data.get('color_favorito'), data.get('regalo_deseado'), clave
        ))
        
        participante_id = cur.fetchone()[0]
        conn.commit()
        
        return jsonify({
            'mensaje': 'Registro exitoso', 
            'id': participante_id,
            'recordatorio': 'Guarda tu clave para ingresar al sistema'
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()