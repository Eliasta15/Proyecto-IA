from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
import psycopg2
import random
from datetime import datetime


DB_CONFIG = {
    'host': '159.203.41.84',
    'port': '6432',
    'database': 'REGISTROS',
    'user': 'consulta_psuv',
    'password': 'NovieNTorISE'
}

admin_bp = Blueprint('admin', __name__)

# Middleware para verificar si es administrador CON AUTENTICACIÓN
def admin_required(f):
    def decorated_function(*args, **kwargs):
        # Verificar si el usuario está autenticado como admin
        if not session.get('es_administrador'):
            return redirect(url_for('auth.formulario_login_admin'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/admin')
@admin_required
def panel_admin():
    return render_template('admin_panel.html')


@admin_bp.route('/api/admin/participantes')
@admin_required
def obtener_participantes():
    """Obtiene todos los participantes registrados"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, nombre, email, departamento, gustos, 
                   talla_camisa, talla_pantalon, talla_zapato,
                   color_favorito, regalo_deseado, codigo_acceso
            FROM ia.tb_participantes_ai 
            ORDER BY nombre
        """)
        
        participantes = []
        for row in cur.fetchall():
            participantes.append({
                'id': row[0],
                'nombre': row[1],
                'email': row[2],
                'departamento': row[3],
                'gustos': row[4],
                'talla_camisa': row[5],
                'talla_pantalon': row[6],
                'talla_zapato': row[7],
                'color_favorito': row[8],
                'regalo_deseado': row[9],
                'codigo_acceso': row[10]
            })
        
        return jsonify({'participantes': participantes})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@admin_bp.route('/api/admin/realizar-sorteo', methods=['POST'])
@admin_required
def realizar_sorteo():
    """Realiza sorteo SOLO para participantes NUEVOS (sin asignación previa)"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # 1. Obtener participantes que NO tienen asignación
        cur.execute("""
            SELECT p.id, p.nombre 
            FROM ia.tb_participantes_ai p
            LEFT JOIN ia.tb_asignaciones_ai a ON p.id = a.dador_id
            WHERE a.dador_id IS NULL  -- Solo los que NO tienen asignación
            ORDER BY p.id
        """)
        
        participantes_sin_asignacion = [(row[0], row[1]) for row in cur.fetchall()]
        
        # 2. Validaciones CRÍTICAS
        if len(participantes_sin_asignacion) == 0:
            return jsonify({
                'error': 'No hay participantes nuevos sin asignación.',
                'participantes_nuevos': 0,
                'minimo_requerido': 2,
                'tipo_sorteo': 'nuevos'
            }), 400
        
        if len(participantes_sin_asignacion) % 2 != 0:
            return jsonify({
                'error': f'Hay {len(participantes_sin_asignacion)} participantes nuevos (número impar). Se necesita un número par para el sorteo.',
                'participantes_nuevos': len(participantes_sin_asignacion),
                'minimo_requerido': 'número par',
                'tipo_sorteo': 'nuevos'
            }), 400
        
        if len(participantes_sin_asignacion) < 2:
            return jsonify({
                'error': f'Se necesitan al menos 2 participantes nuevos. Actualmente hay {len(participantes_sin_asignacion)}.',
                'participantes_nuevos': len(participantes_sin_asignacion),
                'minimo_requerido': 2,
                'tipo_sorteo': 'nuevos'
            }), 400
        
        # 3. Algoritmo de sorteo SOLO para nuevos
        participantes_ids = [p[0] for p in participantes_sin_asignacion]
        random.shuffle(participantes_ids)
        
        asignaciones = []
        for i in range(len(participantes_ids)):
            dador_id = participantes_ids[i]
            receptor_id = participantes_ids[(i + 1) % len(participantes_ids)]  # Circular
            
            # Insertar nueva asignación
            cur.execute("""
                INSERT INTO ia.tb_asignaciones_ai (dador_id, receptor_id) 
                VALUES (%s, %s)
            """, (dador_id, receptor_id))
            
            # Marcar que YA participó en sorteo (opcional, para estadísticas)
            cur.execute("""
                UPDATE ia.tb_participantes_ai 
                SET participo_sorteo = TRUE
                WHERE id = %s
            """, (dador_id,))
            
            # Obtener nombres para la respuesta
            dador_nombre = next(p[1] for p in participantes_sin_asignacion if p[0] == dador_id)
            receptor_nombre = next(p[1] for p in participantes_sin_asignacion if p[0] == receptor_id)
            
            asignaciones.append({
                'dador': dador_nombre,
                'receptor': receptor_nombre
            })
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'mensaje': f'✅ Sorteo realizado para {len(participantes_sin_asignacion)} participantes NUEVOS',
            'total_participantes': len(participantes_sin_asignacion),
            'tipo_sorteo': 'nuevos',
            'asignaciones': asignaciones
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@admin_bp.route('/api/admin/asignaciones')
@admin_required
def obtener_asignaciones():
    """Obtiene todas las asignaciones del sorteo"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                d.nombre as dador_nombre,
                r.nombre as receptor_nombre,
                r.gustos,
                r.color_favorito,
                r.regalo_deseado
            FROM ia.tb_asignaciones_ai a
            JOIN ia.tb_participantes_ai d ON a.dador_id = d.id
            JOIN ia.tb_participantes_ai r ON a.receptor_id = r.id
            ORDER BY d.nombre
        """)
        
        asignaciones = []
        for row in cur.fetchall():
            asignaciones.append({
                'dador': row[0],
                'receptor': row[1],
                'gustos_receptor': row[2],
                'color_favorito_receptor': row[3],
                'regalo_deseado_receptor': row[4]
            })
        
        return jsonify({'asignaciones': asignaciones})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@admin_bp.route('/api/admin/buscar-participantes')
@admin_required
def buscar_participantes():
    """Busca participantes por nombre, email o departamento"""
    busqueda = request.args.get('q', '')
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        if busqueda:
            # Búsqueda en múltiples campos
            cur.execute("""
                SELECT id, nombre, email, departamento, gustos, codigo_acceso
                FROM ia.tb_participantes_ai 
                WHERE nombre ILIKE %s 
                   OR email ILIKE %s 
                   OR departamento ILIKE %s
                ORDER BY nombre
            """, (f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'))
        else:
            # Si no hay búsqueda, traer todos
            cur.execute("""
                SELECT id, nombre, email, departamento, gustos, codigo_acceso
                FROM ia.tb_participantes_ai 
                ORDER BY nombre
            """)
        
        participantes = []
        for row in cur.fetchall():
            participantes.append({
                'id': row[0],
                'nombre': row[1],
                'email': row[2],
                'departamento': row[3],
                'gustos': row[4],
                'codigo_acceso': row[5]
            })
        
        return jsonify({
            'participantes': participantes,
            'total_encontrados': len(participantes),
            'busqueda': busqueda
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@admin_bp.route('/api/admin/estadisticas')
@admin_required
def obtener_estadisticas():
    """Obtiene estadísticas del sistema - VERSIÓN MEJORADA"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Total participantes
        cur.execute("SELECT COUNT(*) FROM ia.tb_participantes_ai")
        total_participantes = cur.fetchone()[0]
        
        # Total asignaciones
        cur.execute("SELECT COUNT(*) FROM ia.tb_asignaciones_ai")
        total_asignaciones = cur.fetchone()[0]
        
        # Participantes CON asignación
        cur.execute("""
            SELECT COUNT(DISTINCT p.id) 
            FROM ia.tb_participantes_ai p
            JOIN ia.tb_asignaciones_ai a ON p.id = a.dador_id
        """)
        participantes_con_asignacion = cur.fetchone()[0]
        
        # Participantes SIN asignación (NUEVOS)
        participantes_sin_asignacion = total_participantes - participantes_con_asignacion
        
        # Verificar si se puede hacer sorteo fino
        puede_sorteo_fino = participantes_sin_asignacion >= 2 and participantes_sin_asignacion % 2 == 0
        
        return jsonify({
            'total_participantes': total_participantes,
            'total_asignaciones': total_asignaciones,
            'participantes_con_asignacion': participantes_con_asignacion,
            'participantes_sin_asignacion': participantes_sin_asignacion,
            'puede_sorteo_fino': puede_sorteo_fino,
            'sorteo_realizado': total_asignaciones > 0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@admin_bp.route('/api/admin/sorteo-completo', methods=['POST'])
@admin_required
def sorteo_completo():
    """Realiza un sorteo COMPLETO (elimina todas las asignaciones anteriores)"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # CONFIRMACIÓN EXTRA desde el frontend
        data = request.json
        if not data.get('confirmado'):
            return jsonify({
                'necesita_confirmacion': True,
                'mensaje': '⚠️ Esta acción eliminará TODAS las asignaciones existentes. ¿Estás seguro?',
                'detalles': 'Se realizará un nuevo sorteo con TODOS los participantes.'
            }), 400
        
        # Obtener TODOS los participantes
        cur.execute("SELECT id, nombre FROM ia.tb_participantes_ai ORDER BY id")
        todos_participantes = [(row[0], row[1]) for row in cur.fetchall()]
        
        if len(todos_participantes) < 2:
            return jsonify({'error': 'Se necesitan al menos 2 participantes'}), 400
        
        # 1. ELIMINAR todas las asignaciones anteriores
        cur.execute("DELETE FROM ia.tb_asignaciones_ai")
        
        # 2. RESETEAR flag de participación
        cur.execute("UPDATE ia.tb_participantes_ai SET participo_sorteo = FALSE")
        
        # 3. Realizar nuevo sorteo completo
        participantes_ids = [p[0] for p in todos_participantes]
        random.shuffle(participantes_ids)
        
        asignaciones = []
        for i in range(len(participantes_ids)):
            dador_id = participantes_ids[i]
            receptor_id = participantes_ids[(i + 1) % len(participantes_ids)]
            
            cur.execute("""
                INSERT INTO ia.tb_asignaciones_ai (dador_id, receptor_id) 
                VALUES (%s, %s)
            """, (dador_id, receptor_id))
            
            # Marcar como participante
            cur.execute("""
                UPDATE ia.tb_participantes_ai 
                SET participo_sorteo = TRUE
                WHERE id = %s
            """, (dador_id,))
            
            dador_nombre = next(p[1] for p in todos_participantes if p[0] == dador_id)
            receptor_nombre = next(p[1] for p in todos_participantes if p[0] == receptor_id)
            
            asignaciones.append({
                'dador': dador_nombre,
                'receptor': receptor_nombre
            })
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'mensaje': f'✅ Sorteo COMPLETO realizado para {len(todos_participantes)} participantes',
            'total_participantes': len(todos_participantes),
            'tipo_sorteo': 'completo',
            'asignaciones': asignaciones
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@admin_bp.route('/api/admin/detalles-participante/<int:participante_id>')
@admin_required
def detalles_participante(participante_id):
    """Obtiene información detallada de un participante específico"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Información básica del participante
        cur.execute("""
            SELECT nombre, email, departamento, gustos, talla_camisa, talla_pantalon,
                   talla_zapato, color_favorito, regalo_deseado, codigo_acceso
            FROM ia.tb_participantes_ai 
            WHERE id = %s
        """, (participante_id,))
        
        participante = cur.fetchone()
        
        if not participante:
            return jsonify({'error': 'Participante no encontrado'}), 404
        
        # Información de asignación (si existe)
        cur.execute("""
            SELECT r.nombre, r.gustos
            FROM ia.tb_asignaciones_ai a
            JOIN ia.tb_participantes_ai r ON a.receptor_id = r.id
            WHERE a.dador_id = %s
        """, (participante_id,))
        
        asignacion = cur.fetchone()
        
        datos_participante = {
            'id': participante_id,
            'nombre': participante[0],
            'email': participante[1],
            'departamento': participante[2],
            'gustos': participante[3],
            'talla_camisa': participante[4],
            'talla_pantalon': participante[5],
            'talla_zapato': participante[6],
            'color_favorito': participante[7],
            'regalo_deseado': participante[8],
            'codigo_acceso': participante[9],
            'tiene_asignacion': asignacion is not None
        }
        
        if asignacion:
            datos_participante['amigo_secreto'] = {
                'nombre': asignacion[0],
                'gustos': asignacion[1]
            }
        
        return jsonify(datos_participante)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@admin_bp.route('/admin-login')
def formulario_login_admin():
    """Muestra el formulario de login para administradores"""
    return render_template('admin_login.html')

@admin_bp.route('/api/admin/login', methods=['POST'])
def login_admin():
    """Procesa el login de administradores"""
    data = request.json
    usuario = data.get('usuario')
    password = data.get('password')
    
    # VERIFICACIÓN CORREGIDA
    if usuario in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[usuario] == password:
        session['es_administrador'] = True
        session['admin_usuario'] = usuario
        return jsonify({
            'success': True,
            'mensaje': 'Login exitoso como administrador',
            'redirect': url_for('admin.panel_admin')
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Credenciales incorrectas'
        }), 401
    
@admin_bp.route('/admin-logout') 
def logout_admin():
    session.clear()
    return redirect('/login')