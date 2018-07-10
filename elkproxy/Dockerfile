FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get install -y sudo python3 python3-pip python3-dev build-essential mg

ADD app /app
WORKDIR /app

RUN pip3 install -r requirements.txt

CMD ["/bin/bash", "-c", "while sleep 1; do : ; done"]
