# syntax=docker/dockerfile:1.3
ARG REQUIREMENTS_IMAGE
FROM            busybox:1.36 as berglas
WORKDIR /tmp
ADD             https://storage.googleapis.com/berglas/0.7.0/linux_amd64/berglas berglas
RUN             echo "25d3515e7cbf269caa0cff462de73c5ba0e4cea143fa90df753a76b09f72519f  berglas" | sha256sum -c

FROM $REQUIREMENTS_IMAGE

# Set working directory
WORKDIR /app
COPY            --chmod=755 --from=berglas /tmp/berglas /usr/local/bin/berglas


COPY . /app/
RUN             python manage.py collectstatic --no-input
