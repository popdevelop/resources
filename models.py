from django.db import models
from django.db.models import Avg, Max, Min, Count

class Station(models.Model):
    name = models.CharField()
    key = models.CharField()
    lon = models.FloatField()
    lat = models.FloatField()

    def __unicode__(self):
        return "%s [%s] (%f, %f)" % (self.name, self.key, self.lon, self.lat)
    class Meta:
        db_table = 'stations'
        app_label = "popdemocracy"


class Line(models.Model):
    name = models.CharField()
    time = models.CharField();
    type = models.CharField();
    towards = models.CharField()

    def __unicode__(self):
        return "%s [%s]" % (self.name, self.time)
    class Meta:
        app_label = "popdemocracy"
