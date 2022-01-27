import datetime

from django.contrib.gis.db import models


class ForecastModel(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=30)
    geotransform = models.CharField(max_length=100, default='(34.875, 0.25, 0.0, 65.125, 0.0, -0.25)')
    rasterWidth = models.PositiveIntegerField(default=161)
    rasterHeight = models.PositiveIntegerField(default=61)

    def __str__(self):
        return self.name


class ForecastGroup(models.Model):
    """
    Отображает для какого явления делаем прогноз
    """
    name = models.CharField(max_length=100)
    alias = models.CharField(max_length=100)

    # Returns the string representation of the model.
    def __str__(self):
        return self.alias


class InfoMixin(models.Model):
    """
    Миксин, который содержит базовую информацию о дате и типе прогноза
    """

    FORECAST_CHOICES = (
        ('OO', 'OO'),
        ('12', '12'),
    )

    FORECAST_UTC_HOURS_CHOICES = (
        ('03', '03'),
        ('09', '09'),
        ('12', '12'),
        ('15', '15'),
        ('18', '18'),
        ('21', '21'),
        ('24', '24'),
    )

    class Meta:
        abstract = True

    date_UTC_full = models.CharField(max_length=50, default='20210101')
    forecast_type = models.CharField(
        max_length=5,
        verbose_name='Тип прогноза',
        choices=FORECAST_CHOICES,
        default='00'
    )
    forecast_date = models.DateField(default=datetime.datetime(2021, 1, 1))
    forecast_datetime_utc = models.DateTimeField(default=datetime.datetime(2021, 1, 1, 3))
    forecast_hour_utc = models.CharField(
        default='00',
        max_length=5,
        verbose_name='Час прогноза',
        choices=FORECAST_UTC_HOURS_CHOICES
    )


class ForecastBaseMixin(models.Model):
    class Meta:
        abstract = True
    model = models.ForeignKey(ForecastModel, on_delete=models.CASCADE)
    forecast_group = models.ForeignKey(ForecastGroup, on_delete=models.CASCADE)


class IndexRaster(InfoMixin):

    # По какой модели сделан прогноз
    model = models.ForeignKey(ForecastModel, on_delete=models.CASCADE)
    index_name = models.CharField(max_length=150)
    raster = models.RasterField(verbose_name='Растр с иходными значениями')


class RasterForecast(InfoMixin, ForecastBaseMixin):

    raster = models.RasterField(verbose_name='Растр c оценками риска')

    # Returns the string representation of the model.
    def __str__(self):
        return f'raster - {self.forecast_group.alias} - {self.date_UTC_full}'


class VectorForecast(InfoMixin, ForecastBaseMixin):
    """
    Векторное представление прогнозов
    """

    geom = models.GeometryCollectionField(verbose_name="Геометрия", srid=4326)

    def __str__(self):
        return f'vector - {self.forecast_group.alias} - {self.date_UTC_full}'


class Variable(models.Model):
    variable = models.CharField(verbose_name='Имя переменной для использования в расчетах', max_length=50)
    index_name = models.CharField(verbose_name='Индекс для использования в расчетах', max_length=50)

    def __str__(self):
        return f"{self.variable} - {self.index_name}"


class Calculation(ForecastBaseMixin):
    """
    Отображает степень риска и порядок расчета
    """
    code = models.PositiveIntegerField(verbose_name="Уровень риска")
    expression = models.CharField(max_length=500)
    variables = models.ManyToManyField(Variable)

    def __str__(self):
        return f'{self.forecast_group} - {self.code} - {self.expression}'

    def get_variables(self):
        return "\n".join([p.index_name for p in self.variables.all()])





