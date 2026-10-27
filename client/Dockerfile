# Stage 1: build the static bundle
FROM node:22-alpine AS build

WORKDIR /app

# Copy package files first so `npm ci` is cached unless deps change
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite inlines import.meta.env.VITE_* at build time, so the API URL has to be
# supplied here as a build arg -- setting it at container start has no effect.
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Stage 2: serve the bundle
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Matches `listen` in nginx.conf; the gateway reaches it on localhost:3000
EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
