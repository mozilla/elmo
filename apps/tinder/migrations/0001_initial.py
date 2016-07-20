# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mbdb', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MasterMap',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('logmount', models.CharField(max_length=200)),
                ('master', models.ForeignKey(to='mbdb.Master')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WebHead',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('masters', models.ManyToManyField(to='mbdb.Master', through='tinder.MasterMap')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='mastermap',
            name='webhead',
            field=models.ForeignKey(to='tinder.WebHead'),
            preserve_default=True,
        ),
    ]
