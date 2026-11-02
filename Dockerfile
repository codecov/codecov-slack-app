# syntax=docker/dockerfile:1.3
ARG REQUIREMENTS_IMAGE
ARG BERGLAS_VERSION=v2.0.18
ARG GO_IMAGE=golang:1.27.3-bookworm

# Build berglas from source: the prebuilt image lags on the Go stdlib, which
# carries critical/high CVEs in AR scans.
FROM ${GO_IMAGE} as berglas
ARG BERGLAS_VERSION
RUN git clone --depth 1 --branch ${BERGLAS_VERSION} \
    https://github.com/GoogleCloudPlatform/berglas.git /src
WORKDIR /src
RUN CGO_ENABLED=0 go build -trimpath -o /bin/berglas .

FROM $REQUIREMENTS_IMAGE

WORKDIR /app
COPY --chmod=755 --from=berglas /bin/berglas /usr/local/bin/berglas

COPY . /app/
