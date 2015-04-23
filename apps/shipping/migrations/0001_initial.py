# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import django.db.models.deletion
from django.conf import settings
import l10nstats.models


class Migration(migrations.Migration):

    dependencies = [
        ('life', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('flag', models.IntegerField(choices=[(0, b'pending'), (1, b'accepted'), (2, b'rejected'), (3, b'canceled'), (4, b'obsoleted')])),
                ('when', models.DateTimeField(default=datetime.datetime.utcnow, verbose_name=b'signoff action timestamp')),
                ('comment', models.TextField(null=True, blank=True)),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('code', models.CharField(max_length=30)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AppVersion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('version', models.CharField(max_length=10)),
                ('code', models.CharField(max_length=20, blank=True)),
                ('codename', models.CharField(max_length=30, null=True, blank=True)),
                ('accepts_signoffs', models.BooleanField(default=False)),
                ('app', models.ForeignKey(to='shipping.Application')),
                ('fallback', models.ForeignKey(related_name='followups', on_delete=django.db.models.deletion.SET_NULL, default=None, blank=True, to='shipping.AppVersion', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AppVersionTreeThrough',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start', models.DateTimeField(default=datetime.datetime.utcnow, null=True, blank=True)),
                ('end', models.DateTimeField(null=True, blank=True)),
                ('appversion', models.ForeignKey(related_name='trees_over_time', to='shipping.AppVersion')),
                ('tree', models.ForeignKey(related_name='appvers_over_time', to='life.Tree')),
            ],
            options={
                'ordering': ['-start', '-end'],
                'get_latest_by': 'start',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('type', models.IntegerField(choices=[(0, b'signoff start'), (1, b'signoff end')])),
                ('date', models.DateField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Milestone',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(unique=True, max_length=30)),
                ('name', models.CharField(max_length=50)),
                ('status', models.IntegerField(default=0, choices=[(0, b'upcoming'), (1, b'open'), (2, b'shipped')])),
                ('appver', models.ForeignKey(to='shipping.AppVersion')),
            ],
            options={
                'permissions': (('can_open', 'Can open a Milestone for sign-off'), ('can_ship', 'Can ship a Milestone')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Signoff',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('when', models.DateTimeField(default=datetime.datetime.utcnow, verbose_name=b'signoff timestamp')),
                ('appversion', models.ForeignKey(related_name='signoffs', to='shipping.AppVersion')),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('locale', models.ForeignKey(to='life.Locale')),
                ('push', models.ForeignKey(to='life.Push')),
            ],
            options={
                'permissions': (('review_signoff', 'Can review a Sign-off'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Snapshot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('test', models.IntegerField(choices=[(0, l10nstats.models.Run)])),
                ('tid', models.IntegerField()),
                ('signoff', models.ForeignKey(to='shipping.Signoff')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='milestone',
            name='signoffs',
            field=models.ManyToManyField(related_name='shipped_in', null=True, to='shipping.Signoff', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='milestone',
            field=models.ForeignKey(related_name='events', to='shipping.Milestone'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='appversiontreethrough',
            unique_together=set([('start', 'end', 'appversion', 'tree')]),
        ),
        migrations.AddField(
            model_name='appversion',
            name='trees',
            field=models.ManyToManyField(to='life.Tree', through='shipping.AppVersionTreeThrough'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='action',
            name='signoff',
            field=models.ForeignKey(to='shipping.Signoff'),
            preserve_default=True,
        ),
    ]
