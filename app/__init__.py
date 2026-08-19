import os
from flask import Flask
from app.config import Config
from app.database import db
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from app.models.usuario import Usuario

def create_app():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, 'web', 'templates')
    static_dir = os.path.join(base_dir, 'web', 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(Config)

    db.init_app(app)
    JWTManager(app)

    # Inicializar LoginManager
    login_manager = LoginManager()
    login_manager.login_view = 'web.login'
    login_manager.login_message = 'Inicia sesión para acceder al panel.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # Registrar Blueprints
    from app.api.auth import auth_bp
    from app.api.estructura import estructura_bp
    from app.api.cortes import cortes_bp
    from app.web.routes import web_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(estructura_bp)
    app.register_blueprint(cortes_bp)
    app.register_blueprint(web_bp)

    with app.app_context():
        db.create_all()

    return app