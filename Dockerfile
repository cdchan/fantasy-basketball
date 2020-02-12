FROM python:3.8.1

COPY . /app

RUN pip install -r /app/requirements.txt

WORKDIR /app
