# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ModuleCount'
        db.create_table('l10nstats_modulecount', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('count', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('l10nstats', ['ModuleCount'])

        # Adding model 'Run'
        db.create_table('l10nstats_run', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('locale', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['life.Locale'])),
            ('tree', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['life.Tree'])),
            ('build', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['mbdb.Build'], unique=True, null=True, blank=True)),
            ('srctime', self.gf('django.db.models.fields.DateTimeField')(db_index=True, null=True, blank=True)),
            ('missing', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('missingInFiles', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('obsolete', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('total', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('changed', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('unchanged', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('keys', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('errors', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('report', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('warnings', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('completion', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
        ))
        db.send_create_signal('l10nstats', ['Run'])

        # Adding M2M table for field unchangedmodules on 'Run'
        m2m_table_name = db.shorten_name('l10nstats_run_unchangedmodules')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('run', models.ForeignKey(orm['l10nstats.run'], null=False)),
            ('modulecount', models.ForeignKey(orm['l10nstats.modulecount'], null=False))
        ))
        db.create_unique(m2m_table_name, ['run_id', 'modulecount_id'])

        # Adding M2M table for field revisions on 'Run'
        m2m_table_name = db.shorten_name('l10nstats_run_revisions')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('run', models.ForeignKey(orm['l10nstats.run'], null=False)),
            ('changeset', models.ForeignKey(orm['life.changeset'], null=False))
        ))
        db.create_unique(m2m_table_name, ['run_id', 'changeset_id'])

        # Adding model 'UnchangedInFile'
        db.create_table('l10nstats_unchangedinfile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('module', self.gf('django.db.models.fields.CharField')(max_length=50, db_index=True)),
            ('file', self.gf('django.db.models.fields.CharField')(max_length=400)),
            ('count', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('run', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['l10nstats.Run'])),
        ))
        db.send_create_signal('l10nstats', ['UnchangedInFile'])

        # Adding model 'Active'
        db.create_table('l10nstats_active', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('run', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['l10nstats.Run'], unique=True)),
        ))
        db.send_create_signal('l10nstats', ['Active'])


    def backwards(self, orm):
        # Deleting model 'ModuleCount'
        db.delete_table('l10nstats_modulecount')

        # Deleting model 'Run'
        db.delete_table('l10nstats_run')

        # Removing M2M table for field unchangedmodules on 'Run'
        db.delete_table(db.shorten_name('l10nstats_run_unchangedmodules'))

        # Removing M2M table for field revisions on 'Run'
        db.delete_table(db.shorten_name('l10nstats_run_revisions'))

        # Deleting model 'UnchangedInFile'
        db.delete_table('l10nstats_unchangedinfile')

        # Deleting model 'Active'
        db.delete_table('l10nstats_active')


    models = {
        'l10nstats.active': {
            'Meta': {'object_name': 'Active'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'run': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['l10nstats.Run']", 'unique': 'True'})
        },
        'l10nstats.modulecount': {
            'Meta': {'object_name': 'ModuleCount'},
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'l10nstats.run': {
            'Meta': {'object_name': 'Run'},
            'build': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['mbdb.Build']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'changed': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'completion': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'errors': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keys': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'locale': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['life.Locale']"}),
            'missing': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'missingInFiles': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'obsolete': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'report': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'revisions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['life.Changeset']", 'symmetrical': 'False'}),
            'srctime': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tree': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['life.Tree']"}),
            'unchanged': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'unchangedmodules': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'runs'", 'symmetrical': 'False', 'to': "orm['l10nstats.ModuleCount']"}),
            'warnings': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'l10nstats.unchangedinfile': {
            'Meta': {'object_name': 'UnchangedInFile'},
            'count': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'file': ('django.db.models.fields.CharField', [], {'max_length': '400'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'run': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['l10nstats.Run']"})
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
            'path': ('django.db.models.fields.CharField', [], {'max_length': '400', 'db_index': 'True'})
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
            'value': ('mbdb.fields.PickledObjectField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'})
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
        'mbdb.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['l10nstats']
