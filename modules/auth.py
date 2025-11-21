from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
import psycopg2

# configuración de DB
DB_CONFIG = {
    'host': '159.203.41.84',
    'port': '6432',
    'database': 'REGISTROS',
    'user': 'consulta_psuv',
    'password': 'NovieNTorISE'
}

auth_bp = Blueprint('auth', __name__)

ADMIN_CREDENTIALS = {
    'prueba@admin.com': 'admin123'
}

@auth_bp.route('/login')
def formulario_login():
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@auth_bp.route('/login', methods=['POST'])
def login_usuario():
    email = request.form.get('email')
    password = request.form.get('password')
    
    print(f"🔍 DEBUG LOGIN: email={email}, password={password}")
    
    # PRIMERO: Verificar si es administrador
    if email in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[email] == password:
        session['es_administrador'] = True
        session['admin_usuario'] = email
        print("✅ DEBUG: Login exitoso como administrador")
        return redirect('/admin')  # Redirige al panel de admin
    
    # SEGUNDO: Si no es admin, verificar como usuario normal
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, nombre FROM ia.tb_participantes_ai 
            WHERE email = %s AND codigo_acceso = %s
        """, (email, password))
        
        usuario = cur.fetchone()
        
        if usuario:
            session['usuario_id'] = usuario[0]
            session['usuario_nombre'] = usuario[1]
            session['usuario_email'] = email
            print("✅ DEBUG: Login exitoso como usuario normal")
            return redirect('/usuario')  # Redirige al panel de usuario normal
        else:
            print("❌ DEBUG: Credenciales incorrectas")
            return render_template('login.html', error='Email o clave incorrectos')
            
    except Exception as e:
        print(f"❌ DEBUG: Error en login: {str(e)}")
        return render_template('login.html', error='Error del sistema')
    finally:
        cur.close()
        conn.close()