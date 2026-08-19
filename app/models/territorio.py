from app.database import db

class Comuna(db.Model):
    __tablename__ = 'comuna'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)
    circuito_gestion = db.Column(db.Integer, nullable=False)

    comunidades = db.relationship('Comunidad', backref='comuna', lazy=True)
    usuarios = db.relationship('Usuario', backref='comuna', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'circuito_gestion': self.circuito_gestion
        }

class SubEstacion(db.Model):
    __tablename__ = 'sub_estacion'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)

    circuitos = db.relationship('CircuitoElectrico', backref='sub_estacion', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre
        }

class CircuitoElectrico(db.Model):
    __tablename__ = 'circuito_electrico'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    sub_estacion_id = db.Column(db.Integer, db.ForeignKey('sub_estacion.id'), nullable=False)

    comunidades = db.relationship('Comunidad', backref='circuito', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'sub_estacion_id': self.sub_estacion_id,
            'sub_estacion_nombre': self.sub_estacion.nombre if self.sub_estacion else ''
        }

class Comunidad(db.Model):
    __tablename__ = 'comunidad'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    comuna_id = db.Column(db.Integer, db.ForeignKey('comuna.id'), nullable=False)
    circuito_id = db.Column(db.Integer, db.ForeignKey('circuito_electrico.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'comuna_id': self.comuna_id,
            'comuna_nombre': self.comuna.nombre if self.comuna else '',
            'circuito_id': self.circuito_id,
            'circuito_nombre': self.circuito.nombre if self.circuito else '',
            'sub_estacion_nombre': self.circuito.sub_estacion.nombre if self.circuito and self.circuito.sub_estacion else ''
        }