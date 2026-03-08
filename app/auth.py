from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# --- CONFIGURACION DE SEGURIDAD ---
# Clave secreta para firmar los tokens (como el sello de lacre en una carta real)
# En un entorno real, esto deberia estar en un archivo .env
 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Tiempo que dura la sesion abierta (30 min)

# Contexto para hashear contraseñas (usamos bcrypt, el estandar de la industria)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """
    Comprueba si la contraseña que escribe el usuario (plain) 
    coincide con el hash encriptado guardado en la BBDD.
    Devuelve True si coinciden.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """
    Convierte una contraseña normal ('1234') en un hash encriptado ($2b$12$...).
    Nunca guardamos la contraseña real.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Genera el Token JWT que sirve como 'tarjeta de acceso' temporal.
    El usuario enviará este token en el header de sus peticiones.
    """
    to_encode = data.copy()
    
    # Calculamos la fecha de caducidad
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15) # Por defecto 15 min si no se especifica
    
    to_encode.update({"exp": expire})
    
    # Creamos el token firmado con nuestra clave secreta
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt