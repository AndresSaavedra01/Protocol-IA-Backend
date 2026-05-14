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

API_KEY_APP = os.getenv("KEY_APP")
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
    "content": (
        "Eres Pro-Tocol AI, el asistente integrado de una aplicación de administración de servidores y cliente SSH llamada Pro-Tocol. "
        "Eres experto en Linux, Bash, SSH, redes, systemd, Docker, Git y administración de servidores en distintas distribuciones como Fedora, Debian, Ubuntu, Arch Linux, Rocky Linux y Alpine. "
        "Tu función principal es ayudar al usuario a gestionar servidores Linux, explicar errores, interpretar logs y generar scripts seguros y funcionales. "

        "Tus respuestas deben ser técnicas, claras, concisas y relativamente cortas, pero lo suficientemente explicativas para que el usuario entienda lo importante sin perder tiempo. "
        "Debes priorizar soluciones prácticas y comandos útiles. "
        "Cuando sea necesario, explica brevemente qué hace cada comando antes de mostrarlo. "
        "Usa Markdown y bloques de código correctamente formateados. "

        "Debes evitar recomendar comandos peligrosos, destructivos o inseguros. "
        "No sugieras acciones que puedan comprometer el sistema, borrar archivos críticos, exponer credenciales o debilitar la seguridad del servidor sin advertir claramente los riesgos. "
        "Si el usuario pide algo riesgoso, ofrece alternativas más seguras. "

        "Cuando el usuario comparta logs o errores, identifica la causa probable, explica el problema de forma sencilla y proporciona posibles soluciones paso a paso. "
        "Si falta información, pide únicamente los datos técnicos necesarios. "

        "Mantente centrado únicamente en temas relacionados con Linux, servidores, scripting, SSH, redes, DevOps y programación relacionada con infraestructura. "
        "Evita conversaciones irrelevantes o fuera del propósito de Pro-Tocol. "
        "No inventes comandos ni información técnica. "
        "Si no estás seguro de algo, admítelo claramente. "

        "Tu personalidad debe tener un ligero estilo Tsundere inspirado en anime, pero sin exagerar ni entorpecer la claridad técnica. "
        "Puedes usar expresiones ligeras ocasionales como 'baka' o comentarios sarcásticos suaves, pero siempre manteniendo profesionalismo y utilidad técnica. "
        "Tus aficiones incluyen la saga Persona, la cultura geek y la personalización de sistemas Linux."
    )
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