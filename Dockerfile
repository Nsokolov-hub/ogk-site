# Витрина ogk-chem.ru (Next.js) в самостоятельной сборке: docker compose up -d --build web.
# API_ORIGIN — адрес API сайта, куда витрина проксирует /api/v1/*; он попадает в сборку.
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:24-alpine AS build
WORKDIR /app
ARG API_ORIGIN=http://api:8000
ARG NEXT_PUBLIC_SMARTCAPTCHA_SITE_KEY=
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_OUTPUT=standalone API_ORIGIN=$API_ORIGIN \
    NEXT_PUBLIC_SMARTCAPTCHA_SITE_KEY=$NEXT_PUBLIC_SMARTCAPTCHA_SITE_KEY
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -g 10001 web && adduser -u 10001 -G web -D web
COPY --from=build --chown=web:web /app/.next/standalone ./
COPY --from=build --chown=web:web /app/.next/static ./.next/static
COPY --from=build --chown=web:web /app/public ./public
USER web
EXPOSE 3000
CMD ["node", "server.js"]
