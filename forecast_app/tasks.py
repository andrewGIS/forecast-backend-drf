import time
import datetime
from typing import List

import numpy as np
from django.contrib.gis.geos import GEOSGeometry
from django.http import HttpResponse
from osgeo import osr, gdal, ogr

from celery_app import app
from django.contrib.gis.gdal import GDALRaster

from forecast_app.models import ForecastGroup, Calculation, RasterForecast, ForecastModel, VectorForecast


@app.task
def debug_task():
    print(f'++++++++++++++++Request++++++++++++')
    time.sleep(5)
    print(f'++++++++++++++++Request++++++++++++')
