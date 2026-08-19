from app.database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

usuario_comunidad = db.Table('usuario_comunidad',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True),
    db.Column('comunidad_id', db.Integer, db.ForeignKey('comunidad.id'), primary_key=True)
)

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    nombre_apellido = db.Column(db.String(150), nullable=False)
    telefono = db.Column(db.String(30), nullable=True)
    correo = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Roles: 0 (Admin Web Alcaldía), 1 (Frank Suárez), 2 (Comisionado), 3 (Jefe de Comunidad)
    rol = db.Column(db.Integer, nullable=False)
    
    comuna_id = db.Column(db.Integer, db.ForeignKey('comuna.id'), nullable=True)
    comunidades_asignadas = db.relationship('Comunidad', secondary=usuario_comunidad, backref=db.backref('jefes', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        # Obtener el nombre de la comuna de forma segura
        nombre_comuna = None
        if hasattr(self, 'comuna') and getattr(self, 'comuna', None):
            nombre_comuna = self.comuna.nombre

        comunidades_list = []
        if hasattr(self, 'comunidades_asignadas'):
            for c in self.comunidades_asignadas:
                circuito_data = None
                if hasattr(c, 'circuito') and c.circuito:
                    circuito_data = {'id': c.circuito.id, 'nombre': c.circuito.nombre}

                comunidades_list.append({
                    'id': c.id,
                    'nombre': c.nombre,
                    'circuito_id': c.circuito_id,
                    'circuito': circuito_data,
                    'circuito_nombre': c.circuito.nombre if (hasattr(c, 'circuito') and c.circuito) else 'Sin Circuito'
                })

        return {
            'id': self.id,
            'cedula': self.cedula,
            'nombre_apellido': self.nombre_apellido,
            'telefono': self.telefono,
            'correo': self.correo,
            'rol': self.rol,
            'comuna_id': self.comuna_id,
            'comuna_nombre': nombre_comuna,
            'comunidades': comunidades_list,
            'comunidades_asignadas': comunidades_list
        }