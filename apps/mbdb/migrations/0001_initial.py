# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

from django.db import models, migrations
import mbdb.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Build',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('buildnumber', models.IntegerField(null=True, db_index=True)),
                ('starttime', models.DateTimeField(null=True, blank=True)),
                ('endtime', models.DateTimeField(null=True, blank=True)),
                ('result', models.SmallIntegerField(null=True, blank=True)),
                ('reason', models.CharField(max_length=50, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Builder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50, db_index=True)),
                ('category', models.CharField(db_index=True, max_length=30, null=True, blank=True)),
                ('bigState', models.CharField(max_length=30, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BuildRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('submitTime', models.DateTimeField()),
                ('builder', models.ForeignKey(to='mbdb.Builder')),
                ('builds', models.ManyToManyField(related_name='requests', to='mbdb.Build')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Change',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.PositiveIntegerField()),
                ('branch', models.CharField(max_length=100, null=True, blank=True)),
                ('revision', models.CharField(max_length=50, null=True, blank=True)),
                ('who', models.CharField(db_index=True, max_length=100, null=True, blank=True)),
                ('comments', models.TextField(null=True, blank=True)),
                ('when', models.DateTimeField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(max_length=400)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, null=True, blank=True)),
                ('filename', models.CharField(max_length=200, unique=True, null=True, blank=True)),
                ('isFinished', models.BooleanField(default=False)),
                ('html', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Master',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NumberedChange',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(db_index=True)),
                ('change', models.ForeignKey(related_name='numbered_changes', to='mbdb.Change')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Property',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20, db_index=True)),
                ('source', models.CharField(max_length=20, db_index=True)),
                ('value', mbdb.fields.PickledObjectField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Slave',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=150)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SourceStamp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('branch', models.CharField(max_length=100, null=True, blank=True)),
                ('revision', models.CharField(max_length=50, null=True, blank=True)),
                ('changes', models.ManyToManyField(related_name='stamps', through='mbdb.NumberedChange', to='mbdb.Change')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Step',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('text', mbdb.fields.ListField(null=True, blank=True)),
                ('text2', mbdb.fields.ListField(null=True, blank=True)),
                ('result', models.SmallIntegerField(null=True, blank=True)),
                ('starttime', models.DateTimeField(null=True, blank=True)),
                ('endtime', models.DateTimeField(null=True, blank=True)),
                ('build', models.ForeignKey(related_name='steps', to='mbdb.Build')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(unique=True, max_length=50, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='URL',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
                ('url', models.URLField()),
                ('step', models.ForeignKey(related_name='urls', to='mbdb.Step')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='numberedchange',
            name='sourcestamp',
            field=models.ForeignKey(related_name='numbered_changes', to='mbdb.SourceStamp'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='log',
            name='step',
            field=models.ForeignKey(related_name='logs', to='mbdb.Step'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='change',
            name='files',
            field=models.ManyToManyField(to='mbdb.File'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='change',
            name='master',
            field=models.ForeignKey(to='mbdb.Master'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='change',
            name='tags',
            field=models.ManyToManyField(to='mbdb.Tag'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='change',
            unique_together=set([('number', 'master')]),
        ),
        migrations.AddField(
            model_name='buildrequest',
            name='sourcestamp',
            field=models.ForeignKey(related_name='requests', to='mbdb.SourceStamp'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='builder',
            name='master',
            field=models.ForeignKey(related_name='builders', to='mbdb.Master'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='build',
            name='builder',
            field=models.ForeignKey(related_name='builds', to='mbdb.Builder'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='build',
            name='properties',
            field=models.ManyToManyField(related_name='builds', to='mbdb.Property'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='build',
            name='slave',
            field=models.ForeignKey(blank=True, to='mbdb.Slave', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='build',
            name='sourcestamp',
            field=models.ForeignKey(related_name='builds', to='mbdb.SourceStamp', null=True),
            preserve_default=True,
        ),
    ]
