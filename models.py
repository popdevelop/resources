from django.conf import settings
settings.configure(DATABASE_ENGINE='sqlite3', DATABASE_NAME='database.db')

from django.db import models
from django.db.models import Avg, Max, Min, Count

class Stop(models.Model):
    name = models.CharField()
    lon = models.FloatField()
    lat = models.FloatField()

    def __unicode__(self):
        return self.name
    class Meta:
        db_table = 'stops'
        app_label = "codemocracy"
