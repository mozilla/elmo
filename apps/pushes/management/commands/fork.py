# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Command to fix any of the repositories in the database
that miss changeset mappings.
'''
from __future__ import absolute_import

from django.core.management.base import BaseCommand, CommandError
from django.utils.six.moves import input

from life.models import Forest, Repository


class Command(BaseCommand):
    help = 'Declare a Repository or Forest to be a fork '\
        'to share the local clone'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', '-n', action='store_true',
                            help='Dry run, do not change db or repos')
        parser.add_argument('orig',
                            help='Repository or Forest to fork')
        parser.add_argument('fork',
                            help='Forked Repository or Forest')

    def handle(self, orig, fork, dry_run=False, **options):
        import hglib
        try:
            orig = Repository.objects.get(name=orig)
        except Repository.DoesNotExist:
            try:
                orig = Forest.objects.get(name=orig)
            except Forest.DoesNotExist:
                raise CommandError(
                    '%s is neither Repository nor Forest' % orig)
        try:
            fork = Repository.objects.get(name=fork)
        except Repository.DoesNotExist:
            try:
                fork = Forest.objects.get(name=fork)
            except Forest.DoesNotExist:
                raise CommandError(
                    '%s is neither Repository nor Forest' % fork)
        if type(orig) is not type(fork):
            raise CommandError(
                '%s and %s need to be both Repository or Forest' %
                (orig, fork))
        if dry_run:
            confirm = 'yes'
        else:
            confirm = input(
                '''Declare
    %s
to be a fork of
    %s
and pull all changesets of the first into the latter? [yes/no] ''' %
                (self.style.WARNING(fork), self.style.WARNING(orig)))
        if confirm != 'yes':
            self.stdout.write('Aborting...')
            return
        # pulling mercurial changesets into orig
        repos = {orig.name: orig}
        forks = {orig.name: fork}
        if type(orig) is Forest:
            repos = {
                r.locale.code: r
                for r in orig.repositories.select_related('locale__code')}
            forks = {
                r.locale.code: r
                for r in fork.repositories.select_related('locale__code')}
            missing = set(forks.keys()) - set(repos.keys())
            if missing:
                raise CommandError("""Cannot fork: %s

They don't exist in %s""" % (', '.join(sorted(missing)), orig))
        for name in sorted(forks.keys()):
            hgrepo = hglib.open(repos[name].local_path())
            inc = hgrepo.incoming(path=forks[name].local_path())
            if not dry_run:
                hgrepo.pull(source=forks[name].local_path())
            self.stdout.write('{:<10}: {:>3}'.format(name, len(inc)))
            hgrepo.close()
        if not dry_run:
            fork.fork_of = orig
            fork.save()
