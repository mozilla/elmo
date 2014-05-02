# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Forest.archived'
        db.add_column('life_forest', 'archived',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Repository.archived'
        db.add_column('life_repository', 'archived',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Forest.archived'
        db.delete_column('life_forest', 'archived')

        # Deleting field 'Repository.archived'
        db.delete_column('life_repository', 'archived')


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
            'archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
            'archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
            'path': ('django.db.models.fields.CharField', [], {'max_length': '400'})
        }
    }

    complete_apps = ['life']