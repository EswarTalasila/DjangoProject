# =============================================================================
# Frontend Production Dockerfile (Multi-stage Build)
# =============================================================================
# This Dockerfile creates an optimized production image using a multi-stage
# build. The final image contains only the compiled static files served by Nginx.
#
# Usage:
#   docker build -t eel-frontend:prod -f Dockerfile .
#
# Stage 1 (builder): Compiles the Angular application
# Stage 2 (runtime): Serves static files with Nginx
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build the Angular application
# -----------------------------------------------------------------------------
FROM node:22-alpine AS builder

WORKDIR /app

# Copy package files first to leverage Docker layer caching.
# Dependencies are only reinstalled when package*.json changes.
COPY package*.json ./

# Install dependencies using ci for reproducible builds
RUN npm ci

# Copy source code and build configuration
COPY . .

# Build the Angular application in production mode
# Output goes to /app/dist/frontend/browser
RUN npm run build -- --configuration production

# -----------------------------------------------------------------------------
# Stage 2: Serve with Nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine

# Copy compiled static files from builder stage
COPY --from=builder /app/dist/frontend/browser /usr/share/nginx/html

# Copy custom Nginx configuration for SPA routing and API proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
