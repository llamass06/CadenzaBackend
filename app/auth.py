from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt

# Importaciones nuevas para leer el Token e ir a la BBDD
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import models
from app.database.database import get_db

# --- CONFIGURACION DE SEGURIDAD ---
# Clave secreta para firmar los tokens (como el sello de lacre en una carta real)
# TODO: En el futuro, mover esto a un archivo oculto .env
SECRET_KEY = "CLAVE_SUPER_SECRETA_PARA_EL_TFG_CADENZA" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Tiempo que dura la sesion abierta (30 min)

# Le indicamos a FastAPI en qué ruta se "fabrican" los tokens
# Esto hará que aparezca el botón verde "Authorize" en tu Swagger (/docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def verify_password(plain_password, hashed_password):
    """
    Comprueba si la contraseña que escribe el usuario (plain) 
    coincide con el hash encriptado guardado en la BBDD.
    Devuelve True si coinciden.
    """
    # Bcrypt requiere que los textos se conviertan a bytes con .encode('utf-8')
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    """
    Convierte una contraseña normal ('1234') en un hash encriptado ($2b$12$...).
    Nunca guardamos la contraseña real.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8') # Lo decodificamos a string para guardarlo en la BBDD

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

# --- NUEVA FUNCION: EL LECTOR DE TARJETAS VIP ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Esta función intercepta la petición, lee el Token JWT del header, 
    lo descifra y busca al usuario en la base de datos.
    Si el token es inválido o el usuario no existe, lanza un error 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales (Token inválido o caducado)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 1. Intentamos descifrar el token usando nuestra SECRET_KEY
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 2. Extraemos el email (que guardamos bajo la clave 'sub' al hacer login)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        # Si el token está caducado, roto o manipulado, saltará por aquí
        raise credentials_exception
        
    # 3. Buscamos al usuario en la base de datos
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
        
    # 4. Devolvemos el objeto usuario completo (con su ID, email, etc.)
    return user