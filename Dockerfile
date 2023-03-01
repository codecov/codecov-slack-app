FROM python:3.11.2-alpine

# Set working directory
WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip

COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

COPY . /app/