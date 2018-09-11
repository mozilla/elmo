# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='milestone',
            name='signoffs',
            field=models.ManyToManyField(related_name='shipped_in', to='shipping.Signoff', blank=True),
        ),
    ]
