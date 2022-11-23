FROM ubuntu:20.04

WORKDIR /app

RUN apt-get update

RUN apt-get install -y python3

RUN apt-get -y install python3-pip

COPY . .

RUN apt-get install -y libmysqlclient-dev

RUN pip install -r requirements.txt 

EXPOSE 8100:8100

CMD [ "python3", "app.py" ]