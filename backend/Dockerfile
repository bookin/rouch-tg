#FROM python:3.11-slim
#
#WORKDIR /app
#
## Install dependencies
#COPY requirements.txt .
#RUN pip install --no-cache-dir -r requirements.txt
#
## Copy application code
#COPY . .
#
## Run application
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM python:3.13-slim

RUN pip install uv
RUN uv pip install --system --index-url https://download.pytorch.org/whl/cpu torch

# COPY . .

#COPY pyproject.toml .
#COPY uv.lock .
#RUN uv sync --frozen --no-dev

WORKDIR /app