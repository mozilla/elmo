from __future__ import absolute_import
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'WebHead'
        db.create_table('tinder_webhead', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('tinder', ['WebHead'])

        # Adding model 'MasterMap'
        db.create_table('tinder_mastermap', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('master', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mbdb.Master'])),
            ('webhead', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tinder.WebHead'])),
            ('logmount', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('tinder', ['MasterMap'])


    def backwards(self, orm):
        # Deleting model 'WebHead'
        db.delete_table('tinder_webhead')

        # Deleting model 'MasterMap'
        db.delete_table('tinder_mastermap')


    models = {
        'mbdb.master': {
            'Meta': {'object_name': 'Master'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'tinder.mastermap': {
            'Meta': {'object_name': 'MasterMap'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logmount': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mbdb.Master']"}),
            'webhead': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tinder.WebHead']"})
        },
        'tinder.webhead': {
            'Meta': {'object_name': 'WebHead'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'masters': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['mbdb.Master']", 'through': "orm['tinder.MasterMap']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['tinder']