FROM python:3.9.6-alpine

# Set working directory
WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip

COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

COPY . /app/