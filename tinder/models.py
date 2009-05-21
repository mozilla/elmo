from django.db import models
from mbdb.models import Master

class WebHead(models.Model):
    name = models.CharField(max_length=50)
    masters = models.ManyToManyField(Master, through='MasterMap')

    def __unicode__(self):
        return self.name


class MasterMap(models.Model):
    master = models.ForeignKey(Master)
    webhead = models.ForeignKey(WebHead)

    logmount = models.CharField(max_length=200)
