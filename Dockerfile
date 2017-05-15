# Run server
FROM alpine:latest
RUN apk add --no-cache curl docker python py2-pip py2-gevent
RUN curl -o /usr/bin/kubectl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod a+x /usr/bin/kubectl
WORKDIR /app
COPY requirements.txt /app
COPY setup.py /app
RUN pip install -r requirements.txt
COPY skunkworks /app/skunkworks
RUN pip install .
EXPOSE 5000
ENTRYPOINT ["sw"]
CMD ["serve"]
