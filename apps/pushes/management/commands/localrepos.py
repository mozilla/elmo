# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Command to update a tree of local repositories according to the status
of an upstream database.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Update set of local clones'

    def add_arguments(self, parser):
        parser.add_argument('-u', '--update', action='store_true',
                            help='Use -u for hg pull')
        parser.add_argument('-a', '--all', action='store_true',
                            help='Refresh all repositories')

    def handle(self, **options):
        update = options.get('update', False)
        all = options.get('all', False)
        pull_args = {}
        if update:
            pull_args['update'] = True
        from life.models import Repository, Changeset
        import hglib
        import os.path
        from django.conf import settings

        def resolve(path):
            return os.path.join(settings.REPOSITORY_BASE, *path.split('/'))

        # check for last push helper file
        if not all and os.path.isfile(resolve('.latest_cs')):
            latest_cs = int(open(resolve('.latest_cs')).read())
            repos = (Repository.objects
                     .filter(changesets__id__gt=latest_cs)
                     .distinct())
        else:
            repos = Repository.objects.all()
        latest_cs = Changeset.objects.order_by('-pk')[0].id

        for repo in repos:
            repopath = str(repo.local_path())
            self.stdout.write(repo.name + '\n')
            if not os.path.isdir(os.path.join(repopath, '.hg')):
                # new repo, need to clone
                if os.path.isdir(repopath):
                    self.stdout.write((
                        "\n\nCannot clone %s, "
                        "existing directory in the way\n\n") % repo.name)
                    continue
                _parent = os.path.dirname(repopath)
                if not os.path.isdir(_parent):
                    try:
                        os.makedirs(_parent)
                    except Exception as e:
                        self.stdout.write(
                            ("\n\nFailed to prepare for clone, %s\n\n"
                             % str(e))
                        )
                        continue
                try:
                    hglib.clone(str(repo.url), repopath, noupdate=not update)
                except hglib.error.CommandError as e:
                    self.stdout.write('Clone problems, %s' % str(e))
            else:
                with hglib.open(repopath) as client:
                    try:
                        client.pull(**pull_args)
                    except hglib.error.CommandError as e:
                        self.stdout.write('Pull problems, %s' % str(e))

        open(resolve('.latest_cs'), 'w').write('%i\n' % latest_cs)
