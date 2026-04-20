import os
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar la clave
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Modelos disponibles para generar texto:")
print("-" * 40)

# Recorremos la lista de modelos de tu cuenta
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)