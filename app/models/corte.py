from app.database import db
from datetime import datetime

class RegistroCorte(db.Model):
    __tablename__ = 'registro_corte'
    id = db.Column(db.Integer, primary_key=True)
    comunidad_id = db.Column(db.Integer, db.ForeignKey('comunidad.id'), nullable=False)
    circuito_id = db.Column(db.Integer, db.ForeignKey('circuito_electrico.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    fecha_inicio = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    
    fecha_fin = db.Column(db.Date, nullable=True)
    hora_fin = db.Column(db.Time, nullable=True)
    
    duracion_minutos = db.Column(db.Integer, nullable=True)
    estado = db.Column(db.String(20), default='EN_CORTE') # 'EN_CORTE', 'RESTABLECIDO'

    comunidad = db.relationship('Comunidad', backref='cortes', lazy=True)
    circuito = db.relationship('CircuitoElectrico', backref='cortes', lazy=True)
    usuario = db.relationship('Usuario', backref='cortes', lazy=True)

    def calcular_duracion(self):
        if self.fecha_inicio and self.hora_inicio and self.fecha_fin and self.hora_fin:
            dt_inicio = datetime.combine(self.fecha_inicio, self.hora_inicio)
            dt_fin = datetime.combine(self.fecha_fin, self.hora_fin)
            diff = dt_fin - dt_inicio
            self.duracion_minutos = max(0, int(diff.total_seconds() / 60))

    def to_dict(self):
        return {
            'id': self.id,
            'comunidad_id': self.comunidad_id,
            'comunidad_nombre': self.comunidad.nombre if self.comunidad else '',
            'comuna_nombre': self.comunidad.comuna.nombre if self.comunidad and self.comunidad.comuna else '',
            'circuito_id': self.circuito_id,
            'circuito_nombre': self.circuito.nombre if self.circuito else '',
            'usuario_nombre': self.usuario.nombre_apellido if self.usuario else '',
            'fecha_inicio': self.fecha_inicio.strftime('%Y-%m-%d') if self.fecha_inicio else None,
            'hora_inicio': self.hora_inicio.strftime('%H:%M') if self.hora_inicio else None,
            'fecha_fin': self.fecha_fin.strftime('%Y-%m-%d') if self.fecha_fin else None,
            'hora_fin': self.hora_fin.strftime('%H:%M') if self.hora_fin else None,
            'duracion_minutos': self.duracion_minutos,
            'estado': self.estado
        }