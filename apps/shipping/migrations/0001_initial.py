from __future__ import absolute_import
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Application'
        db.create_table('shipping_application', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('shipping', ['Application'])

        # Adding model 'AppVersionTreeThrough'
        db.create_table('shipping_appversiontreethrough', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow, null=True, blank=True)),
            ('end', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('appversion', self.gf('django.db.models.fields.related.ForeignKey')(related_name='trees_over_time', to=orm['shipping.AppVersion'])),
            ('tree', self.gf('django.db.models.fields.related.ForeignKey')(related_name='appvers_over_time', to=orm['life.Tree'])),
        ))
        db.send_create_signal('shipping', ['AppVersionTreeThrough'])

        # Adding unique constraint on 'AppVersionTreeThrough', fields ['start', 'end', 'appversion', 'tree']
        db.create_unique('shipping_appversiontreethrough', ['start', 'end', 'appversion_id', 'tree_id'])

        # Adding model 'AppVersion'
        db.create_table('shipping_appversion', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['shipping.Application'])),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('codename', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('fallback', self.gf('django.db.models.fields.related.ForeignKey')(related_name='followups', on_delete=models.SET_NULL, default=None, to=orm['shipping.AppVersion'], blank=True, null=True)),
            ('accepts_signoffs', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('shipping', ['AppVersion'])

        # Adding model 'Signoff'
        db.create_table('shipping_signoff', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('push', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['life.Push'])),
            ('appversion', self.gf('django.db.models.fields.related.ForeignKey')(related_name='signoffs', to=orm['shipping.AppVersion'])),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('when', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow)),
            ('locale', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['life.Locale'])),
        ))
        db.send_create_signal('shipping', ['Signoff'])

        # Adding model 'Action'
        db.create_table('shipping_action', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('signoff', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['shipping.Signoff'])),
            ('flag', self.gf('django.db.models.fields.IntegerField')()),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('when', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow)),
            ('comment', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('shipping', ['Action'])

        # Adding model 'Snapshot'
        db.create_table('shipping_snapshot', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('signoff', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['shipping.Signoff'])),
            ('test', self.gf('django.db.models.fields.IntegerField')()),
            ('tid', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('shipping', ['Snapshot'])

        # Adding model 'Milestone'
        db.create_table('shipping_milestone', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('appver', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['shipping.AppVersion'])),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('shipping', ['Milestone'])

        # Adding M2M table for field signoffs on 'Milestone'
        m2m_table_name = db.shorten_name('shipping_milestone_signoffs')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('milestone', models.ForeignKey(orm['shipping.milestone'], null=False)),
            ('signoff', models.ForeignKey(orm['shipping.signoff'], null=False))
        ))
        db.create_unique(m2m_table_name, ['milestone_id', 'signoff_id'])

        # Adding model 'Event'
        db.create_table('shipping_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('type', self.gf('django.db.models.fields.IntegerField')()),
            ('date', self.gf('django.db.models.fields.DateField')()),
            ('milestone', self.gf('django.db.models.fields.related.ForeignKey')(related_name='events', to=orm['shipping.Milestone'])),
        ))
        db.send_create_signal('shipping', ['Event'])


    def backwards(self, orm):
        # Removing unique constraint on 'AppVersionTreeThrough', fields ['start', 'end', 'appversion', 'tree']
        db.delete_unique('shipping_appversiontreethrough', ['start', 'end', 'appversion_id', 'tree_id'])

        # Deleting model 'Application'
        db.delete_table('shipping_application')

        # Deleting model 'AppVersionTreeThrough'
        db.delete_table('shipping_appversiontreethrough')

        # Deleting model 'AppVersion'
        db.delete_table('shipping_appversion')

        # Deleting model 'Signoff'
        db.delete_table('shipping_signoff')

        # Deleting model 'Action'
        db.delete_table('shipping_action')

        # Deleting model 'Snapshot'
        db.delete_table('shipping_snapshot')

        # Deleting model 'Milestone'
        db.delete_table('shipping_milestone')

        # Removing M2M table for field signoffs on 'Milestone'
        db.delete_table(db.shorten_name('shipping_milestone_signoffs'))

        # Deleting model 'Event'
        db.delete_table('shipping_event')


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
        },
        'shipping.action': {
            'Meta': {'object_name': 'Action'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'flag': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'signoff': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['shipping.Signoff']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow'})
        },
        'shipping.application': {
            'Meta': {'object_name': 'Application'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'shipping.appversion': {
            'Meta': {'object_name': 'AppVersion'},
            'accepts_signoffs': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['shipping.Application']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'fallback': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'followups'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['shipping.AppVersion']", 'blank': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trees': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['life.Tree']", 'through': "orm['shipping.AppVersionTreeThrough']", 'symmetrical': 'False'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        'shipping.appversiontreethrough': {
            'Meta': {'ordering': "['-start', '-end']", 'unique_together': "(('start', 'end', 'appversion', 'tree'),)", 'object_name': 'AppVersionTreeThrough'},
            'appversion': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'trees_over_time'", 'to': "orm['shipping.AppVersion']"}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow', 'null': 'True', 'blank': 'True'}),
            'tree': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'appvers_over_time'", 'to': "orm['life.Tree']"})
        },
        'shipping.event': {
            'Meta': {'object_name': 'Event'},
            'date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'milestone': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['shipping.Milestone']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'type': ('django.db.models.fields.IntegerField', [], {})
        },
        'shipping.milestone': {
            'Meta': {'object_name': 'Milestone'},
            'appver': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['shipping.AppVersion']"}),
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'signoffs': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'shipped_in'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['shipping.Signoff']"}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'shipping.signoff': {
            'Meta': {'object_name': 'Signoff'},
            'appversion': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'signoffs'", 'to': "orm['shipping.AppVersion']"}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locale': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['life.Locale']"}),
            'push': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['life.Push']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow'})
        },
        'shipping.snapshot': {
            'Meta': {'object_name': 'Snapshot'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'signoff': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['shipping.Signoff']"}),
            'test': ('django.db.models.fields.IntegerField', [], {}),
            'tid': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['shipping']