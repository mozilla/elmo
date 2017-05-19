# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def cleanUpContentTypes(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    db_alias = schema_editor.connection.alias
    (ContentType.objects.using(db_alias)
        .filter(app_label='l10nstats',
                model__in=('ModuleCount', 'UnchangedInFile'))
        .delete())


class Migration(migrations.Migration):

    dependencies = [
        ('l10nstats', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='unchangedinfile',
            name='run',
        ),
        migrations.RemoveField(
            model_name='run',
            name='unchangedmodules',
        ),
        migrations.RunPython(cleanUpContentTypes),
        migrations.DeleteModel(
            name='ModuleCount',
        ),
        migrations.DeleteModel(
            name='UnchangedInFile',
        ),
    ]
