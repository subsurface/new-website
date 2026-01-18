FROM python:3.11-slim

RUN apt-get update && \
    apt-get full-upgrade -y && \
    apt-get -y -q install git make asciidoctor docbook-xml ruby-asciidoctor-pdf w3m && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /web
RUN pip install pip-tools
COPY ./requirements.in /web
RUN pip-compile
RUN pip install --no-cache-dir -r /web/requirements.txt
COPY . /web
RUN pip install -e .

CMD gunicorn -w 4 src.web.server:web -b 0.0.0.0:8001
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ="America/Los_Angeles"
