FROM golang:alpine as builder
WORKDIR /go/src/tinyserver
COPY main.go /go/src/tinyserver
ENV CGO_ENABLED=0
ENV GOOS=linux
RUN go build
CMD ["/bin/sh"]

FROM scratch
COPY --from=builder /go/src/tinyserver/tinyserver /
# Do this with a ConfigMap
# COPY www /www 
CMD ["/tinyserver"]
