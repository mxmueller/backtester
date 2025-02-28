FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN echo "streamlit>=1.22.0\npandas>=1.5.3\nnumpy>=1.24.3\nplotly>=5.14.1\nrequests>=2.28.2\nminio>=7.1.15\npyyaml>=6.0\nscikit-learn>=1.2.2\nmatplotlib>=3.7.1" > /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8501

ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "analytics.py", "--server.address=0.0.0.0"]