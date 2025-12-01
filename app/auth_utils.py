"""
Utilidades de autenticación para WorkaTrack.

Aquí centralizamos:
- La generación de tokens JWT.
- La validación/decodificación de esos tokens.
- Un decorador @jwt_required para proteger rutas.

Esta versión incluye información extra de errores para depuración.
"""

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional, Tuple

import jwt
from flask import current_app, request, jsonify, g


def create_access_token(
    user_id: int,
    username: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Genera un token JWT firmado con la SECRET_KEY de Flask.

    - user_id: ID interno del usuario.
    - username: nombre de usuario público.
    - expires_delta: duración del token (por defecto, 12 horas).

    Devuelve un string con el token JWT.
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=12)

    now = datetime.utcnow()
    exp = now + expires_delta

    # IMPORTANTE: PyJWT espera que 'sub' sea string
    payload = {
        "sub": str(user_id),   # subject del token, en string
        "username": username,
        "iat": now,
        "exp": exp,
    }

    secret_key = current_app.config["SECRET_KEY"]
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


def decode_access_token(token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Intenta decodificar/verificar un token JWT.

    Devuelve una tupla (payload, reason):

    - payload: dict con el contenido del token si es válido, o None si falla.
    - reason:  None si todo va bien, o un string con la razón del error
               (ej: 'expired: ...', 'invalid_signature: ...', etc.).
    """
    secret_key = current_app.config["SECRET_KEY"]

    try:
        payload: Dict[str, Any] = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
        )
        return payload, None

    except jwt.ExpiredSignatureError as e:
        return None, f"expired: {str(e)}"

    except jwt.InvalidSignatureError as e:
        return None, f"invalid_signature: {str(e)}"

    except jwt.DecodeError as e:
        return None, f"decode_error: {str(e)}"

    except jwt.InvalidTokenError as e:
        return None, f"invalid_token: {str(e)}"

    except Exception as e:
        return None, f"{e.__class__.__name__}: {str(e)}"


def jwt_required(view_func):
    """
    Decorador para proteger rutas con JWT.

    - Busca el header: Authorization: Bearer <token>
    - Valida el token.
    - Si es correcto, guarda datos del usuario en flask.g.
    - Si no es correcto, devuelve 401 con 'detail' y 'reason'.
    """

    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return (
                jsonify(
                    {
                        "detail": "Missing or invalid Authorization header. Use: 'Authorization: Bearer <token>'",
                        "reason": "header_not_starting_with_bearer",
                    }
                ),
                401,
            )

        token = auth_header.split(" ", 1)[1].strip()

        payload, reason = decode_access_token(token)

        if payload is None:
            return (
                jsonify(
                    {
                        "detail": "Invalid or expired token.",
                        "reason": reason,
                    }
                ),
                401,
            )

        # 'sub' viene como string en el token → lo convertimos a int para usarlo en la app
        sub = payload.get("sub")
        try:
            g.current_user_id = int(sub) if sub is not None else None
        except (TypeError, ValueError):
            g.current_user_id = None

        g.current_username = payload.get("username")
        g.current_token_payload = payload

        return view_func(*args, **kwargs)

    return wrapped_view
