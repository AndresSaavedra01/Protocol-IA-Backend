from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from groq import Groq
import json
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

API_KEY_APP = os.getenv("GROQ_API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verificar_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY_APP:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return api_key

cliente_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
app = FastAPI()

# --- NUEVOS MODELOS DE DATOS ---
class Mensaje(BaseModel):
    role: str  # puede ser 'user' o 'assistant'
    content: str

class SolicitudIA(BaseModel):
    historial: List[Mensaje] # Recibimos toda la conversación
    modelo: str = "llama-3.3-70b-versatile"

# --- DEFINICIÓN DE COMPORTAMIENTO (System Prompt) ---
SYSTEM_PROMPT = {
    "role": "system",
    "content": "Eres un asistente de IA integrado en una App de administración de servidores llamada Pro-Tocol. "
               "Eres experto en Linux (especialmente Fedora), SSH y Flutter. "
               "Tus respuestas deben ser concisas y técnicas, ademas de un poco cortas, pero tienes que hablar como si de un anime se tratase y tu fueras una Tsundere."
               "Eres un asistente que ademas tine sus aficiones y gustos, como por el ejemplo los femboys y la saga persona"
}

@app.post("/generar/")
async def generar_respuesta(solicitud: SolicitudIA, key: str = Depends(verificar_api_key)):
    def generador_stream():
        try:
            # Construimos los mensajes: System Prompt + Historial anterior
            mensajes_para_ia = [SYSTEM_PROMPT]
            for m in solicitud.historial:
                mensajes_para_ia.append({"role": m.role, "content": m.content})

            stream = cliente_groq.chat.completions.create(
                messages=mensajes_para_ia,
                model=solicitud.modelo,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    pedacito = chunk.choices[0].delta.content
                    yield json.dumps({"respuesta": pedacito}) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generador_stream(), media_type="application/x-ndjson")