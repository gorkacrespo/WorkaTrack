# -------------------------------
# Stage 1: Build del frontend
# -------------------------------
FROM node:20-alpine AS build

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Directorio de trabajo
WORKDIR /app

# Copiamos package.json y lock primero (mejor cache)
COPY package.json package-lock.json ./

# Instalamos dependencias
RUN npm ci

# Copiamos el resto del código
COPY . .

# Construimos la app (Vite -> dist/)
RUN npm run build


# -------------------------------
# Stage 2: Servir archivos estáticos
# -------------------------------
FROM nginx:alpine

# Borramos la config por defecto
RUN rm /etc/nginx/conf.d/default.conf

# Copiamos nuestra build al directorio público de nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Configuración básica de nginx para SPA
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Puerto estándar
EXPOSE 80

# Arranque de nginx
CMD ["nginx", "-g", "daemon off;"]
