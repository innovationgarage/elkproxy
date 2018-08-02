FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get install -y sudo python3 python3-pip python3-dev build-essential mg

ADD app /app
WORKDIR /app

RUN python3 setup.py develop

CMD ["/bin/bash", "-c", "LC_ALL=C.UTF-8 LANG=C.UTF-8 elkproxy -c config.json"]
