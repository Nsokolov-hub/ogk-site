# Caddy of staging and production with the admin panel's static files (admin/, TZ 13): one container serves
# the site, the API and the admin panel on its own name (deploy/caddy/admin.caddy).
FROM node:24-alpine AS admin
WORKDIR /admin
COPY admin/package.json admin/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY admin/ ./
RUN npm run build

FROM caddy:2.11.6-alpine
COPY --from=admin /admin/dist /srv/admin
