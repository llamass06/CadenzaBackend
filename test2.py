import os
from dotenv import load_dotenv

load_dotenv()
base_url = os.getenv("BASE_URL")

from app.database import models
from app.database.database import SessionLocal

def test():
    db = SessionLocal()
    canciones = db.query(models.Song).all()
    resultado = []
    for c in canciones:
        backing_url = f"{base_url}/files/{c.path_backing}" if c.path_backing else None
        resultado.append(backing_url)
    print("BACKING URLS:", resultado)

test()
