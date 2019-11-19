# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

from django.db import models, migrations
import datetime


def initial_data(apps, schema_editor):
    Branch = apps.get_model('life', 'branch')
    Changeset = apps.get_model('life', 'changeset')

    default_branch = Branch.objects.create(
        id=1,
        name='default'
    )
    zero_changeset = Changeset.objects.create(
        id=1,
        revision="0"*40,
        user="",
        description="",
        branch=default_branch
    )
    Changeset.parents.through.objects.create(
        from_changeset=zero_changeset,
        to_changeset=zero_changeset
    )


class Migration(migrations.Migration):

    dependencies = [
        ('mbdb', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField(help_text=b'name of the branch')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Changeset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('revision', models.CharField(unique=True, max_length=40, db_index=True)),
                ('user', models.CharField(default=b'', max_length=200, db_index=True)),
                ('description', models.TextField(default=b'', null=True)),
                ('branch', models.ForeignKey(related_name='changesets', default=1, to='life.Branch')),
                ('files', models.ManyToManyField(to='mbdb.File')),
                ('parents', models.ManyToManyField(related_name='_children', to='life.Changeset')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Forest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('url', models.URLField()),
                ('archived', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Locale',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(unique=True, max_length=30)),
                ('name', models.CharField(max_length=100, null=True, blank=True)),
                ('native', models.CharField(max_length=100, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Push',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('user', models.CharField(max_length=200, db_index=True)),
                ('push_date', models.DateTimeField(verbose_name=b'date of push', db_index=True)),
                ('push_id', models.PositiveIntegerField(default=0)),
                ('changesets', models.ManyToManyField(related_name='pushes', to='life.Changeset')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('url', models.URLField()),
                ('archived', models.BooleanField(default=False)),
                ('changesets', models.ManyToManyField(related_name='repositories', to='life.Changeset')),
                ('forest', models.ForeignKey(related_name='repositories', blank=True, to='life.Forest', null=True)),
                ('locale', models.ForeignKey(blank=True, to='life.Locale', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamLocaleThrough',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start', models.DateTimeField(default=datetime.datetime.utcnow, null=True, blank=True)),
                ('end', models.DateTimeField(null=True, blank=True)),
                ('locale', models.ForeignKey(related_name='teams_over_time', to='life.Locale')),
                ('team', models.ForeignKey(related_name='locales_over_time', to='life.Locale')),
            ],
            options={
                'ordering': ['-start', '-end'],
                'get_latest_by': 'start',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tree',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(unique=True, max_length=50)),
                ('l10n', models.ForeignKey(to='life.Forest')),
                ('repositories', models.ManyToManyField(to='life.Repository')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='teamlocalethrough',
            unique_together=set([('start', 'end', 'team', 'locale')]),
        ),
        migrations.AddField(
            model_name='push',
            name='repository',
            field=models.ForeignKey(to='life.Repository'),
            preserve_default=True,
        ),
        migrations.RunPython(initial_data, elidable=True),
    ]
