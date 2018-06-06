FROM golang:alpine as builder
WORKDIR /go/src/tinyserver
COPY main.go /go/src/tinyserver
ENV CGO_ENABLED=0
ENV GOOS=linux
RUN go build -ldflags '-w'
CMD ["/bin/sh"]

FROM scratch
COPY --from=builder /go/src/tinyserver/tinyserver /
# Map in www directory with a ConfigMap
LABEL      description="Tiny static web server" \
             name="lsstsqre/tiny-static-server" \
             version="0.0.1"
CMD ["/tinyserver"]
