# Node.js Application Dockerfile
FROM node:20-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production || npm install

# Copy application code
COPY . .

# Expose the application port
EXPOSE 3000

# Default command
CMD ["node", "index.js"]
