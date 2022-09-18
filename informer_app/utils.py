import os
from abc import ABC, abstractmethod
from datetime import timedelta

from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.db.models import QuerySet

from forecast_app.models import ForecastGroup
from informer_app.models import InfoPoint
from dataclasses import dataclass


class MessageCreator(ABC):
    separator = '\n'
    levels_aliases = {
        1: 'Очень высокая вероятность шквала',
        2: 'Высокая вероятность шквала',
        3: 'Значительная вероятность шквала',
        4: 'Умеренная вероятность шквала'
    }

    @abstractmethod
    def get_message(self, forecastDate: str, forecasts: QuerySet) -> str:
        """

        :param forecastDate: Для какой даты формируем сообщение
        :param forecasts: Прогнозы сформированные для даты
        :return:
        """
        pass

    @staticmethod
    def get_emoji_for_code(level_code: int, count =2) -> str:
        """
        Эмоджи для уровня явления

        :param level_code: Уровень риска явления
        :param count: Количество смайликов
        """
        if level_code == 1:
            return  "😱" * count
        if level_code == 2:
            return "😬" * count
        if level_code == 3:
            return "☹" * count
        if level_code == 4:
            return "🙁" * count


@dataclass
class UserMessageCreator(MessageCreator):
    userPoint: InfoPoint
    def get_message(self, forecastDate: str, forecasts: QuerySet) -> str:
        rowSeparator = MessageCreator.separator * 2
        message = f'Дата прогноза - на **{forecastDate}**'
        message += rowSeparator

        if forecasts.count() == 0:
            message += f'По текущему прогнозу для вашей точки наблюдения **{self.userPoint.name}** опасных явлений не обнаружено'
            return message

        message += f'Для вашей точки наблюдения **{self.userPoint.name}** обнаружены следующие опасные явления:'

        # какие вообще уровни есть для нашего пользователя
        level_codes = set(forecasts.values_list('level_code', flat=True))
        for level_code in sorted(level_codes):
            message += rowSeparator

            emoji = MessageCreator.get_emoji_for_code(level_code)
            level_alias = MessageCreator.levels_aliases.get(level_code)
            message += f"{emoji} ** {level_alias} ** {emoji} \n"
            message += rowSeparator

            for f in forecasts.filter(level_code=level_code).order_by('forecast_datetime_utc'):
                pntDatetime = f.forecast_datetime_utc - timedelta(hours=self.userPoint.pointFromUTCOffset)
                message += (
                    f"Время - {pntDatetime.strftime('%H:%M')};"
                    f" Явление -  {f.forecast_group.alias}; \n"
                )

        return message


@dataclass
class AdminMessageCreator(MessageCreator):
    modelName: str
    forecastType: str

    def get_message(self, forecastDate: str, forecasts: QuerySet) -> str:

        rowSeparator = MessageCreator.separator * 2

        message = 'Сообщение для **админов** сайта'
        message += rowSeparator
        message += f'Прогноз по модели **{self.modelName}**, тип - {self.forecastType}'
        message += rowSeparator
        message += f'Дата прогноза - на {forecastDate}'
        message += rowSeparator
        message += 'Обнаруженные ОЯ:'
        message += rowSeparator

        levels = set(forecasts.values_list('level_code', flat=True))
        for level in levels: # все уровни для дневного прогноза
            emoji = MessageCreator.get_emoji_for_code(level)
            message += f"{emoji} **{MessageCreator.levels_aliases.get(level)}**"
            message += rowSeparator
            eventsIds = set(forecasts.filter(level_code=level).values_list('forecast_group_id', flat=True))
            for eventId in eventsIds: # все явления определенного уровня (например сильные шквалы и сильные смерчи)
                subquery = forecasts.filter(level_code=level, forecast_group_id=eventId)
                area = AdminMessageCreator.calc_area(subquery)
                message += "".join([
                    f"Явление - **{ForecastGroup.objects.get(pk=eventId).alias}**, ",
                    f"Площадь -{area:.2f} км.кв, ",
                    f"Количество объектов- {subquery.count()};"
                ])
                message += rowSeparator

        if forecasts.count() != 0 :
            message += f'Посмотреть {os.getenv("NOTIFICATION_FRONT_ADDRESS", default="http://ogs.psu.ru:5003")}'

        return message

    @staticmethod
    def calc_area(data: QuerySet):
        wgs84 = SpatialReference('WGS84')
        # коническая альберса
        albersConic = '+proj=eqdc +lat_0=0 +lon_0=0 +lat_1=15 +lat_2=65 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m no_defs'
        albersConic = SpatialReference(albersConic)
        ct = CoordTransform(wgs84, albersConic)
        # В в квадратных километрах, важно копировать геометрию иначе на месте изменяется
        area = sum([f.mpoly.transform(ct=ct, clone=True).area for f in list(data.all())]) / 1000000
        return area
