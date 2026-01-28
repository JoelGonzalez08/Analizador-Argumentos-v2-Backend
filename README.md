# Silogia Backend

Backend API para análisis de argumentos con IA.

## Estructura del Proyecto

```
backend/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── arguments.py    # Endpoints de análisis de argumentos
│   │       ├── users.py         # Endpoints de usuarios y autenticación
│   │       └── conversations.py # Endpoints de conversaciones
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py          # Configuración de base de datos
│   │   └── auth.py              # Utilidades de autenticación
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py            # Modelos de SQLAlchemy
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py           # Esquemas de Pydantic
│   └── utils/
│       ├── __init__.py
│       └── features.py          # Utilidades para CRF
├── scripts/
│   ├── create_clean_db.py       # Script para crear base de datos
│   ├── migrate_db.py            # Script de migración
│   ├── query_db.py              # Script para consultas
│   └── test_db.py               # Script de pruebas
├── crf_model_fold_3_7.pkl       # Modelo CRF entrenado
├── silogia_clean.db             # Base de datos SQLite
├── main.py                       # Punto de entrada de la aplicación
├── requirements.txt              # Dependencias de Python
└── .env                          # Variables de entorno

```

## Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno en `.env`:
```
OPENAI_API_KEY=tu_api_key_aqui
DATABASE_URL=sqlite:///./silogia_clean.db
SECRET_KEY=tu_secret_key_aqui
```

4. Inicializar base de datos:
```bash
python scripts/create_clean_db.py
```

## Ejecutar

```bash
python main.py
```

O con uvicorn:
```bash
uvicorn main:app --reload --port 8000
```

## API Endpoints

### Autenticación
- `POST /api/users/register` - Registrar nuevo usuario
- `POST /api/users/login` - Iniciar sesión
- `POST /api/users/logout` - Cerrar sesión
- `GET /api/users/me` - Obtener perfil del usuario actual

### Conversaciones
- `GET /api/conversations` - Listar conversaciones
- `POST /api/conversations` - Crear conversación
- `GET /api/conversations/{id}` - Obtener conversación
- `PUT /api/conversations/{id}` - Actualizar conversación
- `DELETE /api/conversations/{id}` - Eliminar conversación
- `GET /api/conversations/{id}/analyses` - Obtener análisis de una conversación

### Análisis de Argumentos
- `POST /api/arguments/complete-analysis` - Análisis completo (CRF + OpenAI)

## Tecnologías

- **FastAPI**: Framework web
- **SQLAlchemy**: ORM
- **Pydantic**: Validación de datos
- **SQLite**: Base de datos
- **OpenAI**: Generación de sugerencias
- **CRF (sklearn-crfsuite)**: Extracción de argumentos
- **Stanza**: Procesamiento de lenguaje natural

## Desarrollo

Para agregar nuevos endpoints:

1. Crear función en el router apropiado en `app/api/routers/`
2. Definir esquemas en `app/schemas/schemas.py`
3. Agregar modelos si es necesario en `app/models/models.py`
