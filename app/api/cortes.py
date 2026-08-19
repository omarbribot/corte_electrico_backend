from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import db
from app.models.usuario import Usuario
from app.models.territorio import Comunidad, CircuitoElectrico
from app.models.corte import RegistroCorte
from datetime import datetime

cortes_bp = Blueprint('cortes_api', __name__, url_prefix='/api/v1/cortes')

def _parsear_iso_datetime(str_datetime):
    """Convierte un string ISO8601 enviado por Flutter a objetos date y time con soporte amplio de formatos"""
    if not str_datetime or not isinstance(str_datetime, str):
        return None, None
    try:
        # Reemplazar Z y limpiar caracteres no estándar
        clean_str = str_datetime.replace('Z', '').strip()
        # Si contiene 'T', lo parseamos directamente con datetime.fromisoformat
        dt = datetime.fromisoformat(clean_str)
        return dt.date(), dt.time()
    except Exception:
        # Fallback para cadenas separadas por espacio o formatos alternativos
        try:
            dt = datetime.strptime(clean_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
            return dt.date(), dt.time()
        except Exception:
            return None, None

@cortes_bp.route('/reporte-perfil1', methods=['POST'])
def reporte_perfil_1():
    data = request.get_json() or {}
    
    usuario_id = data.get('usuario_id')
    circuito_id = data.get('circuito_id')
    str_inicio = data.get('fecha_inicio')
    str_fin = data.get('fecha_fin')
    observaciones = data.get('observaciones', '')
    estado_solicitado = data.get('estado')

    fecha_inicio, hora_inicio = _parsear_iso_datetime(str_inicio)
    fecha_fin, hora_fin = _parsear_iso_datetime(str_fin)

    if not circuito_id:
        return jsonify({'error': 'Debes seleccionar un Circuito Eléctrico'}), 400

    estado = estado_solicitado if estado_solicitado else ('RESTABLECIDO' if fecha_fin else 'EN_CORTE')

    comunidades = Comunidad.query.filter_by(circuito_id=circuito_id).all()
    if not comunidades:
        return jsonify({'error': 'No hay comunidades registradas en este circuito eléctrico'}), 404

    comunidades_ids = [c.id for c in comunidades]

    # --- VALIDACIÓN 1: INTENTO DE REPETIR INICIO DE CORTE ---
    if estado == 'EN_CORTE':
        cortes_activos = RegistroCorte.query.filter(
            RegistroCorte.comunidad_id.in_(comunidades_ids),
            RegistroCorte.estado == 'EN_CORTE'
        ).all()

        if cortes_activos:
            return jsonify({
                'error': f'El circuito ya tiene un corte activo ({len(cortes_activos)} comunidades afectadas). Si el servicio ya volvió, marque "¿Servicio Restablecido?".'
            }), 400

    # --- VALIDACIÓN 2 Y CIERRE DE CORTE ACTIVO PREVIO ---
    if estado == 'RESTABLECIDO':
        cortes_activos = RegistroCorte.query.filter(
            RegistroCorte.comunidad_id.in_(comunidades_ids),
            RegistroCorte.estado == 'EN_CORTE'
        ).all()

        if not cortes_activos:
            return jsonify({
                'error': 'No hay ningún corte eléctrico activo en este circuito para restablecer.'
            }), 400

        # Si hay cortes activos, cerramos el evento existente
        # NOTA: NO TOCAMOS corte.fecha_inicio NI corte.hora_inicio PARA NO PERDER LA HORA DE INICIO REAL
        for corte in cortes_activos:
            corte.fecha_fin = fecha_fin or datetime.now().date()
            corte.hora_fin = hora_fin or datetime.now().time()
            corte.estado = 'RESTABLECIDO'
            if hasattr(corte, 'observaciones') and observaciones:
                corte.observaciones = observaciones
            if hasattr(corte, 'calcular_duracion'):
                corte.calcular_duracion()  # <--- Recalcula usando inicio original vs fin actual

        db.session.commit()
        return jsonify({
            'mensaje': f'Servicio restablecido exitosamente para {len(cortes_activos)} comunidades',
            'comunidades_afectadas': len(cortes_activos),
            'estado': 'RESTABLECIDO'
        }), 200

    # --- REGISTRO DE NUEVO CORTE (SOLO CUANDO ES EN_CORTE) ---
    for com in comunidades:
        nuevo_corte = RegistroCorte(
            comunidad_id=com.id,
            circuito_id=circuito_id,
            fecha_inicio=fecha_inicio or datetime.now().date(),
            hora_inicio=hora_inicio or datetime.now().time(),
            estado='EN_CORTE',
            usuario_id=usuario_id
        )

        if hasattr(nuevo_corte, 'observaciones'):
            setattr(nuevo_corte, 'observaciones', observaciones)

        db.session.add(nuevo_corte)

    db.session.commit()
    return jsonify({
        'mensaje': f'Inicio de corte reportado exitosamente para {len(comunidades)} comunidades',
        'comunidades_afectadas': len(comunidades),
        'estado': 'EN_CORTE'
    }), 201
@cortes_bp.route('/inicio', methods=['POST'])
@jwt_required()
def reportar_inicio():
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)
    data = request.get_json() or {}

    str_fecha = data.get('fecha')
    str_hora = data.get('hora')

    if not str_fecha or not str_hora:
        return jsonify({'error': 'Fecha y hora requeridas'}), 400

    fecha_obj = datetime.strptime(str_fecha, '%Y-%m-%d').date()
    hora_obj = datetime.strptime(str_hora, '%H:%M').time()

    comunidades_afectadas = []

    if usuario.rol == 1:
        comuna_id = data.get('comuna_id')
        circuito_id = data.get('circuito_id')
        
        query = Comunidad.query
        if circuito_id:
            query = query.filter_by(circuito_id=circuito_id)
        if comuna_id:
            query = query.filter_by(comuna_id=comuna_id)
        comunidades_afectadas = query.all()

    elif usuario.rol == 2:
        if not usuario.comuna_id:
            return jsonify({'error': 'El comisionado no tiene comuna asignada'}), 400
        
        circuito_id = data.get('circuito_id')
        comunidades_afectadas = Comunidad.query.filter_by(
            comuna_id=usuario.comuna_id,
            circuito_id=circuito_id
        ).all()

    elif usuario.rol == 3:
        if not usuario.comunidad_id:
            return jsonify({'error': 'El jefe de comunidad no tiene comunidad asignada'}), 400
        
        comunidad = Comunidad.query.get(usuario.comunidad_id)
        if comunidad:
            comunidades_afectadas = [comunidad]

    if not comunidades_afectadas:
        return jsonify({'error': 'No se encontraron comunidades para este reporte'}), 404

    registros_creados = []
    for com in comunidades_afectadas:
        corte = RegistroCorte(
            comunidad_id=com.id,
            circuito_id=com.circuito_id,
            usuario_id=usuario.id,
            fecha_inicio=fecha_obj,
            hora_inicio=hora_obj,
            estado='EN_CORTE'
        )
        db.session.add(corte)
        registros_creados.append(corte)

    db.session.commit()

    return jsonify({
        'mensaje': f'Se registraron {len(registros_creados)} cortes de inicio exitosamente',
        'cortes': [c.to_dict() for c in registros_creados]
    }), 201

@cortes_bp.route('/fin', methods=['PUT'])
@jwt_required()
def reportar_fin():
    data = request.get_json() or {}
    corte_id = data.get('corte_id')
    str_fecha = data.get('fecha')
    str_hora = data.get('hora')

    if not corte_id or not str_fecha or not str_hora:
        return jsonify({'error': 'ID de corte, fecha y hora de fin son requeridos'}), 400

    corte = RegistroCorte.query.get(corte_id)
    if not corte:
        return jsonify({'error': 'Registro de corte no encontrado'}), 404

    fecha_obj = datetime.strptime(str_fecha, '%Y-%m-%d').date()
    hora_obj = datetime.strptime(str_hora, '%H:%M').time()

    corte.fecha_fin = fecha_obj
    corte.hora_fin = hora_obj
    corte.estado = 'RESTABLECIDO'
    if hasattr(corte, 'calcular_duracion'):
        corte.calcular_duracion()

    db.session.commit()

    return jsonify({
        'mensaje': 'Servicio restablecido exitosamente',
        'corte': corte.to_dict()
    }), 200

@cortes_bp.route('/activos', methods=['GET'])
def cortes_activos():
    cortes = RegistroCorte.query.filter_by(estado='EN_CORTE').all()
    return jsonify([c.to_dict() for c in cortes]), 200

@cortes_bp.route('/reporte-perfil2', methods=['POST'])
@jwt_required()
def reporte_perfil_2():
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.comuna_id:
        return jsonify({'error': 'El comisionado no tiene una comuna asociada'}), 400

    data = request.get_json() or {}
    circuito_id = data.get('circuito_id')
    str_inicio = data.get('fecha_inicio')
    
    fecha_inicio, hora_inicio = _parsear_iso_datetime(str_inicio)

    comunidades = Comunidad.query.filter_by(comuna_id=usuario.comuna_id, circuito_id=circuito_id).all()
    if not comunidades:
        return jsonify({'error': 'No hay comunidades para este circuito en tu comuna'}), 404

    for com in comunidades:
        corte = RegistroCorte(
            comunidad_id=com.id,
            circuito_id=circuito_id,
            fecha_inicio=fecha_inicio,
            hora_inicio=hora_inicio,
            estado='EN_CORTE',
            reportado_por_id=user_id
        )
        db.session.add(corte)

    db.session.commit()
    return jsonify({'mensaje': f'Corte reportado en tu comuna para {len(comunidades)} comunidades'}), 201

# Elimina o comenta @jwt_required() para alinearlo con el resto de los perfiles
@cortes_bp.route('/reporte-perfil3', methods=['POST'])
def reporte_perfil_3():
    data = request.get_json() or {}
    
    user_id = data.get('usuario_id')
    usuario = Usuario.query.get(user_id) if user_id else None

    if not usuario or not getattr(usuario, 'comunidades_asignadas', None):
        return jsonify({'error': 'No tienes comunidades asignadas'}), 400

    str_inicio = data.get('fecha_inicio')
    str_fin = data.get('fecha_fin')
    observaciones = data.get('observaciones', '')
    estado_solicitado = data.get('estado')

    fecha_inicio, hora_inicio = _parsear_iso_datetime(str_inicio)
    fecha_fin, hora_fin = _parsear_iso_datetime(str_fin)

    estado = estado_solicitado if estado_solicitado else ('RESTABLECIDO' if fecha_fin else 'EN_CORTE')

    comunidad_ids_seleccionadas = data.get('comunidades_ids', [c.id for c in usuario.comunidades_asignadas])
    comunidades_a_procesar = [c for c in usuario.comunidades_asignadas if c.id in comunidad_ids_seleccionadas]

    if not comunidades_a_procesar:
        return jsonify({'error': 'No seleccionaste ninguna comunidad válida'}), 400

    comunidades_ids = [c.id for c in comunidades_a_procesar]

    # VALIDACIÓN 1: INICIO DUPLICADO
    if estado == 'EN_CORTE':
        cortes_activos = RegistroCorte.query.filter(
            RegistroCorte.comunidad_id.in_(comunidades_ids),
            RegistroCorte.estado == 'EN_CORTE'
        ).all()

        if cortes_activos:
            return jsonify({
                'error': 'Tu comunidad ya tiene un corte eléctrico activo registrado. Marca "Servicio Restablecido" para notificar el fin.'
            }), 400

        for com in comunidades_a_procesar:
            nuevo_corte = RegistroCorte(
                comunidad_id=com.id,
                circuito_id=com.circuito_id,
                fecha_inicio=fecha_inicio or datetime.now().date(),
                hora_inicio=hora_inicio or datetime.now().time(),
                estado='EN_CORTE',
                usuario_id=usuario.id
            )
            if hasattr(nuevo_corte, 'observaciones'):
                setattr(nuevo_corte, 'observaciones', observaciones)

            db.session.add(nuevo_corte)

        db.session.commit()
        return jsonify({
            'mensaje': 'Inicio de corte reportado correctamente en tu comunidad',
            'estado': 'EN_CORTE'
        }), 201

    # VALIDACIÓN 2: RESTABLECER SIN CORTE ACTIVO
    if estado == 'RESTABLECIDO':
        cortes_activos = RegistroCorte.query.filter(
            RegistroCorte.comunidad_id.in_(comunidades_ids),
            RegistroCorte.estado == 'EN_CORTE'
        ).all()

        # RECHAZO ESTRICTO
        if not cortes_activos:
            return jsonify({
                'error': 'No hay ningún corte eléctrico activo registrado en tu comunidad para restablecer.'
            }), 400

        for corte in cortes_activos:
            corte.fecha_fin = fecha_fin or datetime.now().date()
            corte.hora_fin = hora_fin or datetime.now().time()
            corte.estado = 'RESTABLECIDO'
            if hasattr(corte, 'observaciones') and observaciones:
                corte.observaciones = observaciones
            if hasattr(corte, 'calcular_duracion'):
                corte.calcular_duracion()

        db.session.commit()
        return jsonify({
            'mensaje': 'Servicio restablecido exitosamente en tu comunidad',
            'estado': 'RESTABLECIDO'
        }), 200
@cortes_bp.route('/comuna-estado/<int:comuna_id>', methods=['GET'])
def estado_comuna(comuna_id):
    from app.models.territorio import Comunidad
    from app.database import db

    comunidades = Comunidad.query.filter_by(comuna_id=comuna_id).all()
    resultado = []

    for com in comunidades:
        ultimo_corte = RegistroCorte.query.filter_by(comunidad_id=com.id)\
            .order_by(RegistroCorte.id.desc()).first()

        estado = 'RESTABLECIDO'
        ultima_actualizacion = None

        if ultimo_corte:
            estado = ultimo_corte.estado
            ultima_actualizacion = f"{ultimo_corte.fecha_inicio} {ultimo_corte.hora_inicio}"

        resultado.append({
            'id': com.id,
            'nombre': com.nombre,
            'circuito_nombre': com.circuito.nombre if com.circuito else 'Sin Circuito',
            'estado': estado,
            'ultima_actualizacion': ultima_actualizacion
        })

    return jsonify({'comunidades': resultado}), 200
# 1. Obtener circuitos vinculados a las comunidades de una comuna
@cortes_bp.route('/circuitos-comuna/<int:comuna_id>', methods=['GET'])
def circuitos_comuna(comuna_id):
    from app.models.territorio import Comunidad

    comunidades = Comunidad.query.filter_by(comuna_id=comuna_id).all()
    circuitos_dict = {}

    for com in comunidades:
        if com.circuito:
            c_id = com.circuito.id
            if c_id not in circuitos_dict:
                sub_nombre = com.circuito.subestacion.nombre if hasattr(com.circuito, 'subestacion') and com.circuito.subestacion else "SubEstación N/A"
                circuitos_dict[c_id] = {
                    'id': c_id,
                    'nombre': com.circuito.nombre,
                    'subestacion': sub_nombre
                }

    return jsonify({'circuitos': list(circuitos_dict.values())}), 200


# 2. Registrar/Restablecer corte para Perfil 4 (Circuito dentro de una Comuna)
@cortes_bp.route('/reporte-perfil4', methods=['POST'])
def reporte_perfil_4():
    data = request.get_json() or {}

    usuario_id = data.get('usuario_id')
    circuito_id = data.get('circuito_id')
    
    if not usuario_id or not circuito_id:
        return jsonify({'error': 'Usuario y Circuito son requeridos'}), 400

    usuario = Usuario.query.get(usuario_id)
    if not usuario or not usuario.comuna_id:
        return jsonify({'error': 'El usuario no tiene una comuna asignada'}), 400

    from app.models.territorio import Comunidad
    comunidades = Comunidad.query.filter_by(comuna_id=usuario.comuna_id, circuito_id=circuito_id).all()

    if not comunidades:
        return jsonify({'error': 'No hay comunidades vinculadas a este circuito en tu comuna'}), 400

    comunidades_ids = [c.id for c in comunidades]

    str_inicio = data.get('fecha_inicio')
    str_fin = data.get('fecha_fin')
    observaciones = data.get('observaciones', '')
    estado_solicitado = data.get('estado')

    fecha_inicio, hora_inicio = _parsear_iso_datetime(str_inicio)
    fecha_fin, hora_fin = _parsear_iso_datetime(str_fin)

    estado = estado_solicitado if estado_solicitado else ('RESTABLECIDO' if fecha_fin else 'EN_CORTE')

    # ------------------------------------------------------------------
    # VALIDACIÓN 1: INTENTO DE REPORTAR INICIO CUANDO YA HAY UN CORTE ACTIVO
    # ------------------------------------------------------------------
    if estado == 'EN_CORTE':
        cortes_activos = RegistroCorte.query.filter(
            RegistroCorte.comunidad_id.in_(comunidades_ids),
            RegistroCorte.estado == 'EN_CORTE'
        ).all()

        if cortes_activos:
            return jsonify({
                'error': 'Ya existe un corte eléctrico activo en este circuito dentro de tu comuna. Marca "Servicio Restablecido" para notificar el fin.'
            }), 400

        # Crear nuevo evento EN_CORTE
        for com in comunidades:
            nuevo_corte = RegistroCorte(
                comunidad_id=com.id,
                circuito_id=circuito_id,
                fecha_inicio=fecha_inicio or datetime.now().date(),
                hora_inicio=hora_inicio or datetime.now().time(),
                estado='EN_CORTE',
                usuario_id=usuario.id
            )
            if hasattr(nuevo_corte, 'observaciones'):
                setattr(nuevo_corte, 'observaciones', observaciones)

            db.session.add(nuevo_corte)

        db.session.commit()
        return jsonify({
            'mensaje': f'Inicio de corte registrado en {len(comunidades)} comunidad(es) de tu comuna',
            'estado': 'EN_CORTE'
        }), 201

    # ------------------------------------------------------------------
    # VALIDACIÓN 2: INTENTO DE RESTABLECER SIN NINGÚN CORTE ACTIVO PREVIO
    # ------------------------------------------------------------------
    if estado == 'RESTABLECIDO':
        cortes_activos = RegistroCorte.query.filter(
            RegistroCorte.comunidad_id.in_(comunidades_ids),
            RegistroCorte.estado == 'EN_CORTE'
        ).all()

        # RECHAZO ESTRICTO: No se permite restablecer si no hay corte activo registrado
        if not cortes_activos:
            return jsonify({
                'error': 'No hay ningún corte eléctrico activo registrado en este circuito para poder restablecer.'
            }), 400

        # Cierre y cálculo del evento activo
        for corte in cortes_activos:
            corte.fecha_fin = fecha_fin or datetime.now().date()
            corte.hora_fin = hora_fin or datetime.now().time()
            corte.estado = 'RESTABLECIDO'
            if hasattr(corte, 'observaciones') and observaciones:
                corte.observaciones = observaciones
            if hasattr(corte, 'calcular_duracion'):
                corte.calcular_duracion()

        db.session.commit()
        return jsonify({
            'mensaje': f'Servicio restablecido exitosamente en {len(cortes_activos)} comunidad(es) de tu comuna',
            'estado': 'RESTABLECIDO'
        }), 200

@cortes_bp.route('/comunas-list', methods=['GET'])
def listar_comunas():
    from app.models.territorio import Comuna
    comunas = Comuna.query.order_by(Comuna.nombre.asc()).all()
    resultado = [{'id': c.id, 'nombre': c.nombre} for c in comunas]
    return jsonify({'comunas': resultado}), 200    