# WorkaTrack

WorkaTrack es una aplicación web de gestión de proyectos y tareas con asistencia de IA local. Permite registrar proyectos, tareas, sesiones de trabajo y tiempos, visualizar métricas y diagramas (Gantt, árbol de tareas, gráficas), y consultar el estado del proyecto mediante preguntas en lenguaje natural (Q&A) resueltas por un modelo LLM que se ejecuta localmente con [Ollama](https://ollama.com), sin enviar datos a servicios externos.

El proyecto se desarrolla como caso práctico de un Trabajo de Fin de Grado sobre contenedores y orquestadores: backend en Flask, frontend en React, base de datos PostgreSQL e inferencia LLM con Ollama, todo orquestado con Docker Compose (y con manifiestos de Kubernetes para despliegue en clúster).

## Arquitectura

| Componente | Tecnología |
|---|---|
| Backend | Python 3.12 / Flask 3 / SQLAlchemy / Alembic |
| Frontend | React 19 / Vite / React Router |
| Base de datos | PostgreSQL 16 |
| IA local | Ollama (modelo `workatrack-qa-fast` para Q&A y `nomic-embed-text` para embeddings) |
| Orquestación demo | Docker Compose |
| Orquestación producción | Kubernetes (manifiestos en `k8s/`) |

## Requisitos previos

Solo se necesita tener instalado:

- **Docker** ≥ 24.0
- **Docker Compose** ≥ 2.20 (incluido en Docker Desktop o como plugin `docker compose`)

No es necesario instalar Python, Node.js, PostgreSQL ni Ollama por separado: todo se levanta en contenedores.

> Recursos recomendados: al menos 8 GB de RAM libres y unos 10 GB de espacio en disco, ya que el primer arranque descarga los modelos de Ollama.

## Instalación y arranque

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/gorkacrespo/WorkaTrack.git
   cd WorkaTrack
   ```

2. Arrancar la demo con el script incluido:

   ```bash
   ./scripts/start_portable_demo.sh
   ```

   Este script:
   - construye y levanta los contenedores `db` (PostgreSQL), `ollama` (LLM local), `web` (API Flask) y `frontend` (React servido con Nginx);
   - espera a que la base de datos y Ollama estén saludables (`healthcheck`);
   - siembra automáticamente datos de demostración reproducibles (proyectos, tareas, sesiones).

3. Acceder a la aplicación:

   - URL: [http://localhost:3000](http://localhost:3000)

### Credenciales de demo

| Campo | Valor |
|---|---|
| Usuario | `demo` |
| Contraseña | `demo1234` |
| Contraseña del proyecto demo principal | `proyecto1234` |

## Primer arranque de Ollama

En el primer arranque, el contenedor `ollama` descarga y prepara los modelos necesarios (`workatrack-qa-fast` y `nomic-embed-text`), por lo que el proceso puede tardar varios minutos adicionales según la conexión a internet. El healthcheck del servicio no se marca como saludable hasta que ambos modelos están disponibles, y el resto de servicios esperan a que esto ocurra antes de quedar operativos.

En arranques posteriores, si se conservan los volúmenes Docker (`ollama_data`, `db_data`), el proceso es mucho más rápido porque los modelos y los datos ya están persistidos.

## Detener la demo

Desde la carpeta `WorkaTrack/` (la raíz del repositorio clonado):

```bash
cd WorkaTrack
docker compose -f docker-compose.portable.yml down
```

## Reiniciar con datos limpios

Para volver a sembrar la demo desde cero, basta con volver a ejecutar:

```bash
./scripts/start_portable_demo.sh
```

## Funcionalidades incluidas

- Gestión de proyectos, tareas y sesiones de trabajo
- Métricas y registro de tiempos por tarea/proyecto
- Vista Gantt y árbol jerárquico de tareas
- Gráficas de evolución y desviación
- Q&A **FAST** y **DEEP**: preguntas en lenguaje natural sobre el estado del proyecto, resueltas por un LLM local vía Ollama
- Datos de demostración reproducibles
