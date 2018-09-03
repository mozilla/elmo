# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0002_auto_20160711_2035'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='milestone',
        ),
        migrations.RemoveField(
            model_name='milestone',
            name='appver',
        ),
        migrations.RemoveField(
            model_name='milestone',
            name='signoffs',
        ),
        migrations.DeleteModel(
            name='Event',
        ),
        migrations.DeleteModel(
            name='Milestone',
        ),
    ]
