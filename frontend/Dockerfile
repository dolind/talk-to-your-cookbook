FROM node:20

# Set working directory
WORKDIR /app

# Install deps
COPY package*.json ./
RUN npm install

# Copy source code
COPY src/ .

# Expose Vite dev port
EXPOSE 5173

# Start Vite in dev mode
CMD ["npm", "run", "dev"]
