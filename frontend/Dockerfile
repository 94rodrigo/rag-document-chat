# syntax=docker/dockerfile:1

# ── build ───────────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Dependency layer cached separately from source so editing app code doesn't
# bust the npm install cache.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── runtime ─────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# 127.0.0.1, not localhost: Alpine's wget resolves "localhost" to ::1 first,
# and nginx here isn't listening on IPv6, which makes the healthcheck fail
# even though the app serves fine over IPv4.
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:80/ || exit 1

# nginx's own entrypoint already drops worker processes to the unprivileged
# `nginx` user; the master process needs root only to bind port 80.
CMD ["nginx", "-g", "daemon off;"]
