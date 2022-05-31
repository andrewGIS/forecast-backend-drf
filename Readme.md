## Базовые инструкции по запуску приложения 
Прогнозирование опасных явлений на территории Урала

**Стек**

* Django + Geodjango + django-raster
* Vue + Leaflet
* Celery 

### Основные команды запуска

1 Поднимаем базу
По умолчанию БД (Postgres + PostGIS), параметры подключения к базе 
по умолчанию  указана в [develop.env](./develop.env) в корне проекта 
```.env
DB_NAME=gis
DB_USER=docker
DB_PASS=gis
DB_PORT=25432
#DB_HOST=localhost
DB_HOST=host.docker.internal # когда хотим подключиться к базе из докера на локалхосте
DB_ENGINE=django.contrib.gis.db.backends.postgis

```

Разработка велась c Docker, поэтому параметры такие. PostGIS Image можно взять [отсюда](https://hub.docker.com/r/kartoza/postgis/)

2 Загружаем репозиторий, создаем виртуальное окружение, устанавливаем зависимости из [requirements.txt](./requirements.txt)
```
pip3 install -r requirements.txt
```

3 Делаем миграции, после наполняем базу (пока через [SQL dump](https://drive.google.com/file/d/1zBTXPiScYeq4Q1uIE6uJ0jsA426bhtF3/view?usp=sharing))
```
python manage.py makemigrations
```

4 После этого проверяем работоспобность сервера
```
python manage.py runserver
```

### Подключение веб-сервиса

1 C мая 2022 веб-приложение живет отдельно кклонируем туда [репозиторий](https://github.com/andrewGIS/forecast-web-app) переключаемся в ветку **drf** и далее по инструкции.

2 Ссылки 
* `localhost:8000\admin` - админка Django (`admin admin`)

### Разное
* Запуск шелла в Anaconde

install `ipython, notebook`
```shell
manage.py shell_plus --notebook
```

потом в ноутбуке выполнить 
```python
import os
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
```