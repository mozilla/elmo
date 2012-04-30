# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Models to store the relation between buildbot masters and web heads,
to enable multiple web servers hosting multiple masters.
'''

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
