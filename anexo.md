# Anexo técnico — WorkaTrack

## Parte 1 — Descripción de la aplicación

WorkaTrack es una aplicación web de gestión de proyectos y tareas pensada para equipos pequeños/medianos, que añade una capa de asistencia mediante IA local. El backend, escrito en Python con Flask y SQLAlchemy, expone una API REST para gestionar proyectos, tareas, sesiones de trabajo, hitos y estadísticas de tiempo. El frontend, en React (Vite), consume esa API y ofrece vistas de tablero, Gantt, árbol de tareas y gráficas de evolución/desviación.

La característica diferencial del proyecto es el módulo de **Q&A** (preguntas y respuestas en lenguaje natural sobre el estado del proyecto), resuelto en dos modos:

- **FAST**: respuesta rápida basada en resúmenes semanales pre-calculados.
- **DEEP**: análisis más profundo sobre el histórico completo de evidencias (tareas, sesiones, comentarios).

Ambos modos usan un LLM ejecutado **localmente** mediante [Ollama](https://ollama.com) (modelo `workatrack-qa-fast`, derivado de `qwen2.5`, y `nomic-embed-text` para embeddings de similitud semántica), evitando enviar datos del proyecto a servicios de IA externos. Esta decisión de arquitectura es el motivo por el que el TFG se centra en contenedores y orquestadores: ejecutar un LLM junto a una API web y una base de datos relacional, de forma reproducible, exige resolver problemas reales de orquestación (dependencias de arranque, healthchecks, persistencia de modelos pesados, recursos de cómputo) que son el objeto de estudio del trabajo.

El sistema se distribuye en dos formas:

1. **Demo portable** con Docker Compose (`docker-compose.portable.yml`), pensada para evaluación rápida en una sola máquina.
2. **Manifiestos de Kubernetes** (`k8s/`), que representan cómo se desplegaría el mismo sistema en un clúster, con separación de Deployments, Services, ConfigMaps y Secrets.

Repositorio: [https://github.com/gorkacrespo/WorkaTrack](https://github.com/gorkacrespo/WorkaTrack)

---

## Parte 2 — Fragmentos representativos

### Dockerfile (backend)

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
 && rm -rf /var/lib/apt/lists/*
```

Imagen base ligera (`slim`) para reducir tamaño de la imagen final. Las variables `PYTHONDONTWRITEBYTECODE`/`PYTHONUNBUFFERED` evitan ficheros `.pyc` innecesarios y hacen que los logs salgan sin buffer, algo relevante cuando los logs del contenedor se recogen por el motor de contenedores (`docker logs`/`kubectl logs`). `libpq-dev` y `build-essential` son dependencias de compilación de `psycopg2`, el driver de PostgreSQL: sin ellas, la build fallaría en el paso de `pip install`.

```dockerfile
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app
COPY config.py /app/config.py
COPY migrations /app/migrations
```

`requirements.txt` se copia e instala **antes** del código de la aplicación. Esto aprovecha la caché de capas de Docker: si solo cambia el código fuente, la capa de dependencias no se reconstruye, acelerando los rebuilds durante el desarrollo y en el pipeline de CI.

### docker-compose.portable.yml

```yaml
ollama:
  image: ollama/ollama:0.17.7
  entrypoint: ["/bin/sh", "/app/docker/ollama.entrypoint.compose.sh"]
  volumes:
    - ollama_data:/root/.ollama
    - ./docker/ollama.entrypoint.compose.sh:/app/docker/ollama.entrypoint.compose.sh:ro
  healthcheck:
    test: ["CMD-SHELL", "ollama list | grep -q workatrack-qa-fast && ollama list | grep -q nomic-embed-text"]
    interval: 10s
    timeout: 10s
    retries: 30
```

El servicio de IA local es el más delicado de orquestar: en el primer arranque tiene que descargar y preparar los modelos, lo que puede tardar minutos. El `healthcheck` personalizado comprueba que **ambos** modelos (Q&A y embeddings) están realmente listos, no solo que el proceso de Ollama responde. Esto es clave para el TFG: ilustra cómo un orquestador debe esperar a que una dependencia "pesada" esté lista antes de considerar el servicio disponible.

```yaml
web:
  build:
    context: .
    dockerfile: Dockerfile.compose
  environment:
    DATABASE_URL: postgresql+psycopg2://workatrack:workatrack@db:5432/workatrack
    OLLAMA_BASE_URL: http://ollama:11434
  depends_on:
    db:
      condition: service_healthy
    ollama:
      condition: service_healthy
```

`depends_on` con `condition: service_healthy` encadena el arranque de la API a que tanto la base de datos como Ollama estén realmente operativos (no solo que el contenedor exista), evitando errores de conexión durante el arranque en frío del stack completo.

```yaml
volumes:
  db_data:
  ollama_data:
```

Los datos de PostgreSQL y los modelos de Ollama se persisten en volúmenes con nombre, gestionados por Docker. Esto permite que, tras el primer arranque (lento, por la descarga de modelos), los arranques siguientes sean rápidos, ya que los datos sobreviven a la destrucción y recreación de los contenedores.

### k8s/workatrack-api.yaml (Deployment)

```yaml
initContainers:
  - name: db-migrate
    image: workatrack:latest
    command:
      - sh
      - -lc
      - |
        python - <<'PY'
        import socket, time
        host = "postgres"
        ...
        PY
        flask db upgrade
```

El `initContainer` espera activamente a que PostgreSQL acepte conexiones TCP y, solo entonces, ejecuta `flask db upgrade` (migraciones de Alembic) antes de que arranque el contenedor principal. En Kubernetes no existe un equivalente directo a `depends_on: condition: healthy` de Compose entre Pods distintos, por lo que esta espera activa dentro de un initContainer es el patrón estándar para garantizar el orden de arranque.

```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: workatrack-secret
        key: DATABASE_URL
  - name: FLASK_ENV
    valueFrom:
      configMapKeyRef:
        name: workatrack-config
        key: FLASK_ENV
```

Separación explícita entre configuración no sensible (`ConfigMap`, p. ej. `FLASK_ENV`) y datos sensibles (`Secret`, p. ej. cadena de conexión a la base de datos con credenciales). Es el patrón recomendado en Kubernetes para no versionar secretos junto a los manifiestos y poder rotarlos sin tocar el Deployment.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: workatrack-service
spec:
  type: ClusterIP
  selector:
    app: workatrack
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
```

El `Service` de tipo `ClusterIP` expone la API solo dentro del clúster, en el puerto 80, redirigiendo al puerto real de Flask (5000). La exposición al exterior se delega al `Ingress` (`k8s/ingress.yaml`), separando responsabilidades de enrutado interno y entrada externa.

### .gitlab-ci.yml

```yaml
stages:
  - test
  - build
  - deploy

test_backend:
  stage: test
  script:
    - python -m compileall app
    - python -c "from app import create_app; app = create_app(); print('create_app OK')"
```

Pipeline de tres fases. El stage `test` es deliberadamente ligero: compila el código y comprueba que la factory `create_app()` no lanza excepciones al instanciarse, como verificación mínima de que la app arranca antes de construir la imagen.

```yaml
build_image:
  stage: build
  image:
    name: gcr.io/kaniko-project/executor:debug
    entrypoint: [""]
  script:
    - mkdir -p /kaniko/.docker
    - |
      cat <<EOF > /kaniko/.docker/config.json
      { "auths": { "${CI_REGISTRY}": { "username": "${CI_REGISTRY_USER}", "password": "${CI_REGISTRY_PASSWORD}" } } }
      EOF
    - /kaniko/executor --context "${CI_PROJECT_DIR}" --dockerfile "${CI_PROJECT_DIR}/Dockerfile" --destination "${CI_REGISTRY_IMAGE}:${CI_COMMIT_REF_SLUG}" --destination "${CI_REGISTRY_IMAGE}:latest"
```

Se usa **Kaniko** en lugar de `docker build` porque el runner de GitLab CI ejecuta los jobs dentro de contenedores sin acceso al socket de Docker del host (sin Docker-in-Docker privilegiado). Kaniko construye y sube la imagen al registry sin necesitar un daemon Docker, lo que es más seguro en entornos de CI compartidos.

```yaml
deploy_to_k8s:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - echo "$KUBECONFIG_WORKATRACK" > kubeconfig
    - kubectl --kubeconfig=kubeconfig apply -f k8s/
    - kubectl --kubeconfig=kubeconfig rollout status deployment/workatrack-api
  when: manual
  allow_failure: true
  only:
    - master
```

El despliegue a Kubernetes es **manual** (`when: manual`) y solo disponible en `master`, como medida de control típica en un entorno de prácticas: el pipeline construye y valida automáticamente, pero el despliegue real a clúster requiere una acción explícita. El `kubeconfig` se inyecta como variable de CI protegida (`KUBECONFIG_WORKATRACK`), evitando que credenciales de acceso al clúster queden versionadas en el repositorio.
