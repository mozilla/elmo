# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # initial data migrations, default branch, and zero changeset
        default_branch = zero_changeset = None
        # Adding model 'Locale'
        db.create_table('life_locale', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('native', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal('life', ['Locale'])

        # Adding model 'Branch'
        db.create_table('life_branch', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('life', ['Branch'])
        if not db.dry_run:
            default_branch = orm.Branch.objects.create(
                id=1,
                name='default'
            )

        # Adding model 'Changeset'
        db.create_table('life_changeset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('revision', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40, db_index=True)),
            ('user', self.gf('django.db.models.fields.CharField')(default='', max_length=200, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(default='', null=True)),
            ('branch', self.gf('django.db.models.fields.related.ForeignKey')(default=1, related_name='changesets', to=orm['life.Branch'])),
        ))
        db.send_create_signal('life', ['Changeset'])
        if not db.dry_run:
            zero_changeset = orm.Changeset.objects.create(
                id=1,
                revision="0"*40,
                user="",
                description="",
                branch=default_branch
            )

        # Adding M2M table for field files on 'Changeset'
        m2m_table_name = db.shorten_name('life_changeset_files')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('changeset', models.ForeignKey(orm['life.changeset'], null=False)),
            ('file', models.ForeignKey(orm['mbdb.file'], null=False))
        ))
        db.create_unique(m2m_table_name, ['changeset_id', 'file_id'])

        # Adding M2M table for field parents on 'Changeset'
        m2m_table_name = db.shorten_name('life_changeset_parents')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_changeset', models.ForeignKey(orm['life.changeset'], null=False)),
            ('to_changeset', models.ForeignKey(orm['life.changeset'], null=False))
        ))
        db.create_unique(m2m_table_name, ['from_changeset_id', 'to_changeset_id'])
        # the zero_changeset has itself as parent
        if not db.dry_run:
            orm.Changeset.parents.through.objects.create(
                from_changeset=zero_changeset,
                to_changeset=zero_changeset
            )

        # Adding model 'Forest'
        db.create_table('life_forest', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal('life', ['Forest'])

        # Adding model 'Repository'
        db.create_table('life_repository', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('forest', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='repositories', null=True, to=orm['life.Forest'])),
            ('locale', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['life.Locale'], null=True, blank=True)),
        ))
        db.send_create_signal('life', ['Repository'])

        # Adding M2M table for field changesets on 'Repository'
        m2m_table_name = db.shorten_name('life_repository_changesets')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('repository', models.ForeignKey(orm['life.repository'], null=False)),
            ('changeset', models.ForeignKey(orm['life.changeset'], null=False))
        ))
        db.create_unique(m2m_table_name, ['repository_id', 'changeset_id'])

        # Adding model 'Push'
        db.create_table('life_push', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('repository', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['life.Repository'])),
            ('user', self.gf('django.db.models.fields.CharField')(max_length=200, db_index=True)),
            ('push_date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('push_id', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal('life', ['Push'])

        # Adding M2M table for field changesets on 'Push'
        m2m_table_name = db.shorten_name('life_push_changesets')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('push', models.ForeignKey(orm['life.push'], null=False)),
            ('changeset', models.ForeignKey(orm['life.changeset'], null=False))
        ))
        db.create_unique(m2m_table_name, ['push_id', 'changeset_id'])

        # Adding model 'Tree'
        db.create_table('life_tree', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('l10n', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['life.Forest'])),
        ))
        db.send_create_signal('life', ['Tree'])

        # Adding M2M table for field repositories on 'Tree'
        m2m_table_name = db.shorten_name('life_tree_repositories')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('tree', models.ForeignKey(orm['life.tree'], null=False)),
            ('repository', models.ForeignKey(orm['life.repository'], null=False))
        ))
        db.create_unique(m2m_table_name, ['tree_id', 'repository_id'])


    def backwards(self, orm):
        # Deleting model 'Locale'
        db.delete_table('life_locale')

        # Deleting model 'Branch'
        db.delete_table('life_branch')

        # Deleting model 'Changeset'
        db.delete_table('life_changeset')

        # Removing M2M table for field files on 'Changeset'
        db.delete_table(db.shorten_name('life_changeset_files'))

        # Removing M2M table for field parents on 'Changeset'
        db.delete_table(db.shorten_name('life_changeset_parents'))

        # Deleting model 'Forest'
        db.delete_table('life_forest')

        # Deleting model 'Repository'
        db.delete_table('life_repository')

        # Removing M2M table for field changesets on 'Repository'
        db.delete_table(db.shorten_name('life_repository_changesets'))

        # Deleting model 'Push'
        db.delete_table('life_push')

        # Removing M2M table for field changesets on 'Push'
        db.delete_table(db.shorten_name('life_push_changesets'))

        # Deleting model 'Tree'
        db.delete_table('life_tree')

        # Removing M2M table for field repositories on 'Tree'
        db.delete_table(db.shorten_name('life_tree_repositories'))


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