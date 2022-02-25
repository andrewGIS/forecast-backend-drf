## Базовые инструкции по запуску приложения 
Прогнозирование опасных явлений на территории Урала

**Стек**

* Django + Geodjango + django-raster
* Vue + Leaflet
* Celery 

### Основные команды запуска

1 Поднимаем базу
По умолчанию БД (Postgres + PostGIS), параметры подключения к базе 
по умолчанию  указана в [settings.py](./settings.py) в корне проекта 
КЛЮЧ **DATABESES**
```.env
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'gis',
        'USER': 'docker',
        'PASSWORD': 'gis',
        'PORT': 25432
    }
}
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

1 Создаем папку `.\forecast_app\web` клонируем туда [репозиторий](https://github.com/andrewGIS/forecast-web-app) и далее по инструкции. Пробуем запустить `localhost:8000`

2 Ссылки 
* `localhost:8000\admin` - админка Django (`admin admin`)
* `localhost:8000` - приложение