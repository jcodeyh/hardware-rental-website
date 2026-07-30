# Pull official node image (matches .github/workflows/ci.yml's node-version: 22)
FROM node:22

WORKDIR /app

# Copy package files first so `npm ci` is cached unless deps change
COPY package.json package-lock.json ./
RUN npm ci

# Add Vite app to working directory
COPY . .

# vite.config.js pins the dev server to port 8080
EXPOSE 8080

# --host so the dev server is reachable from outside the container, not just localhost inside it
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
