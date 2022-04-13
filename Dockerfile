FROM osgeo/gdal:ubuntu-small-latest

WORKDIR /usr/src/app

COPY ./requirements.txt /usr/src/app/requirements.txt

RUN apt-get install --no-install-recommends -y \
    python3-pip

# Отключаем буферизацию логов
ENV PYTHONUNBUFFERED 1

RUN pip3 install -r requirements.txt

COPY . /usr/src/app/