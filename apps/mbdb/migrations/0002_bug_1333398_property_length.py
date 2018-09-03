# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mbdb', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='property',
            name='name',
            field=models.CharField(max_length=40, db_index=True),
        ),
    ]
