# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Weblocale', fields ['project', 'locale']
        db.delete_unique('webby_weblocale', ['project_id', 'locale_id'])

        # Deleting model 'Weblocale'
        db.delete_table('webby_weblocale')

        # Deleting model 'ProjectType'
        db.delete_table('webby_projecttype')

        # Deleting model 'Project'
        db.delete_table('webby_project')


    def backwards(self, orm):
        # Adding model 'Weblocale'
        db.create_table('webby_weblocale', (
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['webby.Project'])),
            ('requestee', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('in_verbatim', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('in_vcs', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('locale', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['life.Locale'])),
            ('is_on_stage', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('is_on_prod', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('webby', ['Weblocale'])

        # Adding unique constraint on 'Weblocale', fields ['project', 'locale']
        db.create_unique('webby_weblocale', ['project_id', 'locale_id'])

        # Adding model 'ProjectType'
        db.create_table('webby_projecttype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
        ))
        db.send_create_signal('webby', ['ProjectType'])

        # Adding model 'Project'
        db.create_table('webby_project', (
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=80)),
            ('final_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('verbatim_url', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('stage_passwd', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('is_archived', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('stage_login', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('stage_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('word_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['webby.ProjectType'])),
            ('l10n_repo_url', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('string_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('stage_auth_url', self.gf('django.db.models.fields.CharField')(max_length=250, null=True, blank=True)),
            ('code_repo_url', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
        ))
        db.send_create_signal('webby', ['Project'])


    models = {
        
    }

    complete_apps = ['webby']