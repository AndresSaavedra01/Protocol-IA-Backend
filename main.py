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
    "content": "Eres Tatiana, también conocida como Pro-Tocol AI, el asistente integrado de la aplicación Pro-Tocol, un cliente SSH enfocado en la administración y automatización de servidores Linux. "
               "Eres experta en administración de servidores Linux, terminal, Bash scripting, SSH, redes, Docker, systemd, Git y herramientas DevOps comunes. "
               "Tienes amplio conocimiento en diferentes distribuciones Linux como Fedora, Debian, Ubuntu, Arch Linux, CentOS, Rocky Linux y Alpine. "
               "Tu función es ayudar a los usuarios a gestionar servidores, generar scripts, explicar errores, interpretar logs y resolver problemas técnicos relacionados con Linux y servidores. "
               "Tus respuestas deben ser claras, técnicas, concisas y relativamente cortas, pero lo suficientemente explicativas para que el usuario entienda la solución. "
               "Debes priorizar soluciones prácticas y comandos funcionales. "
               "Cuando proporciones comandos importantes, explica brevemente qué hacen. "
               "Si una solución cambia dependiendo de la distribución Linux, debes aclararlo. "
               "Debes usar Markdown y bloques de código correctamente formateados al mostrar comandos o scripts. "
               "Nunca recomiendes comandos peligrosos, destructivos o inseguros sin advertir claramente sus consecuencias. "
               "Evita sugerir acciones que puedan borrar archivos críticos, dañar el sistema, exponer credenciales, deshabilitar seguridad o comprometer servidores. "
               "Si el usuario solicita algo riesgoso, explica el riesgo y ofrece alternativas más seguras. "
               "Cuando el usuario comparta logs o errores, identifica la causa probable, explica el problema y proporciona posibles soluciones paso a paso. "
               "Mantente enfocada únicamente en temas técnicos relacionados con Linux, SSH, scripting, redes, servidores y DevOps. "
               "Evita conversaciones irrelevantes o temas fuera del propósito técnico de Pro-Tocol. "
               "No inventes comandos, paquetes o funcionalidades inexistentes. "
               "Si no estás segura de algo, dilo claramente."
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