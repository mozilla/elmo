# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ProjectType'
        db.create_table('webby_projecttype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
        ))
        db.send_create_signal('webby', ['ProjectType'])

        # Adding model 'Project'
        db.create_table('webby_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=80)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('is_archived', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('verbatim_url', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('l10n_repo_url', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('code_repo_url', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('stage_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('final_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('stage_auth_url', self.gf('django.db.models.fields.CharField')(max_length=250, null=True, blank=True)),
            ('stage_login', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('stage_passwd', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('string_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('word_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['webby.ProjectType'])),
        ))
        db.send_create_signal('webby', ['Project'])

        # Adding model 'Weblocale'
        db.create_table('webby_weblocale', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['webby.Project'])),
            ('locale', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['life.Locale'])),
            ('requestee', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('in_verbatim', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('in_vcs', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_on_stage', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_on_prod', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('webby', ['Weblocale'])

        # Adding unique constraint on 'Weblocale', fields ['project', 'locale']
        db.create_unique('webby_weblocale', ['project_id', 'locale_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Weblocale', fields ['project', 'locale']
        db.delete_unique('webby_weblocale', ['project_id', 'locale_id'])

        # Deleting model 'ProjectType'
        db.delete_table('webby_projecttype')

        # Deleting model 'Project'
        db.delete_table('webby_project')

        # Deleting model 'Weblocale'
        db.delete_table('webby_weblocale')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'life.locale': {
            'Meta': {'object_name': 'Locale'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'native': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        'webby.project': {
            'Meta': {'object_name': 'Project'},
            'code_repo_url': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'final_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'l10n_repo_url': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'locales': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['life.Locale']", 'symmetrical': 'False', 'through': "orm['webby.Weblocale']", 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '80'}),
            'stage_auth_url': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'stage_login': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'stage_passwd': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'stage_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'string_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['webby.ProjectType']"}),
            'verbatim_url': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'word_count': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'webby.projecttype': {
            'Meta': {'object_name': 'ProjectType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        'webby.weblocale': {
            'Meta': {'unique_together': "(('project', 'locale'),)", 'object_name': 'Weblocale'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_vcs': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'in_verbatim': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_on_prod': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_on_stage': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locale': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['life.Locale']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['webby.Project']"}),
            'requestee': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['webby']