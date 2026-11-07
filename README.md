# 🌋 Turismo GT

![CI/CD](https://github.com/AlexP3rez/turismo-gt/actions/workflows/ci.yml/badge.svg)

Aplicación web con **servicios de Inteligencia Artificial** para planificar viajes por Guatemala. Proyecto final del curso de Programación Comercial.

| | |
|---|---|
| **Aplicación** | https://turismo-gt-web.onrender.com |
| **API / Swagger** | https://turismo-gt.onrender.com/docs |
| **Repositorio** | https://github.com/AlexP3rez/turismo-gt |

> **Nota:** la API corre en el plan gratuito de Render, que la duerme tras 15 minutos sin uso. La primera petición puede tardar hasta ~50 segundos. Abre `/health` antes de una demostración.

## Contenido

1. [Servicios de IA](#servicios-de-ia)
2. [Arquitectura](#arquitectura)
3. [Tecnologías](#tecnologías)
4. [Estructura del repositorio](#estructura-del-repositorio)
5. [Puesta en marcha local](#puesta-en-marcha-local)
6. [Variables de entorno](#variables-de-entorno)
7. [Usuarios y roles](#usuarios-y-roles)
8. [API REST](#api-rest)
9. [Control de consumo de tokens](#control-de-consumo-de-tokens)
10. [Pruebas](#pruebas)
11. [CI/CD y despliegue](#cicd-y-despliegue)
12. [Consumo externo: Postman y Power BI](#consumo-externo-postman-y-power-bi)
13. [Solución de problemas](#solución-de-problemas)
14. [Autores](#autores)

## Servicios de IA

| # | Servicio | Qué hace |
|---|---|---|
| 1 | **Chatbot RAG** (`POST /ai/chat`) | Responde con información de los destinos y actividades registrados en la base de datos (búsqueda vectorial con pgvector). Cita las fuentes, avisa cuando no hay información suficiente y mantiene memoria de la conversación. |
| 2 | **Agente planificador de itinerarios** (`POST /ai/itinerary`) | Según los intereses, los días y el presupuesto, busca actividades, consulta el clima y las distancias, calcula costos y arma un itinerario. |
| 3 | **Agente ajustador de plan** (`POST /ai/adjust-plan`) | Recibe un plan y un cambio (presupuesto o clima), busca alternativas y reajusta las actividades. |

Los agentes usan un bucle propio de *tool calling* (máximo 6 pasos) con estas herramientas: `listar_destinos`, `buscar_actividades`, `consultar_clima` (Open-Meteo), `calcular_distancia` (OSRM), `buscar_lugares_externos` (OpenStreetMap/Nominatim) y `calcular_costo_plan`. La respuesta incluye los **pasos intermedios** de cada herramienta, que se muestran en la interfaz.

## Arquitectura

![Arquitectura](docs/arquitectura.png)

**Recorrido de una solicitud desde la interfaz web**

![Recorrido desde la GUI](docs/recorrido_gui.png)

**Recorrido de una solicitud desde un consumidor externo (Power BI)**

![Recorrido desde Power BI](docs/recorrido_powerbi.png)

**Modelo de datos**

![Modelo de datos](docs/modelo_datos.png)

## Tecnologías

| Capa | Tecnología |
|---|---|
| Frontend | React + Vite (JavaScript), React Router, Recharts, react-markdown |
| Backend y API | FastAPI (Python), Swagger automático en `/docs` |
| Base de datos | PostgreSQL en Neon, con la extensión **pgvector** |
| LLM | Groq (`openai/gpt-oss-120b`) |
| Embeddings | Google Gemini (`gemini-embedding-001`, 768 dimensiones) |
| Autenticación | JWT (usuarios) y API key de solo lectura (consumidores externos) |
| Pruebas | pytest, con el LLM y los embeddings simulados |
| CI/CD | GitHub Actions |
| Hosting | Render (API como *Web Service*, frontend como *Static Site*) y Neon (base de datos) |
| Reportes | Power BI Desktop consumiendo la API |

## Estructura del repositorio

```
turismo-gt/
├── .github/workflows/ci.yml        Pruebas, compilación y despliegue
├── backend/
│   ├── app/                        API: routers, agentes, RAG, herramientas, seguridad
│   ├── db/
│   │   ├── schema.sql              Creación de tablas (script de la base de datos)
│   │   └── seed.sql                Datos de demostración (destinos, actividades, servicios)
│   ├── scripts/
│   │   ├── init_db.py              Crea las tablas y carga los datos de ejemplo
│   │   ├── create_admin.py         Crea el usuario administrador
│   │   └── reindex.py              Genera los embeddings del RAG
│   ├── tests/                      Pruebas automatizadas
│   ├── .env.example
│   └── requirements.txt
├── frontend/                       Aplicación React
└── docs/                           Diagramas y colección de Postman
```

## Puesta en marcha local

**Requisitos:** Python 3.11 o superior, Node.js 20.19 o superior (se recomienda 22), una base de datos PostgreSQL con pgvector (por ejemplo, un proyecto gratuito de [Neon](https://neon.tech)), una llave de [Groq](https://console.groq.com) y una de [Google AI Studio](https://aistudio.google.com).

### 1. Backend

Desde la carpeta `backend/`:

```bash
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Mac/Linux:             source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # en Windows: copy .env.example .env
```

Completa `.env` (ver [Variables de entorno](#variables-de-entorno)) y prepara la base de datos:

```bash
python -m scripts.init_db       # crea las tablas y carga los datos de ejemplo
python -m scripts.create_admin admin@turismo.gt "Administrador"   # pide la contraseña por consola
python -m scripts.reindex       # genera los embeddings del RAG (requiere GEMINI_API_KEY)
uvicorn app.main:app --reload
```

> ⚠️ `init_db` **borra y recrea todas las tablas**. Úsalo solo en una base de datos nueva o de desarrollo. Después de ejecutarlo hay que volver a correr `create_admin` y `reindex`.

La API queda en `http://localhost:8000` (Swagger en `/docs`). Comprueba que `GET /health` responda `{"status":"ok","ai_services":3}`.

### 2. Frontend

Desde la carpeta `frontend/`:

```bash
cp .env.example .env            # en Windows: copy .env.example .env
npm install
npm run dev
```

Abre `http://localhost:5173` (con `localhost`, no con `127.0.0.1`, por la configuración de CORS).

### Datos de demostración

`seed.sql` carga 3 servicios de IA, 8 destinos y 17 actividades de Guatemala (Quetzaltenango, Lago de Atitlán, Antigua, Tikal, Semuc Champey, Chichicastenango, Pacaya y Río Dulce). Los costos y coordenadas son aproximados. `reindex` convierte esos textos en fragmentos con embeddings, y el administrador puede regenerarlos desde la sección *Base de conocimiento* de la aplicación.

## Variables de entorno

**Backend (`backend/.env`)**

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Cadena de conexión de PostgreSQL (en Neon termina en `?sslmode=require`) |
| `GROQ_API_KEY` | Llave de Groq |
| `GROQ_MODEL` | Modelo del LLM. Por defecto `openai/gpt-oss-120b` |
| `GEMINI_API_KEY` | Llave de Google Gemini (embeddings) |
| `JWT_SECRET` | Secreto para firmar los JWT. Genera uno con `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CORS_ORIGINS` | Orígenes permitidos separados por comas, sin espacios ni `/` final |
| `TEST_DATABASE_URL` | Solo para pruebas: base de datos **desechable** (se borra en cada ejecución) |

**Frontend (`frontend/.env`)**

| Variable | Descripción |
|---|---|
| `VITE_API_URL` | URL de la API, sin `/` final. Se incrusta al compilar |

Los archivos `.env` no se suben al repositorio.

## Usuarios y roles

| Rol | Puede |
|---|---|
| **Usuario** | Usar los servicios de IA activos, ver su historial de conversaciones y su consumo de tokens |
| **Administrador** | Todo lo anterior, más: CRUD de usuarios (con su límite de tokens), destinos y actividades, activar o desactivar servicios de IA, reindexar el RAG, ver el uso general y las conversaciones de todos, reportes y API keys |

- El registro público (`POST /auth/register`) siempre crea usuarios con rol `user`.
- El administrador se crea únicamente con `python -m scripts.create_admin`.
- **Credenciales de la demostración:** `admin@turismo.gt` / *(se entregan por separado)*.

## API REST

Documentación interactiva: **`/docs`** (Swagger). Todos los endpoints, salvo `/health`, `/auth/register` y `/auth/login`, exigen autenticación.

| Grupo | Endpoints principales | Acceso |
|---|---|---|
| Sistema | `GET /health` | Público |
| Autenticación | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` | Público / autenticado |
| Servicios de IA | `GET /services`, `POST /ai/chat`, `POST /ai/itinerary`, `POST /ai/adjust-plan` | Usuario |
| Historial | `GET /history/conversations`, `GET /history/conversations/{id}` | Usuario (solo lo suyo) |
| Consumo | `GET /usage/me`, `GET /usage/me/records` | Usuario |
| Catálogo | `GET /destinations`, `GET /activities` (lectura) · `POST`, `PUT`, `DELETE` | Lectura: usuario · Escritura: admin |
| Administración | `/admin/users` (CRUD, `reset-tokens`), `PATCH /admin/services/{id}`, `/admin/knowledge`, `/admin/api-keys` | Admin |
| Uso general | `GET /admin/usage`, `GET /admin/history/conversations` (filtros por usuario, servicio y fecha) | Admin |
| Reportes | `GET /reports/summary`, `GET /reports/usage` (filtros por usuario, servicio y fecha) | API key o admin |

**Autenticación.** El login recibe un formulario (`x-www-form-urlencoded`) con `username` (el correo) y `password`, y devuelve un JWT para la cabecera `Authorization: Bearer <token>`. Los consumidores externos de solo lectura (Power BI) usan la cabecera `X-API-Key`, solo válida en `/reports/*`. Las llaves se crean en la sección *API keys* de la aplicación, se muestran una sola vez y en la base de datos solo se guarda su hash SHA-256.

## Control de consumo de tokens

1. **Antes** de ejecutar un servicio, la API verifica que esté activo y que el usuario tenga tokens disponibles. Si no, responde `403` (servicio desactivado) o `429` (límite alcanzado) sin llamar a la IA.
2. **Después**, registra los tokens reales de entrada y salida que reporta el proveedor en `usage_log` y los suma al usuario, junto con los mensajes, en una sola transacción. Si la IA falla, no se guarda ni se cobra nada.
3. Los reportes (web y Power BI) suman `usage_log`. Por eso `tokens_used` (el contador que bloquea al usuario, que el administrador puede reiniciar) puede diferir del acumulado del historial.

Los embeddings de Gemini no cuentan como tokens del usuario. Un agente consume más que el chat, porque cada paso reenvía el historial al modelo, y una sola petición se corta al pasar de 15,000 tokens.

## Pruebas

Las pruebas automatizadas cubren el chatbot RAG (fuentes, información insuficiente, memoria), los agentes y sus herramientas, el registro y la consulta del historial, el cálculo y el bloqueo por tokens, los reportes y la API key, y la seguridad por roles. Usan **PostgreSQL real** y simulan el LLM y los embeddings, de modo que no consumen tokens ni dependen de internet.

```bash
cd backend
# En .env: TEST_DATABASE_URL=<una base de datos o rama DESECHABLE, distinta de DATABASE_URL>
python -m pytest -v
```

> ⚠️ Las pruebas **borran y recrean todas las tablas** de `TEST_DATABASE_URL`, y se niegan a ejecutarse si es igual a `DATABASE_URL`. Usa una rama de Neon o un contenedor, nunca la base real.

Alternativa local con Docker:

```bash
docker run --name turismo-pg-test -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=turismo_test -p 5433:5432 -d pgvector/pgvector:pg16
# TEST_DATABASE_URL=postgresql://test:test@localhost:5433/turismo_test
```

## CI/CD y despliegue

El flujo `.github/workflows/ci.yml` se ejecuta en cada `push` y *pull request* a `main`:

| Job | Qué hace |
|---|---|
| `test` | Levanta PostgreSQL con pgvector y ejecuta `pytest` |
| `frontend` | Instala dependencias y compila el frontend (`npm run build`) |
| `deploy` | **Solo si `test` y `frontend` pasan** y solo en `push` a `main`: llama a los *deploy hooks* de Render |

Si una prueba falla, el job `deploy` se omite y no se publica nada. Para que esto funcione, el **Auto-Deploy de Render está en *Off*** en ambos servicios y el despliegue solo ocurre desde GitHub Actions.

**Secretos de GitHub** (*Settings → Secrets and variables → Actions*): `RENDER_API_DEPLOY_HOOK` y `RENDER_WEB_DEPLOY_HOOK`.

**Render: API (*Web Service*)**

| Campo | Valor |
|---|---|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Variables | `DATABASE_URL`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `GROQ_MODEL`, `JWT_SECRET`, `CORS_ORIGINS` |

**Render: frontend (*Static Site*)**

| Campo | Valor |
|---|---|
| Root Directory | `frontend` |
| Build Command | `npm install && npm run build` |
| Publish Directory | `dist` |
| Variables | `VITE_API_URL`, `NODE_VERSION` (22 o superior) |
| Rewrite | `/*` → `/index.html` (para que recargar una ruta no dé 404) |

## Consumo externo: Postman y Power BI

**Postman.** Importa `docs/TurismoGT.postman_collection.json`, completa las variables de la colección (`user_email`, `user_password`, `admin_email`, `admin_password`, `api_key`) y ejecuta las carpetas en orden con *Run collection*. Cada petición incluye pruebas, y hay una carpeta de controles de acceso que deben fallar con `401` o `403`.

**Power BI.** El reporte consume `GET /reports/usage` con la cabecera `X-API-Key` y replica el reporte web: consultas y tokens por servicio, con segmentadores de fecha, servicio y usuario. Ambos usan el mismo endpoint, así que los resultados coinciden.

| | |
|---|---|
| Archivo | `Turismo_GT_Reporte.pbix` (entregado aparte: contiene una API key de solo lectura) |
| Origen | `https://turismo-gt.onrender.com/reports/usage` |
| Autenticación | Anónima, con la API key enviada en la cabecera `X-API-Key` |

## Solución de problemas

| Síntoma | Causa y solución |
|---|---|
| El frontend dice «No se pudo conectar con el servidor» | `VITE_API_URL` incorrecta, o la API está dormida. Cambiarla exige volver a compilar el frontend |
| Error de CORS en la consola del navegador | `CORS_ORIGINS` no coincide exactamente con la URL del frontend (revisa `https`, el `/` final y los espacios) |
| `502` al usar un servicio de IA | Falla de Groq o Gemini: llave faltante, modelo retirado o límite de uso. Revisa `GROQ_MODEL` y espera un minuto |
| El chatbot responde «no tengo información suficiente» sobre algo que sí existe | Faltan los embeddings: ejecuta `python -m scripts.reindex` o *Reindexar todo* en la aplicación |
| `extension "vector" is not available` | Ejecuta `CREATE EXTENSION vector;` en la base de datos |
| `429` | El usuario alcanzó su límite de tokens: el administrador puede ampliarlo o reiniciar el consumo |
| `pytest` falla al iniciar con un error de `TEST_DATABASE_URL` | Falta la variable, o es igual a `DATABASE_URL` |

## Autor

- Bryan Alexander Pérez Santos · Universidad Mesoamericana, Campus Quetzaltenango · Programación Comercial