# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Master'
        db.create_table('mbdb_master', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
        ))
        db.send_create_signal('mbdb', ['Master'])

        # Adding model 'Slave'
        db.create_table('mbdb_slave', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=150)),
        ))
        db.send_create_signal('mbdb', ['Slave'])

        # Adding model 'File'
        db.create_table('mbdb_file', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=400)),
        ))
        db.send_create_signal('mbdb', ['File'])

        # Adding model 'Tag'
        db.create_table('mbdb_tag', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('value', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50, db_index=True)),
        ))
        db.send_create_signal('mbdb', ['Tag'])

        # Adding model 'Change'
        db.create_table('mbdb_change', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('master', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mbdb.Master'])),
            ('branch', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('revision', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('who', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=100, null=True, blank=True)),
            ('comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('when', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('mbdb', ['Change'])

        # Adding unique constraint on 'Change', fields ['number', 'master']
        db.create_unique('mbdb_change', ['number', 'master_id'])

        # Adding M2M table for field files on 'Change'
        m2m_table_name = db.shorten_name('mbdb_change_files')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('change', models.ForeignKey(orm['mbdb.change'], null=False)),
            ('file', models.ForeignKey(orm['mbdb.file'], null=False))
        ))
        db.create_unique(m2m_table_name, ['change_id', 'file_id'])

        # Adding M2M table for field tags on 'Change'
        m2m_table_name = db.shorten_name('mbdb_change_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('change', models.ForeignKey(orm['mbdb.change'], null=False)),
            ('tag', models.ForeignKey(orm['mbdb.tag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['change_id', 'tag_id'])

        # Adding model 'SourceStamp'
        db.create_table('mbdb_sourcestamp', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('branch', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('revision', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal('mbdb', ['SourceStamp'])

        # Adding model 'NumberedChange'
        db.create_table('mbdb_numberedchange', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('change', self.gf('django.db.models.fields.related.ForeignKey')(related_name='numbered_changes', to=orm['mbdb.Change'])),
            ('sourcestamp', self.gf('django.db.models.fields.related.ForeignKey')(related_name='numbered_changes', to=orm['mbdb.SourceStamp'])),
            ('number', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
        ))
        db.send_create_signal('mbdb', ['NumberedChange'])

        # Adding model 'Property'
        db.create_table('mbdb_property', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=20, db_index=True)),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=20, db_index=True)),
            ('value', self.gf('mbdb.fields.PickledObjectField')(null=True, blank=True)),
        ))
        db.send_create_signal('mbdb', ['Property'])

        # Adding model 'Builder'
        db.create_table('mbdb_builder', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50, db_index=True)),
            ('master', self.gf('django.db.models.fields.related.ForeignKey')(related_name='builders', to=orm['mbdb.Master'])),
            ('category', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=30, null=True, blank=True)),
            ('bigState', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
        ))
        db.send_create_signal('mbdb', ['Builder'])

        # Adding model 'Build'
        db.create_table('mbdb_build', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('buildnumber', self.gf('django.db.models.fields.IntegerField')(null=True, db_index=True)),
            ('builder', self.gf('django.db.models.fields.related.ForeignKey')(related_name='builds', to=orm['mbdb.Builder'])),
            ('slave', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mbdb.Slave'], null=True, blank=True)),
            ('starttime', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('endtime', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('result', self.gf('django.db.models.fields.SmallIntegerField')(null=True, blank=True)),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('sourcestamp', self.gf('django.db.models.fields.related.ForeignKey')(related_name='builds', null=True, to=orm['mbdb.SourceStamp'])),
        ))
        db.send_create_signal('mbdb', ['Build'])

        # Adding M2M table for field properties on 'Build'
        m2m_table_name = db.shorten_name('mbdb_build_properties')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('build', models.ForeignKey(orm['mbdb.build'], null=False)),
            ('property', models.ForeignKey(orm['mbdb.property'], null=False))
        ))
        db.create_unique(m2m_table_name, ['build_id', 'property_id'])

        # Adding model 'Step'
        db.create_table('mbdb_step', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('text', self.gf('mbdb.fields.ListField')(null=True, blank=True)),
            ('text2', self.gf('mbdb.fields.ListField')(null=True, blank=True)),
            ('result', self.gf('django.db.models.fields.SmallIntegerField')(null=True, blank=True)),
            ('starttime', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('endtime', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('build', self.gf('django.db.models.fields.related.ForeignKey')(related_name='steps', to=orm['mbdb.Build'])),
        ))
        db.send_create_signal('mbdb', ['Step'])

        # Adding model 'URL'
        db.create_table('mbdb_url', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('step', self.gf('django.db.models.fields.related.ForeignKey')(related_name='urls', to=orm['mbdb.Step'])),
        ))
        db.send_create_signal('mbdb', ['URL'])

        # Adding model 'Log'
        db.create_table('mbdb_log', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=200, unique=True, null=True, blank=True)),
            ('step', self.gf('django.db.models.fields.related.ForeignKey')(related_name='logs', to=orm['mbdb.Step'])),
            ('isFinished', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('html', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('mbdb', ['Log'])

        # Adding model 'BuildRequest'
        db.create_table('mbdb_buildrequest', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('builder', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mbdb.Builder'])),
            ('submitTime', self.gf('django.db.models.fields.DateTimeField')()),
            ('sourcestamp', self.gf('django.db.models.fields.related.ForeignKey')(related_name='requests', to=orm['mbdb.SourceStamp'])),
        ))
        db.send_create_signal('mbdb', ['BuildRequest'])

        # Adding M2M table for field builds on 'BuildRequest'
        m2m_table_name = db.shorten_name('mbdb_buildrequest_builds')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('buildrequest', models.ForeignKey(orm['mbdb.buildrequest'], null=False)),
            ('build', models.ForeignKey(orm['mbdb.build'], null=False))
        ))
        db.create_unique(m2m_table_name, ['buildrequest_id', 'build_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Change', fields ['number', 'master']
        db.delete_unique('mbdb_change', ['number', 'master_id'])

        # Deleting model 'Master'
        db.delete_table('mbdb_master')

        # Deleting model 'Slave'
        db.delete_table('mbdb_slave')

        # Deleting model 'File'
        db.delete_table('mbdb_file')

        # Deleting model 'Tag'
        db.delete_table('mbdb_tag')

        # Deleting model 'Change'
        db.delete_table('mbdb_change')

        # Removing M2M table for field files on 'Change'
        db.delete_table(db.shorten_name('mbdb_change_files'))

        # Removing M2M table for field tags on 'Change'
        db.delete_table(db.shorten_name('mbdb_change_tags'))

        # Deleting model 'SourceStamp'
        db.delete_table('mbdb_sourcestamp')

        # Deleting model 'NumberedChange'
        db.delete_table('mbdb_numberedchange')

        # Deleting model 'Property'
        db.delete_table('mbdb_property')

        # Deleting model 'Builder'
        db.delete_table('mbdb_builder')

        # Deleting model 'Build'
        db.delete_table('mbdb_build')

        # Removing M2M table for field properties on 'Build'
        db.delete_table(db.shorten_name('mbdb_build_properties'))

        # Deleting model 'Step'
        db.delete_table('mbdb_step')

        # Deleting model 'URL'
        db.delete_table('mbdb_url')

        # Deleting model 'Log'
        db.delete_table('mbdb_log')

        # Deleting model 'BuildRequest'
        db.delete_table('mbdb_buildrequest')

        # Removing M2M table for field builds on 'BuildRequest'
        db.delete_table(db.shorten_name('mbdb_buildrequest_builds'))


    models = {
        'mbdb.build': {
            'Meta': {'object_name': 'Build'},
            'builder': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': "orm['mbdb.Builder']"}),
            'buildnumber': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'endtime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'properties': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'builds'", 'symmetrical': 'False', 'to': "orm['mbdb.Property']"}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'result': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slave': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mbdb.Slave']", 'null': 'True', 'blank': 'True'}),
            'sourcestamp': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'null': 'True', 'to': "orm['mbdb.SourceStamp']"}),
            'starttime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'mbdb.builder': {
            'Meta': {'object_name': 'Builder'},
            'bigState': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'category': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builders'", 'to': "orm['mbdb.Master']"}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'mbdb.buildrequest': {
            'Meta': {'object_name': 'BuildRequest'},
            'builder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mbdb.Builder']"}),
            'builds': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'requests'", 'symmetrical': 'False', 'to': "orm['mbdb.Build']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sourcestamp': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requests'", 'to': "orm['mbdb.SourceStamp']"}),
            'submitTime': ('django.db.models.fields.DateTimeField', [], {})
        },
        'mbdb.change': {
            'Meta': {'unique_together': "(('number', 'master'),)", 'object_name': 'Change'},
            'branch': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['mbdb.File']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mbdb.Master']"}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['mbdb.Tag']", 'symmetrical': 'False'}),
            'when': ('django.db.models.fields.DateTimeField', [], {}),
            'who': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        'mbdb.file': {
            'Meta': {'object_name': 'File'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '400'})
        },
        'mbdb.log': {
            'Meta': {'object_name': 'Log'},
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '200', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isFinished': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'step': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['mbdb.Step']"})
        },
        'mbdb.master': {
            'Meta': {'object_name': 'Master'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'mbdb.numberedchange': {
            'Meta': {'object_name': 'NumberedChange'},
            'change': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'numbered_changes'", 'to': "orm['mbdb.Change']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'sourcestamp': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'numbered_changes'", 'to': "orm['mbdb.SourceStamp']"})
        },
        'mbdb.property': {
            'Meta': {'object_name': 'Property'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20', 'db_index': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '20', 'db_index': 'True'}),
            'value': ('mbdb.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'})
        },
        'mbdb.slave': {
            'Meta': {'object_name': 'Slave'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'mbdb.sourcestamp': {
            'Meta': {'object_name': 'SourceStamp'},
            'branch': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'changes': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'stamps'", 'symmetrical': 'False', 'through': "orm['mbdb.NumberedChange']", 'to': "orm['mbdb.Change']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        'mbdb.step': {
            'Meta': {'object_name': 'Step'},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'steps'", 'to': "orm['mbdb.Build']"}),
            'endtime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'result': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'starttime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'text': ('mbdb.fields.ListField', [], {'null': 'True', 'blank': 'True'}),
            'text2': ('mbdb.fields.ListField', [], {'null': 'True', 'blank': 'True'})
        },
        'mbdb.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'mbdb.url': {
            'Meta': {'object_name': 'URL'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'step': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'urls'", 'to': "orm['mbdb.Step']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['mbdb']
