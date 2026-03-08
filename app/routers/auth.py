from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

# Importamos nuestros modulos (ajustados a tu estructura de carpetas)
from app.database import models          
from app.database.database import get_db 
from app import schemas, auth            

router = APIRouter()

# 1. REGISTRO DE USUARIO
@router.post("/register", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario:
    1. Verifica que el email no exista.
    2. Encripta la contraseña.
    3. Guarda en BBDD.
    """
    # A) Comprobar si existe
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")
    
    # B) Encriptar password
    hashed_password = auth.get_password_hash(user.password)
    
    # C) Crear objeto y guardar
    new_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

# 2. LOGIN (CONSEGUIR TOKEN)
@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Valida usuario/contraseña y devuelve el Token de acceso.
    """
    # A) Buscar usuario por email (form_data usa el campo 'username' para recibirlo)
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # B) Verificar password
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # C) Generar Token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}