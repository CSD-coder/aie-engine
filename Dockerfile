FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY aie_engine ./aie_engine
RUN useradd --create-home --uid 10001 aie && chown -R aie:aie /app
USER aie
CMD ["uvicorn","aie_engine.main:app","--host","0.0.0.0","--port","8000"]
