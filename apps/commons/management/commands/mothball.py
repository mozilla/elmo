# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Clean up mbdb data that doesn't connect to data that elmo needs.
'''

import cmd
from optparse import make_option
import os
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max, Count
from django.db.utils import DatabaseError
from django.conf import settings

from life.models import Tree, Forest
from mbdb.models import (Build, Step, Log, Property)
from l10nstats.models import (Run_Revisions)


class Repl(cmd.Cmd):
    def __init__(self, completekey='tab', stdin=None, stdout=None):
        cmd.Cmd.__init__(self, completekey='tab', stdin=None, stdout=None)
        self.dirty = False

    def do_ls(self, rest):
        '''show the list of inactive trees'''
        tree_width = len(sorted(Tree.objects.values_list('code', flat=True),
                                key=lambda c:-len(c))[0])
        fmt = '{0!s:<10}  {1:<' + str(tree_width+2) + '}{2:>6}{3:>8}\n'
        self.stdout.write(fmt.format('end date', 'code', 'runs', 'builds'))
        for t in (Tree.objects
                  .exclude(run__active__isnull=False)
                  .distinct()
                  .annotate(sm=Max("run__srctime"),
                            rc=Count("run"),
                            bc=Count("run__build")).order_by('sm')):
            self.stdout.write(fmt.format(t.sm.date() if t.sm else '',
                                         t.code, t.rc, t.bc))

    def do_builds(self, rest):
        '''clobber database and logs for builds for a given tree'''
        try:
            tree = Tree.objects.get(code=rest)
        except Tree.DoesNotExist:
            self.stdout.write('"{0}" is not a tree\n'.format(rest))
            return
        builds = (Build.objects
                  .filter(run__tree=tree))
        if not builds:
            self.stdout.write('No builds found, done\n')
            return
        self.stdout.write('Found {0} builds\n'.format(builds.count()))
        steps = (Step.objects
                 .filter(build__in=builds))
        self.stdout.write('Found {0} steps\n'.format(steps.count()))
        logs = (Log.objects
                .filter(step__in=steps))
        self.stdout.write('Found {0} logs\n'.format(logs.count()))
        self.stdout.write('Deleting log files and objects\n')
        # WARNING(assumption):
        # Let's rule out that Runs could be associated with multiple
        # Builders, and thus Masters.
        master = (builds
                  .values_list('builder__master__name',flat=True)
                  .distinct())[0]
        base = settings.LOG_MOUNTS[master]
        for f in (logs
                  .exclude(filename=None)
                  .values_list('filename', flat=True)):
            fname = os.path.join(base, f)
            if os.path.exists(fname):
                os.remove(fname)
            else:
                fname += '.bz2'
                if os.path.exists(fname):
                    os.remove(fname)
        self.bisect_delete(logs)
        self.stdout.write('Deleting steps\n')
        self.bisect_delete(steps)
        self.stdout.write('Deleting builds\n')
        self.bisect_delete(builds)
        self.dirty = True

    def complete_builds(self, text, line, begidx, endidx):
        return list(Tree.objects
                    .filter(code__startswith=text)
                    .exclude(run__active__isnull=False)
                    .distinct()
                    .values_list('code', flat=True))

    def do_cleanup(self, _):
        '''Remove all orphaned database objects.

        This is not done as part of the build command, as it's
        useful to do it once for all cleaned up builds.'''
        self.stdout.write('Deleting properties\n')
        (Property.objects
         .filter(builds__isnull=True)
         .delete())
        self.dirty = False

    def default(self, line):
        if line is 'EOF':
            if self.dirty:
                self.stdout.write('You want to `cleanup` first. '
                                  'Crtl-D to really quit\n')
                self.dirty = False
                return
            self.stdout.write('\n')
            return True
        return cmd.Cmd.default(self, line)

    def bisect_delete(self, query, recursion=0):
        """Try to delete a query. If it fails, try again on half the problem.

        MySQL Error 1153 - Got a packet bigger than 'max_allowed_packet' bytes

        The queries in this command failed on maximum packet size in
        practice. This helper does a binary tree of queries to cut
        them down into digestible chunks.
        It dies after a recursion depth of 10, assuming that that's
        good enough. After that, DatabaseError is actually just a
        DatabaseError, we guess.
        """
        try:
            query.delete()
        except DatabaseError:
            if recursion > 10:
                raise
            limit = int(query.count() / 2)
            limit = query.order_by('pk').values_list('pk',flat=True)[limit]
            self.stdout.write('Bisecting at %d\n' % limit)
            self.bisect_delete(query.filter(pk__lt=limit),
                               recursion + 1)
            self.bisect_delete(query.filter(pk__gte=limit),
                               recursion + 1)


class Command(BaseCommand):
    option_list = BaseCommand.option_list

    help = 'REPL to clean up old trees and/or their build data'

    def handle(self, *args, **options):
        repl = Repl(stdout=self.stdout)
        repl.cmdloop()
