# IIM frontend image. Multi-stage: build the Vite bundle with Node, then serve
# the static assets with nginx. nginx also reverse-proxies /api + /healthz to
# the backend service, mirroring the dev-server proxy in vite.config.ts — the
# built app still talks to a relative `/api` base, so no CORS config needed.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
