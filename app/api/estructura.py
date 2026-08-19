from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.territorio import Comuna, SubEstacion, CircuitoElectrico, Comunidad
from app.models.usuario import Usuario

estructura_bp = Blueprint('estructura_api', __name__, url_prefix='/api/v1/estructura')

@estructura_bp.route('/comunas', methods=['GET'])
def get_comunas():
    comunas = Comuna.query.all()
    return jsonify([c.to_dict() for c in comunas]), 200

@estructura_bp.route('/subestaciones', methods=['GET'])
def get_subestaciones():
    subestaciones = SubEstacion.query.all()
    return jsonify([s.to_dict() for s in subestaciones]), 200

@estructura_bp.route('/circuitos', methods=['GET'])
def get_circuitos():
    # Acepta tanto sub_estacion_id como subestacion_id por flexibilidad
    sub_estacion_id = request.args.get('sub_estacion_id') or request.args.get('subestacion_id')
    query = CircuitoElectrico.query
    if sub_estacion_id:
        query = query.filter_by(sub_estacion_id=sub_estacion_id)
    circuitos = query.all()
    return jsonify([c.to_dict() for c in circuitos]), 200

@estructura_bp.route('/mi-relacion', methods=['GET'])
@jwt_required()
def get_mi_relacion():
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)
    
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
        
    res = {'rol': usuario.rol}
    
    if usuario.rol == 2 and usuario.comuna_id:
        comuna = Comuna.query.get(usuario.comuna_id)
        res['comuna'] = comuna.to_dict() if comuna else None
        
    elif usuario.rol == 3 and usuario.comunidad_id:
        comunidad = Comunidad.query.get(usuario.comunidad_id)
        res['comunidad'] = comunidad.to_dict() if comunidad else None
        
    return jsonify(res), 200