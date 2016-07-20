# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('life', '0001_initial'),
        ('mbdb', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Active',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ModuleCount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('count', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProgressPosition',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('x', models.IntegerField()),
                ('y', models.IntegerField()),
                ('locale', models.ForeignKey(to='life.Locale')),
                ('tree', models.ForeignKey(to='life.Tree')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Run',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('srctime', models.DateTimeField(db_index=True, null=True, blank=True)),
                ('missing', models.IntegerField(default=0)),
                ('missingInFiles', models.IntegerField(default=0)),
                ('obsolete', models.IntegerField(default=0)),
                ('total', models.IntegerField(default=0)),
                ('changed', models.IntegerField(default=0)),
                ('unchanged', models.IntegerField(default=0)),
                ('keys', models.IntegerField(default=0)),
                ('errors', models.IntegerField(default=0)),
                ('report', models.IntegerField(default=0)),
                ('warnings', models.IntegerField(default=0)),
                ('completion', models.SmallIntegerField(default=0)),
                ('build', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='mbdb.Build')),
                ('locale', models.ForeignKey(to='life.Locale')),
                ('revisions', models.ManyToManyField(to='life.Changeset')),
                ('tree', models.ForeignKey(to='life.Tree')),
                ('unchangedmodules', models.ManyToManyField(related_name='runs', to='l10nstats.ModuleCount')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UnchangedInFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('module', models.CharField(max_length=50, db_index=True)),
                ('file', models.CharField(max_length=400)),
                ('count', models.IntegerField(db_index=True)),
                ('run', models.ForeignKey(to='l10nstats.Run')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='active',
            name='run',
            field=models.OneToOneField(to='l10nstats.Run'),
            preserve_default=True,
        ),
    ]
