# syntax=docker/dockerfile:1.3
ARG REQUIREMENTS_IMAGE
ARG BERGLAS_VERSION=v2.0.15
ARG GO_IMAGE=golang:1.26-bookworm

# Build berglas from source: the prebuilt image lags on Go stdlib and
# module pins (x/crypto, grpc), which carry critical/high CVEs in AR scans.
FROM ${GO_IMAGE} as berglas
ARG BERGLAS_VERSION
RUN git clone --depth 1 --branch ${BERGLAS_VERSION} \
    https://github.com/GoogleCloudPlatform/berglas.git /src
WORKDIR /src
RUN go get google.golang.org/grpc@v1.82.1 \
        golang.org/x/crypto@v0.54.0 \
        golang.org/x/net@v0.57.0 && go mod tidy
RUN CGO_ENABLED=0 go build -trimpath -o /bin/berglas .

FROM $REQUIREMENTS_IMAGE

WORKDIR /app
COPY --chmod=755 --from=berglas /bin/berglas /usr/local/bin/berglas

COPY . /app/
