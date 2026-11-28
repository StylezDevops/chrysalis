FROM python:latest
RUN apt-get update && apt-get install -y curl
ADD . /app
CMD python -m http.server 8080
