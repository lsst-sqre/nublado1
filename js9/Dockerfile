FROM golang:alpine as gobuilder
ENV  CGO_ENABLED=0
ENV  GOOS=linux
RUN  mkdir -p /src/tinyserver
COPY main.go /src/tinyserver/main.go
RUN  cd /src/tinyserver && \
      go build -ldflags '-w'
FROM alpine:latest as builder
RUN  apk update && apk add make gcc musl-dev git bash
# Later add libfuntools, cfitsio, and node
ENV  cv="cfitsio-3.47"
RUN  mkdir -p /usr/local/src && \
      cd /usr/local/src && \
      wget http://heasarc.gsfc.nasa.gov/FTP/software/fitsio/c/${cv}.tar.gz && \
      tar xfz ${cv}.tar.gz && \
      cd ${cv} && \
      ./configure --prefix=/usr/local && \
      make && \
      make install
RUN  apk add git make bash
RUN  mkdir -p /usr/local/src && \
      cd /usr/local/src && \
      git clone https://github.com/ericmandel/js9 && \
      cd js9 && \
      ./configure --with-webdir=/www/js9 --with-helper=nodejs \
                  --with-cfitsio=/usr/local --prefix=/usr/local && \
      make && \
      make install
FROM alpine:latest
RUN  mkdir -p /usr/local/bin /usr/local/include /usr/local/lib && \
      apk update && \
      apk add nodejs bash
COPY --from=builder /usr/local/include/ /usr/local/include
COPY --from=builder /usr/local/lib/ /usr/local/lib
COPY --from=builder /usr/local/bin/ /usr/local/bin
COPY --from=builder /www/js9/ /www/js9/js9
COPY --from=builder /www/js9/index.html /www/js9/index.html
COPY --from=gobuilder /src/tinyserver/tinyserver /usr/local/bin/tinyserver
COPY casa.fits.gz /www/js9/js9/fits/casa.fits.gz
COPY passwd /etc/passwd
COPY group /etc/group
COPY runjs9 /usr/local/bin
RUN  mkdir -p /var/log/js9 && \
     chown nobody /var/log/js9
USER 65534
LABEL      description="JS9 Web Server" \
             name="lsstsqre/js9server" \
             version="0.0.2"
CMD ["/usr/local/bin/runjs9"]
