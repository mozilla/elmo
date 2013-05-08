# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TeamLocaleThrough'
        db.create_table('life_teamlocalethrough', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow, null=True, blank=True)),
            ('end', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('team', self.gf('django.db.models.fields.related.ForeignKey')(related_name='locales_over_time', to=orm['life.Locale'])),
            ('locale', self.gf('django.db.models.fields.related.ForeignKey')(related_name='teams_over_time', to=orm['life.Locale'])),
        ))
        db.send_create_signal('life', ['TeamLocaleThrough'])

        # Adding unique constraint on 'TeamLocaleThrough', fields ['start', 'end', 'team', 'locale']
        db.create_unique('life_teamlocalethrough', ['start', 'end', 'team_id', 'locale_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'TeamLocaleThrough', fields ['start', 'end', 'team', 'locale']
        db.delete_unique('life_teamlocalethrough', ['start', 'end', 'team_id', 'locale_id'])

        # Deleting model 'TeamLocaleThrough'
        db.delete_table('life_teamlocalethrough')


    models = {
        'life.branch': {
            'Meta': {'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {})
        },
        'life.changeset': {
            'Meta': {'object_name': 'Changeset'},
            'branch': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'related_name': "'changesets'", 'to': "orm['life.Branch']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True'}),
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['mbdb.File']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parents': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'_children'", 'symmetrical': 'False', 'to': "orm['life.Changeset']"}),
            'revision': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'user': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200', 'db_index': 'True'})
        },
        'life.forest': {
            'Meta': {'object_name': 'Forest'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'life.locale': {
            'Meta': {'object_name': 'Locale'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'native': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        'life.push': {
            'Meta': {'object_name': 'Push'},
            'changesets': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'pushes'", 'symmetrical': 'False', 'to': "orm['life.Changeset']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'push_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'push_id': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'repository': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['life.Repository']"}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'})
        },
        'life.repository': {
            'Meta': {'object_name': 'Repository'},
            'changesets': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'repositories'", 'symmetrical': 'False', 'to': "orm['life.Changeset']"}),
            'forest': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'repositories'", 'null': 'True', 'to': "orm['life.Forest']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locale': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['life.Locale']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'life.teamlocalethrough': {
            'Meta': {'ordering': "['-start', '-end']", 'unique_together': "(('start', 'end', 'team', 'locale'),)", 'object_name': 'TeamLocaleThrough'},
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locale': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'teams_over_time'", 'to': "orm['life.Locale']"}),
            'start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow', 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'locales_over_time'", 'to': "orm['life.Locale']"})
        },
        'life.tree': {
            'Meta': {'object_name': 'Tree'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'l10n': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['life.Forest']"}),
            'repositories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['life.Repository']", 'symmetrical': 'False'})
        },
        'mbdb.file': {
            'Meta': {'object_name': 'File'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '400', 'db_index': 'True'})
        }
    }

    complete_apps = ['life']