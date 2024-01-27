FROM python:3.11-slim

WORKDIR /web
COPY ./requirements.txt /web
RUN apt update && apt install -y git
RUN pip install --no-cache-dir -r /web/requirements.txt
COPY . /web
RUN pip install -e .
CMD gunicorn -w 4 src.web.server:web -b 0.0.0.0:8001
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ="America/Los_Angeles"
