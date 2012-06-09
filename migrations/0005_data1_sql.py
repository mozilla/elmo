# data 1.1 migration, step 1
# just migrate the database scheme
# no more data migration than persisting the difference
# between tree and lasttree


def migrate():
    from django.db import models, router, connections
    from django.conf import settings
    from django.core.management import color, sql

    import datetime
    import sys
    import types

    from shipping.models import AppVersion, AppVersionTreeThrough
    from life.models import Tree
    from elmo_commons.models import DurationThrough
    ship_connection = connections[router.db_for_write(AppVersion)]

    # hardcode an intermediate model to migrate AppVersion-Tree relations
    # to AppVersionTreeThrough, and get the sql details
    mig_name = 'migration_phase_1'
    mig_models_name = mig_name + '.models'
    mig_module = types.ModuleType(mig_name)
    mig_module.models = types.ModuleType(mig_models_name)
    mig_module.__file__ = mig_name + '/__init.py'
    mig_module.models.__file__ = mig_name + '/models.py'
    sys.modules[mig_name] = mig_module
    sys.modules[mig_models_name] = mig_module.models
    settings.INSTALLED_APPS.append('migration_phase_1')
    meta_dict = dict((k, getattr(AppVersionTreeThrough._meta, k))
                     for k in ('db_table',
                               'managed',
                               'auto_created',
                               'unique_together',
                               'verbose_name',
                               'verbose_name_plural'))
    meta_dict['app_label'] = 'migration_phase_1'
    AVTT_meta = type('Meta', (object,), meta_dict)
    InterAppVersionTreeThrough = type('AppVersionTreeThrough',
                                      (DurationThrough,), {
        'Meta': AVTT_meta,
        '__module__': 'migration_phase_1.models',
        'appversion': models.ForeignKey('AppVersion',
                                        related_name='trees_over_time'),
        'tree': models.ForeignKey(Tree, related_name='appvers_over_time')
        })
    mig_module.models.AppVersionTreeThrough = InterAppVersionTreeThrough
    meta_dict = dict((k, getattr(AppVersion._meta, k))
                     for k in ('db_table',
                               'managed',
                               'auto_created',
                               'verbose_name',
                               'verbose_name_plural'))
    meta_dict['app_label'] = 'migration_phase_1'
    AV_meta = type('Meta', (object,), meta_dict)
    InterAppVersion = type('AppVersion',  (models.Model,), {
        'Meta': AV_meta,
        '__module__': 'migration_phase_1.models',
        'trees': models.ManyToManyField(Tree,
                                        through=InterAppVersionTreeThrough),
        'fallback': models.ForeignKey('self', blank=True, null=True,
                                      default=None,
                                      on_delete=models.SET_NULL,
                                      related_name='followups'),
        'accepts_signoffs': models.BooleanField(default=False),
        # tree of the previous model, name oldtree, override dbcolumn
        'tree': models.ForeignKey(Tree, blank=True, null=True),
        # lasttree works as is
        'lasttree': models.ForeignKey(Tree, related_name='legacy_appversions',
                                     blank=True, null=True)
        })
    mig_module.models.AppVersion = InterAppVersion

    c = ship_connection.cursor()
    style = color.no_style()
    for stmnt in sql.sql_all(mig_module.models,style, ship_connection):
        if stmnt.startswith('CREATE TABLE'):
            if InterAppVersionTreeThrough._meta.db_table not in stmnt:
                # appversion table, we want to ALTER, not CREATE
                # find column definitions for fallback and accepts_signoffs
                for l in stmnt.splitlines():
                    if 'fallback' in l or 'accepts_signoffs' in l:
                        c.execute('ALTER TABLE %s ADD COLUMN %s;' %
                                  (InterAppVersion._meta.db_table,
                                   l.replace(',', '')))
                continue
            else:
                # appversiontreethrough table, execute below
                pass
        elif 'ADD CONSTRAINT' in stmnt or stmnt.startswith('CREATE INDEX'):
            # add constraints and indices for the appversiontreethrough table,
            # or for the fallback field.
            if InterAppVersionTreeThrough._meta.db_table in stmnt:
                # add constraints to the new table below
                pass
            elif 'fallback' in stmnt:
                # for appversion, only add constraints for fallback
                pass
            else:
                continue
        else:
            print stmnt
        c.execute(stmnt)
    create_app_tree = InterAppVersion.trees.through.objects.create
    for av in InterAppVersion.objects.all():
        if av.tree_id is not None:
            create_app_tree(appversion=av,
                            tree_id=av.tree_id,
                            start=None)
        else:
            assert av.lasttree_id
            print "fix end of " + str(av)
            create_app_tree(appversion=av,
                            tree_id=av.lasttree_id,
                            start=None,
                            end=datetime.datetime.utcnow())

    # prune "migration_phase_1" app again
    del settings.INSTALLED_APPS[-1]
    from django.db.models import loading
    loading.cache.app_models.pop('migration_phase_1', None)
    loading.cache.register_models('migration_phase_1')  # clear cache
    # empty sys modules from our fake modules
    sys.modules.pop(mig_name)
    sys.modules.pop(mig_models_name)
    # we can only remove columns for mysql, let's warn if we're not that:
    if settings.DATABASES['default']['ENGINE'].split('.')[-1] != 'mysql':
        print """
WARNING
This migration can only remove tree and lasttree for mysql.
"""
        return
    # next up, find the foreign key indexes.
    constraints = []
    c.execute("""select CONSTRAINT_NAME
    from information_schema.table_constraints
    where table_schema = schema()
    and table_name = 'shipping_appversion';""")
    for (constraint,) in c.fetchall():
        if 'tree_id' in constraint:
            constraints.append(constraint)

    stmnt = """ALTER TABLE `shipping_appversion`"""
    subs = [' DROP COLUMN %s' % col for col in ('tree_id', 'lasttree_id')] + \
           [' DROP FOREIGN KEY %s' % constraint for constraint in constraints]
    stmnt += ','.join(subs) + ';'

    c.execute(stmnt)
