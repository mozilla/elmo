# -*- coding: utf-8 -*-
# Generated by Django 1.11.25 on 2019-11-19 09:29
from __future__ import unicode_literals

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import l10nstats.models


class Migration(migrations.Migration):

    replaces = [('shipping', '0001_initial'), ('shipping', '0002_auto_20160711_2035'), ('shipping', '0003_auto_20160729_1128'), ('shipping', '0004_auto_20191116_1511')]

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('life', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('flag', models.IntegerField(choices=[(0, b'pending'), (1, b'accepted'), (2, b'rejected'), (3, b'canceled'), (4, b'obsoleted')])),
                ('when', models.DateTimeField(default=datetime.datetime.utcnow, verbose_name=b'signoff action timestamp')),
                ('comment', models.TextField(blank=True, null=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('code', models.CharField(max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='AppVersion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(max_length=10)),
                ('code', models.CharField(blank=True, max_length=20)),
                ('codename', models.CharField(blank=True, max_length=30, null=True)),
                ('accepts_signoffs', models.BooleanField(default=False)),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shipping.Application')),
                ('fallback', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='followups', to='shipping.AppVersion')),
            ],
        ),
        migrations.CreateModel(
            name='AppVersionTreeThrough',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(blank=True, default=datetime.datetime.utcnow, null=True)),
                ('end', models.DateTimeField(blank=True, null=True)),
                ('appversion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trees_over_time', to='shipping.AppVersion')),
                ('tree', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appvers_over_time', to='life.Tree')),
            ],
            options={
                'ordering': ['-start', '-end'],
                'get_latest_by': 'start',
            },
        ),
        migrations.CreateModel(
            name='Signoff',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('when', models.DateTimeField(default=datetime.datetime.utcnow, verbose_name=b'signoff timestamp')),
                ('appversion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signoffs', to='shipping.AppVersion')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('locale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='life.Locale')),
                ('push', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='life.Push')),
            ],
            options={
                'permissions': (('review_signoff', 'Can review a Sign-off'),),
            },
        ),
        migrations.CreateModel(
            name='Snapshot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('test', models.IntegerField(choices=[(0, l10nstats.models.Run)])),
                ('tid', models.IntegerField()),
                ('signoff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shipping.Signoff')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='appversiontreethrough',
            unique_together=set([('start', 'end', 'appversion', 'tree')]),
        ),
        migrations.AddField(
            model_name='appversion',
            name='trees',
            field=models.ManyToManyField(through='shipping.AppVersionTreeThrough', to='life.Tree'),
        ),
        migrations.AddField(
            model_name='action',
            name='signoff',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shipping.Signoff'),
        ),
        migrations.AlterField(
            model_name='action',
            name='flag',
            field=models.IntegerField(choices=[(0, 'pending'), (1, 'accepted'), (2, 'rejected'), (3, 'canceled'), (4, 'obsoleted')]),
        ),
        migrations.AlterField(
            model_name='action',
            name='when',
            field=models.DateTimeField(default=datetime.datetime.utcnow, verbose_name='signoff action timestamp'),
        ),
        migrations.AlterField(
            model_name='signoff',
            name='when',
            field=models.DateTimeField(default=datetime.datetime.utcnow, verbose_name='signoff timestamp'),
        ),
    ]
