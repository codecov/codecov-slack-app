# syntax=docker/dockerfile:1.3
ARG REQUIREMENTS_IMAGE
ARG BERGLAS_VERSION=2.0.6
FROM            us-docker.pkg.dev/berglas/berglas/berglas:$BERGLAS_VERSION as berglas

FROM $REQUIREMENTS_IMAGE

# Set working directory
WORKDIR /app
COPY            --chmod=755 --from=berglas /bin/berglas /usr/local/bin/berglas


COPY . /app/
