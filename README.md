# Silogia Studio API - Backend

<div align="center">

**API REST para análisis inteligente de argumentos académicos y generación de sugerencias con IA**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-412991?logo=openai)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Características](#características) •
[Instalación](#instalación) •
[Configuración](#configuración) •
[API](#documentación-de-la-api) •
[Deployment](#deployment)

</div>

---

## Descripción

**Silogia Studio API** es un backend robusto y escalable diseñado para analizar argumentos en textos académicos utilizando técnicas de machine learning (CRF) y modelos de lenguaje (OpenAI GPT-3.5). El sistema identifica premisas y conclusiones, y proporciona sugerencias personalizadas para mejorar la calidad argumentativa.

### ¿Para quién es esto?

- **Estudiantes** que buscan mejorar la calidad de sus argumentos académicos
- **Educadores** que desean herramientas para analizar ensayos y trabajos
- **Investigadores** interesados en análisis automático de argumentación
- **Desarrolladores** que necesitan APIs de análisis de texto

---

## Características

- **Análisis de argumentos con CRF**: Extracción automática de premisas y conclusiones
- **Sugerencias con IA**: Recomendaciones personalizadas usando GPT-3.5
- **Sistema de autenticación**: Registro, login y gestión de sesiones seguras
- **Gestión de conversaciones**: Historial completo de análisis por usuario
- **Persistencia de datos**: Base de datos SQLite con SQLAlchemy ORM
- **CORS configurable**: Control de acceso mediante variables de entorno
- **Documentación automática**: Swagger UI y ReDoc integrados
- **Producción lista**: Deploy-ready con guía completa para VPS

---

## Stack Tecnológico

### Core Framework
- **[FastAPI](https://fastapi.tiangolo.com/)** - Framework web moderno y de alto rendimiento
- **[Uvicorn](https://www.uvicorn.org/)** - Servidor ASGI ultrarrápido

### Base de Datos
- **[SQLAlchemy](https://www.sqlalchemy.org/)** - ORM para Python
- **SQLite** - Base de datos relacional ligera

### Machine Learning & NLP
- **[OpenAI](https://openai.com/)** - GPT-3.5 para generación de sugerencias
- **[sklearn-crfsuite](https://sklearn-crfsuite.readthedocs.io/)** - Modelo CRF preentrenado
- **[Stanza](https://stanfordnlp.github.io/stanza/)** - Procesamiento de lenguaje natural
- **[spaCy](https://spacy.io/)** - Análisis lingüístico avanzado
- **[scikit-learn](https://scikit-learn.org/)** - Toolkit de machine learning

### Seguridad & Validación
- **[Pydantic](https://docs.pydantic.dev/)** - Validación de datos con tipos
- **[python-jose](https://python-jose.readthedocs.io/)** - JWT tokens
- **[Passlib](https://passlib.readthedocs.io/)** - Hash de contraseñas con bcrypt

---

## Requisitos Previos

- **Python 3.10+** instalado
- **pip** (gestor de paquetes de Python)
- **Cuenta de OpenAI** con API Key activa
- **Git** (opcional, para clonar el repositorio)

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/JoelGonzalez08/Analizador-Argumentos-v2-Backend.git

cd Analizador-Argumentos-v2-Backend
```

### 2. Crear y activar entorno virtual

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Descargar modelos de NLP (primera vez)

```bash
python -c "import stanza; stanza.download('es')"
```

---

## Configuración

### 1. Crear archivo `.env`

Crea un archivo `.env` en la raíz del proyecto basándote en `.env.example`:

```bash
cp .env.example .env  # Linux/macOS
copy .env.example .env  # Windows
```

### 2. Configurar variables de entorno

Edita el archivo `.env`:

```env

# CORS - URLs permitidas (OBLIGATORIO)

CORS_ORIGINS=http://localhost:3000,http://localhost:9002
```

**IMPORTANTE:**
- `CORS_ORIGINS` es **obligatorio** - el servidor no arrancará sin él
- Separa múltiples URLs con comas (sin espacios)
- Incluye el protocolo (`http://` o `https://`)
- NO termines las URLs con `/`

### 3. Inicializar la base de datos

La base de datos se crea automáticamente al iniciar el servidor por primera vez.

---

## Uso

### Ejecutar el servidor de desarrollo

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

O simplemente:

```bash
python main.py
```

El servidor estará disponible en:
- **API:** http://localhost:8000
- **Documentación interactiva (Swagger):** http://localhost:8000/docs
- **Documentación alternativa (ReDoc):** http://localhost:8000/redoc

---

## Documentación de la API

### Health Check

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Estado de la API |
| `GET` | `/health` | Health check |

---

### Usuarios y Autenticación

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| `POST` | `/api/users/register` | Registrar nuevo usuario | No |
| `POST` | `/api/users/login` | Iniciar sesión (obtener token) | No |
| `POST` | `/api/users/logout` | Cerrar sesión | Sí |
| `GET` | `/api/users/me` | Obtener perfil del usuario actual | Sí |
| `PUT` | `/api/users/me` | Actualizar perfil del usuario | Sí |
| `GET` | `/api/users/{user_id}` | Obtener perfil de usuario por ID | Sí |
| `DELETE` | `/api/users/{user_id}` | Eliminar cuenta de usuario | Sí |
| `GET` | `/api/users/{user_id}/conversations` | Conversaciones de un usuario | Sí |

---

### Conversaciones

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| `GET` | `/api/conversations` | Listar conversaciones del usuario | Sí |
| `POST` | `/api/conversations` | Crear nueva conversación | Sí |
| `GET` | `/api/conversations/{id}` | Obtener conversación con mensajes | Sí |
| `PUT` | `/api/conversations/{id}` | Actualizar título de conversación | Sí |
| `DELETE` | `/api/conversations/{id}` | Eliminar conversación | Sí |
| `GET` | `/api/conversations/{id}/messages` | Obtener mensajes de conversación | Sí |
| `POST` | `/api/conversations/{id}/messages` | Agregar mensaje a conversación | Sí |
| `GET` | `/api/conversations/{id}/analyses` | Análisis de una conversación | Sí |

---

### Análisis de Argumentos

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| `POST` | `/api/arguments/analyze` | Analizar texto completo (CRF + OpenAI) | Sí |
| `POST` | `/api/arguments/recommendations` | Obtener solo recomendaciones | Sí |
| `GET` | `/api/arguments/history` | Historial de análisis | Sí |

#### Ejemplo de petición: Análisis completo

```bash
curl -X POST "http://localhost:8000/api/arguments/analyze" \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": 1,
    "text": "La educación es fundamental para el desarrollo. Por lo tanto, debemos invertir más en escuelas.",
    "include_recommendations": true
  }'
```

#### Respuesta:

```json
{
  "id": 1,
  "conversation_id": 1,
  "components": [
    {
      "id": 1,
      "text": "La educación es fundamental para el desarrollo.",
      "component_type": "premise",
      "start_char": 0,
      "end_char": 47
    },
    {
      "id": 2,
      "text": "debemos invertir más en escuelas",
      "component_type": "conclusion",
      "start_char": 65,
      "end_char": 98
    }
  ],
  "llm_suggestions": [
    {
      "component_id": 1,
      "suggestion": "Agrega datos estadísticos para respaldar esta premisa.",
      "suggestion_type": "improvement"
    }
  ]
}
```

---

## Estructura del Proyecto

```
Analizador-Argumentos-v2-Backend/
│
├── app/                             # Código principal de la aplicación
│   ├── api/                         # Capa de API
│   │   └── routers/                 # Endpoints organizados por dominio
│   │       ├── arguments.py         # Análisis de argumentos
│   │       ├── users.py             # Autenticación y usuarios
│   │       └── conversations.py     # Gestión de conversaciones
│   │
│   ├── core/                        # Configuración y utilidades core
│   │   ├── auth.py                  # Autenticación JWT
│   │   └── database.py              # Conexión a base de datos
│   │
│   ├── models/                      # Modelos de base de datos
│   │   └── models.py                # Modelos SQLAlchemy
│   │
│   ├── schemas/                     # Validación y serialización
│   │   └── schemas.py               # Esquemas Pydantic
│   │
│   ├── services/                    # Lógica de negocio
│   │   ├── argument_service.py      # Servicio de análisis CRF
│   │   ├── llm_service.py           # Servicio OpenAI
│   │   └── paragraph_service.py     # Procesamiento de párrafos
│   │
│   ├── repositories/                # Acceso a datos
│   │   └── analysis_repository.py   # Repositorio de análisis
│   │
│   └── utils/                       # Utilidades generales
│       └── features.py              # Extracción de features para CRF
│
├── main.py                          # Punto de entrada de la aplicación
├── requirements.txt                 # Dependencias de Python
├── .env                             # Variables de entorno (no subir a git)
├── .env.example                     # Template de variables de entorno
├── .gitignore                       # Archivos ignorados por Git
├── README.md                        # Este archivo
├── DEPLOYMENT.md                    # Guía de deployment a VPS
├── LICENSE                          # Licencia del proyecto
│
├── crf_model_fold_3_7.pkl           # Modelo CRF preentrenado
└── silogia.db                       # Base de datos SQLite (generada)
```

---

## Seguridad

### Implementaciones de Seguridad

- **CORS configurado dinámicamente**: Solo las URLs en `CORS_ORIGINS` pueden acceder
- **Autenticación JWT**: Tokens seguros para sesiones
- **Hash de contraseñas**: Bcrypt para almacenamiento seguro
- **Variables de entorno**: Credenciales fuera del código fuente
- **Validación de datos**: Pydantic valida todas las entradas
- **`.env` en `.gitignore`**: Secretos no se suben al repositorio

### Recomendaciones para Producción

- **Usa HTTPS siempre** (Let's Encrypt es gratis)
- **Configura rate limiting** para prevenir abuso
- **Monitorea logs** para detectar actividad sospechosa
- **Mantén dependencias actualizadas** (`pip list --outdated`)
- **Haz backups regulares** de la base de datos

---

## Deployment

Para hacer deploy del backend a un VPS (servidor privado virtual), consulta la **[Guía Completa de Deployment](DEPLOYMENT.md)**.

La guía incluye:
- Configuración del servidor
- Instalación de dependencias
- Configuración de Nginx como reverse proxy
- Certificado SSL con Let's Encrypt
- Systemd service para auto-inicio
- Seguridad y firewall
- Troubleshooting común

### Quick Start (Producción)

```bash
# 1. Clonar repositorio en el VPS
git clone <url-repo>
cd Analizador-Argumentos-v2-Backend

# 2. Configurar .env con tu URL de producción
echo "CORS_ORIGINS=https://tu-app.vercel.app" >> .env
echo "API_KEY=tu-api-key" >> .env

# 3. Instalar dependencias
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Ejecutar
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Testing

```bash
# Verificar que el servidor esté corriendo
curl http://localhost:8000/health

# Probar registro de usuario
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","username":"testuser"}'
```

---

## Contribución

Las contribuciones son bienvenidas. Para contribuir:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

---

## Soporte

Si encuentras algún problema o tienes preguntas:

1. Revisa la [documentación interactiva](http://localhost:8000/docs) mientras el servidor está corriendo
2. Consulta el archivo [DEPLOYMENT.md](DEPLOYMENT.md) para problemas de deployment
3. Abre un issue en el repositorio

---

<div align="center">

**Hecho para mejorar la argumentación académica**

Si te gusta este proyecto, dale una estrella en GitHub

</div>
