FROM node:22-alpine AS frontend-build
WORKDIR /workspace/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HIDANI_DATA_DIR=/var/lib/ai-job-assistant
WORKDIR /app/backend
COPY backend/ ./
COPY --from=frontend-build /workspace/frontend/dist /app/frontend/dist
RUN python -m pip install --no-cache-dir -r requirements.txt
EXPOSE 8001
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
