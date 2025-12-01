"""
Servicios relacionados con usuarios.

Aquí concentramos toda la lógica de negocio de usuarios:
- Crear un usuario nuevo.
- Recuperar usuarios por ID.
- Autenticar usuarios (login).
"""

from app.models import db, User


def create_user(email: str, password: str, nombre: str | None, username: str) -> User:
    """
    Crea un nuevo usuario con username único y email único.
    """

    # Comprobar username único
    existing_username = User.query.filter_by(username=username).first()
    if existing_username:
        raise ValueError("Ese nombre de usuario ya está en uso")

    # Comprobar email único
    existing_email = User.query.filter_by(email=email).first()
    if existing_email:
        raise ValueError("Ese correo ya está registrado")

    # Crear usuario
    user = User(
        email=email,
        nombre=nombre,
        username=username,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return user


def get_user_by_id(user_id: int) -> User | None:
    """
    Devuelve el usuario con ese ID o None si no existe.
    """
    return User.query.get(user_id)


def authenticate_user(username: str, password: str) -> User:
    """
    Autentica un usuario por username y contraseña.

    - Si el username no existe o la contraseña no coincide, lanza ValueError.
    - Si todo está bien, devuelve el objeto User.
    """
    # Buscamos el usuario por su username único
    user = User.query.filter_by(username=username).first()

    # Si no existe o la contraseña no es correcta, devolvemos error genérico
    if user is None or not user.check_password(password):
        raise ValueError("Credenciales inválidas")

    return user
