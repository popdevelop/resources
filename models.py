from django.conf import settings
settings.configure(DATABASE_ENGINE='sqlite3', DATABASE_NAME='database.db')

from django.db import models
from django.db.models import Avg, Max, Min, Count

class User(models.Model):
    username = models.CharField()
    realname = models.CharField()
    image = models.CharField()

    def __unicode__(self):
        return self.username
    class Meta:
        db_table = 'users'
        app_label = "myapp"

class Message(models.Model):
    user = models.ForeignKey(User)
    text = models.CharField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.username
    class Meta:
        db_table = 'messages'
        app_label = "myapp"
        get_latest_by = 'timestamp'
