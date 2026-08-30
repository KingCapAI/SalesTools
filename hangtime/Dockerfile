# Build the frontend
FROM node:22-alpine AS webbuild
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Run the API + serve the built frontend from one service
FROM python:3.11-slim
WORKDIR /srv
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=webbuild /web/dist ./static
ENV HANGTIME_STATIC_DIR=/srv/static
EXPOSE 8000
CMD ["/bin/sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
