# Pro-Tocol AI Backend 🚀

Este es el servidor middleware desarrollado con FastAPI para la aplicación móvil Pro-Tocol. Se encarga de gestionar la comunicación con los modelos de lenguaje de Groq, manejar el historial de chat (contexto) y asegurar las peticiones mediante una API Key.

---

# 🛠️ Requisitos Previos

- Python 3.10 o superior (Probado en Fedora con Python 3.14).
- Pip (Gestor de paquetes de Python).
- Una API Key de Groq (Obtenla en https://console.groq.com).

---

# 📦 Instalación y Configuración

Sigue estos pasos en tu terminal para preparar el entorno:

## 1. Clonar o entrar al directorio del proyecto

```bash
cd /ruta/a/tu/proyecto/Protocol-IA-Backend
```

## 2. Crear y activar el entorno virtual

Es importante usar un entorno virtual para evitar conflictos con las librerías del sistema.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Instalar dependencias

Instala las librerías necesarias especificadas en el código:

```bash
pip install fastapi uvicorn groq python-dotenv pydantic
```

## 4. Configurar variables de entorno

Crea un archivo llamado `.env` en la raíz del proyecto:

```bash
touch .env
```

Edita el archivo `.env` y agrega tu llave de Groq:

```env
GROQ_API_KEY=gsk_tu_llave_maestra_de_groq_aqui
```

> **Nota:**  
> El código utiliza la misma llave de Groq para validar la seguridad entre Flutter y FastAPI (`API_KEY_APP = os.getenv("GROQ_API_KEY")`).  
> Asegúrate de que Flutter envíe esta misma llave en el header `X-API-Key`.

---

# 🔥 Ejecución del Servidor

Para que el servidor sea accesible desde tu aplicación móvil (emulador o dispositivo físico), debes exponerlo en la red local.

## Comando para desarrollo

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Explicación de parámetros

- `--host 0.0.0.0`: Permite conexiones externas (no solo localhost).
- `--port 8000`: Puerto de escucha.
- `--reload`: Reinicia el servidor automáticamente al detectar cambios en el código.

---

# 🛡️ Configuración del Firewall (Solo Fedora)

Si usas Fedora, debes abrir el puerto `8000` para permitir el tráfico entrante:

```bash
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

---

# 📡 Endpoints

## `POST /generar/`

Genera una respuesta en streaming con contexto.

### Headers

```http
X-API-Key: Tu GROQ_API_KEY
Content-Type: application/json
```

### Cuerpo de la petición (JSON)

```json
{
  "historial": [
    {
      "role": "user",
      "content": "Hola"
    },
    {
      "role": "assistant",
      "content": "¡No es como si quisiera saludarte o algo así, baka!"
    }
  ],
  "modelo": "llama-3.3-70b-versatile"
}
```

---

# 🤖 Detalles del Asistente

El sistema incluye un `SYSTEM_PROMPT` predefinido que configura a la IA como una asistente Tsundere experta en:

- Administración de servidores (Fedora, Linux, SSH).
- Desarrollo en Flutter.
- Aficiones: Saga Persona y cultura geek.

---

# 📁 Estructura de Archivos Recomendada

```plaintext
Protocol-IA-Backend/
├── .venv/              # Entorno virtual
├── .env                # Variables sensibles (NO SUBIR A GIT)
├── main.py             # Código fuente FastAPI
└── README.md           # Este archivo
```