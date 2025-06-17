FROM python:3.10-buster

WORKDIR /app

RUN useradd -m appuser && chown -R appuser /app
USER appuser

COPY --chown=appuser:appuser . .

ARG EXTRAS=""
RUN pip install --no-cache-dir ".[${EXTRAS}]"

ENTRYPOINT ["python", "-m", "sameli"]
CMD ["--conf", "/app/conf/dummy_model.yaml"]