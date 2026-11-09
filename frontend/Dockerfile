# 1) Build the React app into static files.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# 2) Serve them with nginx, which also forwards /api, /ws, /admin and /static
#    to Django, so the browser sees ONE origin (cookies + CSRF just work).
FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
