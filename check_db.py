from app import create_app
from app.database import db
from app.models.usuario import Usuario

app = create_app()

with app.app_context():
    cedula_admin = "11793938"  # Puedes cambiar esta cédula por la que desees
    usuario_admin = Usuario.query.filter_by(cedula=cedula_admin).first()

    if not usuario_admin:
        usuario_admin = Usuario(
            cedula=cedula_admin,
            nombre_apellido="Omar Briceño (Admin Web)",
            telefono="04120000000",
            rol=1,  # Perfil 1: Coordinador General / Administrador
            comuna_id=1
        )
        usuario_admin.set_password(cedula_admin)
        db.session.add(usuario_admin)
        print(f"✅ Creado usuario Administrador Web con Cédula: {cedula_admin}")
    else:
        usuario_admin.rol = 1
        usuario_admin.nombre_apellido = "Omar Briceño (Admin Web)"
        print(f"🔄 Usuario {cedula_admin} actualizado a Perfil 1 (Admin Web)")

    db.session.commit()