# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend & Static Serving
FROM python:3.11-slim AS runner

WORKDIR /app

# Install system dependencies (build-essential, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code and config
COPY backend/ ./backend/
COPY pytest.ini ./

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose port (default 8000)
ENV PORT=8000
EXPOSE 8000

# Seed database on container start and run uvicorn
CMD ["sh", "-c", "python backend/app/seed.py && python backend/run.py"]
