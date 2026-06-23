# WorkaTrack Demo Portable

## Requisitos
- Docker
- Docker Compose

## Arranque
Desde la raíz del proyecto:

```bash
./scripts/start_portable_demo.sh
```

## Acceso
- URL: http://localhost:3000
- Usuario: demo
- Password: demo1234

## Contraseña del proyecto demo principal
- proyecto1234

## Qué incluye esta demo
- gestión de proyectos, tareas y sesiones
- métricas y tiempos
- vista Gantt
- árbol de tareas
- charts
- Q&A FAST
- Q&A DEEP
- datos demo reproducibles

## Notas
- El primer arranque puede tardar más porque descarga y prepara modelos de Ollama.
- Los siguientes arranques serán más rápidos si se conservan los volúmenes Docker.

## Parada
Para detener la demo:

```bash
docker compose -f docker-compose.portable.yml down
```

## Reinicio limpio de datos demo
Si se quiere volver a sembrar la demo, basta con volver a ejecutar:

```bash
./scripts/start_portable_demo.sh
```
