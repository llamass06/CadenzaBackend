"""
Módulo de Autenticación y Gestión de Usuarios.

Este módulo define los endpoints de la API encargados del registro de usuarios,
la verificación de correos electrónicos mediante SMTP y la generación de 
tokens de acceso (login) mediante OAuth2.
"""

import secrets
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from datetime import timedelta

# Modulos de la bbdd
from app.database import models          
from app.database.database import get_db 
from app import schemas, auth            
from sqlalchemy.orm import Session

router = APIRouter()

# 1. REGISTRO DE USUARIO
@router.post("/register")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en el sistema.
    
    Flujo de ejecución:
    1. Verifica que el correo electrónico no esté ya registrado.
    2. Hashea (encripta) la contraseña introducida por el usuario.
    3. Genera un token seguro y único para la verificación de correo electrónico.
    4. Guarda el nuevo usuario en la base de datos (con estado "no verificado").
    5. Envía un correo electrónico al usuario usando SMTP con un enlace para verificar su cuenta.
    
    Args:
        user (schemas.UserCreate): Los datos del usuario (email, username, password) recibidos del cliente.
        db (Session): Sesión de la base de datos inyectada como dependencia.
        
    Returns:
        dict: Mensaje informativo sobre la creación exitosa del usuario y el envío del correo.
        
    Raises:
        HTTPException: 
            - 400 Si el correo electrónico ya se encuentra registrado.
    """
    # A) Comprobar si existe
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")
    
    # B) Encriptar password y crear token
    hashed_password = auth.get_password_hash(user.password)
    token_verificacion = secrets.token_urlsafe(32)
    
    # C) Crear objeto y guardar
    new_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        is_verified=False,
        verification_token=token_verificacion
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # D) ENVÍO DE CORREO REAL CON SMTP

    email_password = os.getenv("EMAIL_PASSWORD")
    email = os.getenv("EMAIL")

    sender_email = email
    sender_password = email_password
    smtp_server = "smtp.gmail.com"  
    smtp_port = 465  # 465 para SSL o 587 para TLS dependiendo del servidor
    
    link_verificacion = f"http://localhost:8000/api/auth/verify?token={token_verificacion}"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
        <h2 style="color: #00f2ff; background-color: #0a0f1c; padding: 10px; border-radius: 8px;">CADENZA</h2>
        <h3>¡Bienvenido a Cadenza, {user.username}!</h3>
        <p>Para empezar a usar el Estudio Virtual, necesitamos verificar tu correo.</p>
        <a href="{link_verificacion}" style="display: inline-block; padding: 10px 20px; background-color: #00f2ff; color: #000; text-decoration: none; font-weight: bold; border-radius: 5px; margin-top: 15px;">
            Activar mi cuenta
        </a>
        <p style="margin-top: 30px; font-size: 12px; color: #666;">Si el botón no funciona, copia y pega este enlace:<br>{link_verificacion}</p>
    </div>
    """
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verifica tu cuenta en Cadenza 🎹"
    msg["From"] = sender_email
    msg["To"] = user.email
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        # Usamos SMTP_SSL para el puerto 465 (Gmail por defecto)
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, user.email, msg.as_string())
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        
    return {"message": "Usuario creado. Por favor, revisa tu correo para verificar la cuenta."}

# 2. ENDPOINT PARA VERIFICAR EL CORREO (PANTALLA HTML)
@router.get("/verify", response_class=HTMLResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verifica la dirección de correo electrónico del usuario.
    
    Este endpoint se accede mediante el enlace enviado al correo electrónico
    del usuario. Busca al usuario por el token de verificación en la URL,
    y si lo encuentra y es válido, actualiza su estado a "verificado".
    
    Args:
        token (str): El token único de verificación que fue enviado por correo.
        db (Session): Sesión de la base de datos inyectada como dependencia.
        
    Returns:
        HTMLResponse: Una página HTML elegante indicando el resultado de la verificación 
        (éxito o token inválido/caducado).
    """
    user = db.query(models.User).filter(models.User.verification_token == token).first()
    
    # Plantilla HTML para la respuesta visual
    html_template = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verificación Cadenza</title>
        <style>
            body {{ background-color: #0a0f1c; color: #ffffff; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .card {{ background-color: #12182b; padding: 40px; border-radius: 16px; border: 1px solid #1f2937; text-align: center; max-width: 400px; box-shadow: 0 4px 20px rgba(0,242,255,0.1); }}
            h1 {{ color: {color}; margin-bottom: 10px; font-style: italic; text-transform: uppercase; letter-spacing: 2px;}}
            p {{ color: #94a3b8; line-height: 1.5; margin-bottom: 25px;}}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>{titulo}</h1>
            <p>{mensaje}</p>
        </div>
    </body>
    </html>
    """

    if not user:
        return html_template.format(
            color="#ef4444", 
            titulo="Enlace Inválido", 
            mensaje="El enlace de verificación ha caducado o ya ha sido utilizado."
        )
    
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    return html_template.format(
        color="#00f2ff", 
        titulo="¡Cuenta Activada!", 
        mensaje=f"Genial {user.username}, tu correo ha sido verificado correctamente. Ya puedes cerrar esta pestaña e iniciar sesión en Cadenza.",
    )


# 3. LOGIN (CONSEGUIR TOKEN)
@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Endpoint de inicio de sesión para obtener el Token de Acceso JWT.
    
    Valida las credenciales proporcionadas por el usuario (email como username 
    y contraseña) y comprueba que la cuenta esté verificada. Si es correcto, 
    devuelve un token JWT con la información del usuario para la autorización
    en futuros requests.
    
    Args:
        form_data (OAuth2PasswordRequestForm): Formulario estándar de OAuth2 con las credenciales (username/email y password).
        db (Session): Sesión de la base de datos inyectada como dependencia.
        
    Returns:
        dict: Un diccionario con el token de acceso (JWT) y el tipo de token ("bearer").
        
    Raises:
        HTTPException:
            - 401 Si las credenciales (email o contraseña) son incorrectas.
            - 403 Si la cuenta de usuario no ha sido verificada aún.
    """
    # A) Buscar usuario por email
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # B) Verificar password
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # C) Verificar si ha validado su correo
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta aún no está verificada. Revisa tu bandeja de entrada."
        )
    
    # D) Generar Token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={
                "sub": user.email,
                "username": user.username
            }, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}