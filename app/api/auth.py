from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models.usuario import Usuario

auth_bp = Blueprint('auth_api', __name__, url_prefix='/api/v1/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    cedula = data.get('cedula')
    password = data.get('password')

    if not cedula or not password:
        return jsonify({'error': 'Cédula y contraseña son requeridas'}), 400

    usuario = Usuario.query.filter_by(cedula=str(cedula)).first()

    if not usuario or not usuario.check_password(password):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    access_token = create_access_token(identity=str(usuario.id))
    
    return jsonify({
        'token': access_token,
        'usuario': usuario.to_dict()
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    current_user_id = get_jwt_identity()
    usuario = Usuario.query.get(current_user_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify(usuario.to_dict()), 200

@auth_bp.route('/buscar-cedula/<cedula>', methods=['GET'])
def buscar_por_cedula(cedula):
    usuario = Usuario.query.filter_by(cedula=str(cedula).strip()).first()
    if not usuario:
        return jsonify({'encontrado': False}), 404
    return jsonify({
        'encontrado': True,
        'usuario': usuario.to_dict()
    }), 200

@auth_bp.route('/login-cedula', methods=['POST'])
def login_cedula():
    data = request.get_json() or {}
    cedula = data.get('cedula')

    if not cedula:
        return jsonify({'error': 'La cédula es requerida'}), 400

    usuario = Usuario.query.filter_by(cedula=str(cedula).strip()).first()

    if not usuario:
        return jsonify({'error': 'Cédula no registrada en el sistema'}), 404

    # Generar token JWT con la identidad del usuario
    access_token = create_access_token(identity=str(usuario.id))

    return jsonify({
        'token': access_token,
        'usuario': usuario.to_dict()
    }), 200