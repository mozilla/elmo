# -*- coding: utf-8 -*-
# Generated by Django 1.11.25 on 2019-11-19 09:28
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [('life', '0001_initial'), ('life', '0002_bug_1138550_unified_clones'), ('life', '0003_bug_1353850_on_delete'), ('life', '0004_auto_20191116_1511')]

    initial = True

    dependencies = [
        ('mbdb', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(help_text=b'name of the branch')),
            ],
        ),
        migrations.CreateModel(
            name='Changeset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('revision', models.CharField(db_index=True, max_length=40, unique=True)),
                ('user', models.CharField(db_index=True, default=b'', max_length=200)),
                ('description', models.TextField(default=b'', null=True)),
                ('branch', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='changesets', to='life.Branch')),
                ('files', models.ManyToManyField(to='mbdb.File')),
                ('parents', models.ManyToManyField(related_name='_children', to='life.Changeset')),
            ],
        ),
        migrations.CreateModel(
            name='Forest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('url', models.URLField()),
                ('archived', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Locale',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=30, unique=True)),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('native', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Push',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.CharField(db_index=True, max_length=200)),
                ('push_date', models.DateTimeField(db_index=True, verbose_name=b'date of push')),
                ('push_id', models.PositiveIntegerField(default=0)),
                ('changesets', models.ManyToManyField(related_name='pushes', to='life.Changeset')),
            ],
        ),
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('url', models.URLField()),
                ('archived', models.BooleanField(default=False)),
                ('changesets', models.ManyToManyField(related_name='repositories', to='life.Changeset')),
                ('forest', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='repositories', to='life.Forest')),
                ('locale', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='life.Locale')),
            ],
        ),
        migrations.CreateModel(
            name='TeamLocaleThrough',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(blank=True, default=datetime.datetime.utcnow, null=True)),
                ('end', models.DateTimeField(blank=True, null=True)),
                ('locale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teams_over_time', to='life.Locale')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='locales_over_time', to='life.Locale')),
            ],
            options={
                'ordering': ['-start', '-end'],
                'get_latest_by': 'start',
            },
        ),
        migrations.CreateModel(
            name='Tree',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True)),
                ('l10n', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='life.Forest')),
                ('repositories', models.ManyToManyField(to='life.Repository')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='teamlocalethrough',
            unique_together=set([('start', 'end', 'team', 'locale')]),
        ),
        migrations.AddField(
            model_name='push',
            name='repository',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='life.Repository'),
        ),
        migrations.AddField(
            model_name='forest',
            name='fork_of',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='forks', to='life.Forest'),
        ),
        migrations.AddField(
            model_name='repository',
            name='fork_of',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='forks', to='life.Repository'),
        ),
        migrations.AlterField(
            model_name='repository',
            name='forest',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='repositories', to='life.Forest'),
        ),
        migrations.AlterField(
            model_name='repository',
            name='locale',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='life.Locale'),
        ),
        migrations.AlterField(
            model_name='branch',
            name='name',
            field=models.TextField(help_text='name of the branch'),
        ),
        migrations.AlterField(
            model_name='changeset',
            name='description',
            field=models.TextField(default='', null=True),
        ),
        migrations.AlterField(
            model_name='changeset',
            name='user',
            field=models.CharField(db_index=True, default='', max_length=200),
        ),
        migrations.AlterField(
            model_name='push',
            name='push_date',
            field=models.DateTimeField(db_index=True, verbose_name='date of push'),
        ),
    ]
