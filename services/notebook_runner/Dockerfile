FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m ipykernel install --user --name python3 --display-name "Python 3"

RUN mkdir -p /app/data/raw /app/data/results /app/notebooks

COPY app.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]