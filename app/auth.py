"""
Módulo de autenticación y seguridad de la aplicación.

Este módulo centraliza toda la lógica de seguridad del backend:
- Hashing de contraseñas con bcrypt.
- Generación y firma de tokens de acceso JWT.
- Validación de tokens entrantes y resolución del usuario autenticado.

Las funciones de este módulo son usadas tanto por los endpoints de autenticación
(app/routers/auth.py) como por los endpoints protegidos de toda la API, que
dependen de `get_current_user` para identificar al usuario que hace cada petición.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import os

# Dependencias de FastAPI y SQLAlchemy para el sistema de inyección de dependencias
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import models
from app.database.database import get_db

# --- CONFIGURACIÓN DE SEGURIDAD ---

# Clave secreta cargada desde variables de entorno para firmar y verificar los tokens JWT.
# Si esta clave se filtra, cualquier persona podría forjar tokens válidos, así que NUNCA
# debe quedar hardcodeada en el código fuente.
secret_key = os.getenv("SECRET_KEY")

# Algoritmo de firma del token. HS256 (HMAC con SHA-256) es el estándar más usado para JWT.
ALGORITHM = "HS256"

# Tiempo de vida de la sesión en minutos. Tras este tiempo el token caduca y el usuario
# deberá volver a iniciar sesión.
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Esquema OAuth2: indica a FastAPI dónde se generan los tokens (endpoint /api/auth/token).
# Esto activa el botón "Authorize" en la documentación interactiva de Swagger (/docs).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def verify_password(plain_password, hashed_password):
    """
    Verifica si una contraseña en texto plano coincide con su hash almacenado en la BBDD.
    
    Utiliza bcrypt.checkpw, que internamente aplica la misma sal (salt) que se usó al
    generar el hash original y compara el resultado de forma segura, resistente a
    ataques de temporización.
    
    Args:
        plain_password (str): Contraseña introducida por el usuario en el formulario de login.
        hashed_password (str): Hash bcrypt almacenado en la base de datos para ese usuario.
        
    Returns:
        bool: True si la contraseña es correcta, False en caso contrario.
    """
    # bcrypt requiere que las cadenas estén en bytes antes de procesarlas
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    """
    Genera el hash bcrypt de una contraseña en texto plano para almacenarla de forma segura.
    
    Bcrypt genera automáticamente una sal (salt) aleatoria en cada llamada, lo que
    garantiza que dos usuarios con la misma contraseña tendrán hashes diferentes. 
    La contraseña original nunca se almacena en la base de datos.
    
    Args:
        password (str): Contraseña en texto plano introducida por el usuario en el registro.
        
    Returns:
        str: Hash bcrypt en formato string listo para ser guardado en la BBDD.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')  # Se decodifica de bytes a str para compatibilidad con SQLAlchemy

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Genera un token JWT firmado que actúa como credencial de acceso temporal para el usuario.
    
    El token incluye los datos del usuario (email, username) y un campo 'exp' con la
    fecha de caducidad. Está firmado con `secret_key` usando el algoritmo HS256, lo que
    garantiza que no puede ser modificado sin invalidar la firma.
    
    Args:
        data (dict): Payload del token. Debe incluir al menos 'sub' (email del usuario).
        expires_delta (Optional[timedelta]): Duración de validez del token. Si no se
                                             proporciona, el token caduca en 15 minutos.
                                             
    Returns:
        str: Token JWT codificado y firmado, listo para enviar al cliente.
    """
    to_encode = data.copy()
    
    # Calcular la fecha exacta de caducidad del token
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Fallback si no se especifica duración
    
    # El campo estándar JWT para la caducidad es 'exp'
    to_encode.update({"exp": expire})
    
    # Firmar y codificar el token con la clave secreta
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependencia de FastAPI que autentica al usuario a partir del token JWT de la petición.
    
    Esta función actúa como un middleware de autenticación: se inyecta en los endpoints
    protegidos y, antes de ejecutar su lógica, extrae y valida el token del header
    'Authorization: Bearer <token>'. Si el token es válido, devuelve el objeto User
    completo; si no, lanza una excepción 401 automáticamente.
    
    Args:
        token (str): Token JWT extraído automáticamente del header de la petición por oauth2_scheme.
        db (Session): Sesión de la base de datos inyectada como dependencia.
        
    Returns:
        models.User: Objeto User completo del usuario autenticado (con id, email, username, etc.).
        
    Raises:
        HTTPException: 401 si el token es inválido, ha caducado, ha sido manipulado,
                       o si el usuario ya no existe en la base de datos.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales (Token inválido o caducado)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 1. Descifrar y validar la firma del token con la clave secreta
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        
        # 2. Extraer el email del payload (almacenado bajo la clave estándar 'sub')
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        # El token está caducado, su firma no es válida o ha sido manipulado
        raise credentials_exception
        
    # 3. Verificar que el usuario todavía existe en la base de datos
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
        
    # 4. Devolver el objeto usuario completo para que el endpoint lo use
    return user