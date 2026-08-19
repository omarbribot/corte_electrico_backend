from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.database import db
from app.models.territorio import Comuna, SubEstacion, CircuitoElectrico, Comunidad
from app.models.usuario import Usuario
from app.models.corte import RegistroCorte

web_bp = Blueprint('web', __name__)

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))

    if request.method == 'POST':
        cedula = request.form.get('cedula', '').strip()
        password = request.form.get('password', '').strip()

        usuario = Usuario.query.filter_by(cedula=cedula).first()

        if usuario and usuario.check_password(password):
            if usuario.rol <= 1:
                login_user(usuario)
                return redirect(url_for('web.dashboard'))
            else:
                flash('Acceso no autorizado: Esta cuenta es exclusiva para la aplicación móvil.', 'danger')
        else:
            flash('Cédula o contraseña incorrectas.', 'danger')

    return render_template('login.html')

@web_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('web.login'))

@web_bp.route('/')
@login_required
def dashboard():
    cortes_activos = RegistroCorte.query.filter_by(estado='EN_CORTE').all()
    ultimos_cortes = RegistroCorte.query.order_by(RegistroCorte.id.desc()).limit(50).all()
    total_comunidades = Comunidad.query.count()
    total_comunas = Comuna.query.count()
    
    return render_template('dashboard.html',
                           cortes_activos=cortes_activos,
                           ultimos_cortes=ultimos_cortes,
                           total_comunidades=total_comunidades,
                           total_comunas=total_comunas)

@web_bp.route('/matriz', methods=['GET', 'POST'])
@login_required
def matriz_relaciones():
    if request.method == 'POST':
        comunidad_id = request.form.get('comunidad_id')
        nuevo_circuito_id = request.form.get('circuito_id')
        nueva_comuna_id = request.form.get('comuna_id')

        comunidad = Comunidad.query.get(comunidad_id)
        if comunidad:
            comunidad.circuito_id = nuevo_circuito_id
            comunidad.comuna_id = nueva_comuna_id
            db.session.commit()
            flash('Relación de comunidad actualizada con éxito', 'success')

    comunidades = Comunidad.query.all()
    circuitos = CircuitoElectrico.query.all()
    comunas = Comuna.query.all()
    sub_estaciones = SubEstacion.query.all()
    
    return render_template('matriz.html',
                           comunidades=comunidades,
                           circuitos=circuitos,
                           comunas=comunas,
                           sub_estaciones=sub_estaciones)

@web_bp.route('/jefes', methods=['GET', 'POST'])
@login_required
def asignacion_jefes():
    if request.method == 'POST':
        cedula = request.form.get('cedula', '').strip()
        nombre = request.form.get('nombre', '').strip()
        telefono = request.form.get('telefono', '').strip()
        comunidades_ids = request.form.getlist('comunidades_ids')
        password = request.form.get('password', '123456')

        usuario = Usuario.query.filter_by(cedula=cedula).first()
        if not usuario:
            usuario = Usuario(
                cedula=cedula,
                nombre_apellido=nombre,
                telefono=telefono,
                rol=3
            )
            usuario.set_password(password)
            db.session.add(usuario)
        else:
            usuario.nombre_apellido = nombre
            usuario.telefono = telefono
            usuario.rol = 3

        comunidades_objs = Comunidad.query.filter(Comunidad.id.in_(comunidades_ids)).all()
        usuario.comunidades_asignadas = comunidades_objs

        db.session.commit()
        flash('Jefe de comunidad asignado correctamente', 'success')

    jefes = Usuario.query.filter_by(rol=3).all()
    comunidades = Comunidad.query.all()
    
    return render_template('jefes.html', jefes=jefes, comunidades=comunidades)