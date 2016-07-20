# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import privacy.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField()),
            ],
            options={
            },
            bases=(models.Model, privacy.models.CTMixin),
        ),
        migrations.CreateModel(
            name='Policy',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField(help_text=b'use html markup')),
                ('active', models.BooleanField(default=False)),
            ],
            options={
                'permissions': (('activate_policy', 'Can activate a policy'),),
            },
            bases=(models.Model, privacy.models.CTMixin),
        ),
        migrations.AddField(
            model_name='comment',
            name='policy',
            field=models.ForeignKey(related_name='comments', to='privacy.Policy'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='comment',
            name='who',
            field=models.ForeignKey(related_name='privacy_comments', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
