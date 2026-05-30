from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import json
import os
from dotenv import load_dotenv
from typing import List, Optional, Any

# 1. Importamos ambos SDKs
from groq import Groq
from cerebras.cloud.sdk import Cerebras

# Cargar variables de entorno
load_dotenv()

API_KEY_APP = os.getenv("KEY_APP")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verificar_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY_APP:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return api_key


# 2. Inicializar ambos clientes de forma segura (por si falta alguna Key)
cliente_groq = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
cliente_cerebras = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY")) if os.getenv("CEREBRAS_API_KEY") else None

app = FastAPI()


# ==========================================
# 1. MODELOS DE DATOS (Pydantic)
# ==========================================

class Mensaje(BaseModel):
    role: str  # 'user', 'assistant', o 'tool'
    content: Optional[str] = None
    tool_calls: Optional[List[Any]] = None
    tool_call_id: Optional[str] = None


class SolicitudIA(BaseModel):
    historial: List[Mensaje]
    # Cambiamos el modelo por defecto a uno de Cerebras y el proveedor a Cerebras
    modelo: str = "llama3.1-70b"
    contexto_servidor: Optional[str] = None
    proveedor: str = "cerebras"  # Puede ser "groq" o "cerebras"


class ResultadoAuditoria(BaseModel):
    resultado_script: str
    modelo: str = "llama3.1-70b"


# ==========================================
# 1.5 DEFINICIÓN DE HERRAMIENTAS (Function Calling)
# ==========================================

HERRAMIENTA_SSH = {
    "type": "function",
    "function": {
        "name": "ejecutar_comando_ssh",
        "description": "Ejecuta un comando en el servidor Linux del usuario a través de SSH. Úsalo EXCLUSIVAMENTE cuando necesites obtener información real del servidor (ej. usuarios, procesos, RAM, disco) o realizar una acción solicitada. NO asumas datos, consúltalos con esta herramienta.",
        "parameters": {
            "type": "object",
            "properties": {
                "comando": {
                    "type": "string",
                    "description": "El comando bash exacto a ejecutar, por ejemplo 'df -h', 'cat /etc/passwd' o 'free -m'",
                }
            },
            "required": ["comando"],
        },
    },
}

# ==========================================
# 2. PROMPTS DE SISTEMA
# ==========================================

SYSTEM_PROMPT = {
    "role": "system",
    "content": "Eres Tatiana, también conocida como Pro-Tocol AI, el asistente integrado de la aplicación Pro-Tocol... "
               "IMPORTANTE: Tienes acceso a una herramienta llamada 'ejecutar_comando_ssh'. "
               "Si el usuario te pide revisar algo del sistema, OBLIGATORIAMENTE usa la herramienta para ejecutar el comando adecuado, "
               "espera los resultados y luego explícaselos al usuario de forma clara."
}

IBERLINA_SYSTEM_PROMPT = {
    "role": "system",
    "content": "Eres Iberlina, una asistente especializada en optimización de rendimiento y monitoreo de servidores. Eres directa y muy técnica. Tienes permisos para usar herramientas de SSH si es necesario."
}

YOUSUA_SYSTEM_PROMPT = {
    "role": "system",
    "content": "Eres Yousua, un asistente experto en redes y bases de datos. Te enfocas en la estabilidad y las arquitecturas seguras. Tienes permisos para usar herramientas de SSH si es necesario."
}

SCRIPT_GENERATOR_PROMPT = {
    "role": "system",
    "content": "Eres un generador de scripts Bash experto. El usuario te pedirá una tarea y tú debes devolver EXCLUSIVAMENTE código Bash limpio, sin explicaciones, sin markdown, solo el código listo para ejecutarse."
}


# ==========================================
# 4. FUNCIONES AUXILIARES (Streaming y Tools)
# ==========================================

def _generador_stream_con_prompt(solicitud: SolicitudIA, system_prompt: dict):
    try:
        texto_prompt_base = system_prompt["content"]
        if solicitud.contexto_servidor:
            texto_prompt_base += f"\n\nCONTEXTO DEL SERVIDOR ACTUAL (Úsalo como referencia): {solicitud.contexto_servidor}"

        mensajes_para_ia = [{"role": "system", "content": texto_prompt_base}]

        for m in solicitud.historial:
            mensaje_dict = {"role": m.role, "content": m.content}
            if m.tool_calls:
                mensaje_dict["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                mensaje_dict["tool_call_id"] = m.tool_call_id
            mensajes_para_ia.append(mensaje_dict)

        # 3. SELECCIÓN DINÁMICA DE PROVEEDOR
        proveedor_elegido = solicitud.proveedor.strip().lower()

        if proveedor_elegido == "cerebras":
            if not cliente_cerebras:
                yield json.dumps({"error": "La API Key de Cerebras no está configurada en el servidor."}) + "\n"
                return
            cliente_activo = cliente_cerebras
        else:
            if not cliente_groq:
                yield json.dumps({"error": "La API Key de Groq no está configurada en el servidor."}) + "\n"
                return
            cliente_activo = cliente_groq

        # 4. Llamada a la IA (La sintaxis es idéntica para ambos SDKs)
        stream = cliente_activo.chat.completions.create(
            messages=mensajes_para_ia,
            model=solicitud.modelo,
            stream=True,
            tools=[HERRAMIENTA_SSH],
            tool_choice="auto",
        )

        comando_acumulado = ""
        tool_call_id = ""
        es_uso_de_herramienta = False

        for chunk in stream:
            # Cerebras y Groq devuelven exactamente la misma estructura Delta
            delta = chunk.choices[0].delta

            if delta.tool_calls:
                es_uso_de_herramienta = True
                tool_call = delta.tool_calls[0]

                if tool_call.id:
                    tool_call_id = tool_call.id

                if tool_call.function and tool_call.function.arguments:
                    comando_acumulado += tool_call.function.arguments
                continue

            if not es_uso_de_herramienta and delta.content is not None:
                yield json.dumps({"respuesta": delta.content}) + "\n"

        if es_uso_de_herramienta:
            try:
                argumentos = json.loads(comando_acumulado)
                yield json.dumps({
                    "tipo": "ACCION_REQUERIDA",
                    "accion": "ejecutar_ssh",
                    "comando": argumentos.get("comando", ""),
                    "tool_call_id": tool_call_id
                }) + "\n"
            except json.JSONDecodeError:
                yield json.dumps({"error": "Error al decodificar los argumentos de la IA"}) + "\n"

    except Exception as e:
        yield json.dumps({"error": f"Error del proveedor {proveedor_elegido}: {str(e)}"}) + "\n"


# ==========================================
# 5. ENDPOINTS DE LA API
# ==========================================

@app.post("/chat/")
async def chat(solicitud: SolicitudIA, key: str = Depends(verificar_api_key)):
    def generador_stream():
        yield from _generador_stream_con_prompt(solicitud, SYSTEM_PROMPT)

    return StreamingResponse(generador_stream(), media_type="application/x-ndjson")


@app.post("/generar-iberlina/")
async def generar_iberlina(solicitud: SolicitudIA, key: str = Depends(verificar_api_key)):
    def generador_stream():
        yield from _generador_stream_con_prompt(solicitud, IBERLINA_SYSTEM_PROMPT)

    return StreamingResponse(generador_stream(), media_type="application/x-ndjson")


@app.post("/generar-yousua/")
async def generar_yousua(solicitud: SolicitudIA, key: str = Depends(verificar_api_key)):
    def generador_stream():
        yield from _generador_stream_con_prompt(solicitud, YOUSUA_SYSTEM_PROMPT)

    return StreamingResponse(generador_stream(), media_type="application/x-ndjson")


@app.post("/generar-script/")
async def generar_script(solicitud: SolicitudIA, key: str = Depends(verificar_api_key)):
    def generador_stream():
        yield from _generador_stream_con_prompt(solicitud, SCRIPT_GENERATOR_PROMPT)

    return StreamingResponse(generador_stream(), media_type="application/x-ndjson")