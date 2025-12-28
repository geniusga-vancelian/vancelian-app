FROM python:3.12-slim

WORKDIR /app

COPY agent_gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY agent_gateway /app/agent_gateway

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "agent_gateway.app:app", "--host", "0.0.0.0", "--port", "8000"]
