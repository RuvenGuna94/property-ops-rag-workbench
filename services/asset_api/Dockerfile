FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY asset_api.py prepare_runtime.py ./
RUN chmod 755 /app && chmod 644 /app/*.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["python", "-m", "uvicorn", "asset_api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
