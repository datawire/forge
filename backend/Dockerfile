# Run server
FROM alpine:latest
RUN apk update
RUN apk add docker python py2-pip py2-gevent
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 5000
ENTRYPOINT ["python"]
CMD ["app.py"]
