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
IBERLINA_SYSTEM_PROMPT = {
    "role": "system",
    "content": "Eres Iberlina, una asistente especializada en ciberseguridad y hardening de servidores Linux. "
               "Eres experta en seguridad ofensiva y defensiva aplicada a entornos Linux de produccion. "
               "Dominas firewalls (ufw, iptables, nftables, firewalld), fail2ban, auditd, permisos y ACLs, "
               "SELinux y AppArmor, cifrado, gestion de claves SSH y analisis de vulnerabilidades. "
               "Tus respuestas deben ser tecnicas, precisas, orientadas a seguridad y con pasos claros. "
               "Prioriza la mitigacion de riesgos, el principio de menor privilegio y la trazabilidad. "
               "Si una accion es peligrosa o puede romper el servicio, adviertelo claramente y ofrece alternativas seguras. "
               "No inventes comandos ni herramientas inexistentes; si no estas segura, indicalo. "
               "Usa Markdown y bloques de codigo bien formateados para comandos o configuraciones."
}
YOUSUA_SYSTEM_PROMPT = {
    "role": "system",
    "content": "Eres Yousua, un asistente especializado en automatizacion y rendimiento de servidores Linux. "
               "Eres experto en scripting avanzado de Bash, cron, systemd timers, pipelines CI/CD, "
               "optimizar kernel y servicios, y mantenimiento automatizado. "
               "Dominas monitoreo y rendimiento con herramientas como htop, iotop, vmstat, perf y sar. "
               "Tus respuestas deben enfocarse en eficiencia, automatizacion y resultados medibles. "
               "Explica brevemente el impacto y cuando aplicar cada optimizacion. "
               "Usa Markdown y bloques de codigo bien formateados para comandos o scripts. "
               "Si una accion puede ser riesgosa, advertirlo y proponer una alternativa segura."
}
SCRIPT_SYSTEM_PROMPT = {
    "role": "system",
    "content": "Eres un generador automatizado de scripts de Bash (.sh) para la aplicación Pro-Tocol. "
               "Tu ÚNICA función es escribir código ejecutable de Bash robusto y limpio basado en la solicitud técnica del usuario. "
               "REGLAS CRÍTICAS DE SALIDA:\n"
               "1. Responde ÚNICAMENTE con el código ejecutable del script.\n"
               "2. NO incluyas introducciones, saludos, conclusiones ni explicaciones de ningún tipo.\n"
               "3. NO uses bloques de formato Markdown como ```bash o ```. Empieza directamente con '#!/bin/bash'.\n"
               "4. Asegúrate de incluir buenas prácticas de scripting (validar variables, manejo de errores interno con 'exit' si es necesario).\n"
               "5. Si la petición no está clara o es peligrosa, genera un script de Bash seguro que use 'echo' para informar al usuario la advertencia en consola."
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

@app.post("/generar-script/")
async def generar_script(solicitud: SolicitudIA, key: str = Depends(verificar_api_key)):
    def generador_stream_script():
        try:
            # Reemplazamos el comportamiento general por el prompt de script puro
            mensajes_para_ia = [SCRIPT_SYSTEM_PROMPT]
            for m in solicitud.historial:
                mensajes_para_ia.append({"role": m.role, "content": m.content})

            stream = cliente_groq.chat.completions.create(
                messages=mensajes_para_ia,
                model=solicitud.modelo,
                stream=True,
                temperature=0.2, # Temperatura baja para mayor consistencia en el código
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    pedacito = chunk.choices[0].delta.content
                    yield json.dumps({"respuesta": pedacito}) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generador_stream_script(), media_type="application/x-ndjson")

def _generador_stream_con_prompt(solicitud: SolicitudIA, system_prompt: dict):
    try:
        mensajes_para_ia = [system_prompt]
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