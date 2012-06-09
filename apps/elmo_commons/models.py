# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.db import models

import datetime


class DatedManager(models.Manager):
    def for_date(self, date):
        return (self.filter(models.Q(start__lte=date) |
                            models.Q(start__isnull=True))
                .filter(models.Q(end__gt=date) |
                        models.Q(end__isnull=True)))

    def current(self):
        return self.for_date(datetime.datetime.utcnow())


class DurationThrough(models.Model):
    start = models.DateTimeField(default=datetime.datetime.utcnow,
                                 blank=True,
                                 null=True)
    end = models.DateTimeField(blank=True, null=True)
    objects = DatedManager()
    unique = ('start', 'end')

    class Meta:
        abstract = True

    class DurationMeta:
        get_latest_by = 'start'
        ordering = ['-start', '-end']
