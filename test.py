import httpx
import asyncio
from app.database import models
from app.database.database import SessionLocal

def main():
    db = SessionLocal()
    canciones = db.query(models.Song).all()
    print("DB songs:")
    for c in canciones:
        print(f"ID: {c.id}, path_backing: {c.path_backing}")

if __name__ == '__main__':
    main()
