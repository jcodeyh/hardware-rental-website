# Pull latest official node image
FROM node:latest

# Expose ports
EXPOSE 3000
EXPOSE 35729

# Set working directory
WORKDIR /app

# add `/app/node_modules/.bin` to environment variables
ENV PATH /app/node_modules/.bin:$PATH

# react-scripts 3's webpack 4 calls Node's crypto module in a way modern
# OpenSSL (Node 17+) rejects; this restores the legacy provider
ENV NODE_OPTIONS=--openssl-legacy-provider

# Copy package files and install app dependencies
COPY package.json /app/package.json
COPY package-lock.json /app/package-lock.json
RUN npm install
RUN npm install react-scripts -g

# Add React app to working directory
ADD . /app

# Start the React app
CMD ["npm", "start"]