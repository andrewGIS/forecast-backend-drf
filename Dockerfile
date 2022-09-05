FROM osgeo/gdal:ubuntu-small-latest

WORKDIR /usr/src/app

COPY ./requirements.txt /usr/src/app/requirements.txt

RUN apt-get install --no-install-recommends -y \
    python3-pip

# Отключаем буферизацию логов
ENV PYTHONUNBUFFERED 1

RUN pip3 install -r requirements.txt

#RUN groupadd djangoapp
# TODO вынести имя пользователя (в docker compose также)
RUN useradd -ms /bin/bash -d /opt/appuser -u 1500 appuser
#RUN usermod -a -G djangoapp appuser
#RUN chown -R djangoapp:appuser /var/log/celery/
#RUN chown -R djangoapp:appuser /var/run/celery/

COPY . /usr/src/app/

# Для сессий телерамма
# TODO при возможности исправить
RUN chmod 777 /usr/src/app/

USER appuser