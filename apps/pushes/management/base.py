# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Command base class to do a task for a given set of repositories.
'''

import os.path
import logging

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.conf import settings

from life.models import Repository


class RepositoryCommand(BaseCommand):
    _needsNewline = False

    def handle(self, *args, **options):
        self.verbosity = options.pop('verbosity', 1)
        self.handleOptions(**options)
        from mercurial.ui import ui as _ui
        from mercurial.hg import repository

        repos = self.repos_for_names(*args)
        ui = _ui()
        for dbrepo in repos:
            repopath = str(resolve(dbrepo.name))
            if not os.path.isdir(os.path.join(repopath, '.hg')):
                self.minimal(("\n  Cannot process %s, "
                              "there's no local clone\n\n") % dbrepo.name)
                continue
            hgrepo = repository(ui, repopath)
            try:
                self.handleRepo(dbrepo, hgrepo)
            except StopIteration:
                # allow subclass to stop our loop over repositories
                break
            except StandardError:
                self.stdout.write('')
                logging.error('%s\tError while processing' % dbrepo.name,
                              exc_info=True)
                self._needsNewline = False
        if self._needsNewline:
            self.stdout.write('')

    def handleOptions(self, **options):
        """Overload to take more options
        """
        pass

    def handleRepo(self, dbrepo, hgrepo):
        """Overload this or handleRepoWithCounts for
        your command subclasses
        """
        # count the db entries, excluding changeset 000000000000
        dbcount = dbrepo.changesets.exclude(id=1).count()
        hgcount = len(hgrepo)
        return self.handleRepoWithCounts(dbrepo, hgrepo, dbcount, hgcount)

    def handleRepoWithCounts(self, dbrepo, hgrepo, dbcount, hgcount):
        """Overload this method,
        or handleRepo if you don't need changeset counts
        """
        raise NotImplementedError

    def repos_for_names(self, *names):
        repos = Repository.objects.all()
        if names:
            q = Q(name__startswith=names[0])
            for _name in names[1:]:
                q |= Q(name__startswith=_name)
            repos = repos.filter(q)
        return repos

    def minimal(self, c, wantsnewline=True):
        self._output(0, c, wantsnewline)

    def normal(self, c, wantsnewline=True):
        self._output(1, c, wantsnewline)

    def verbose(self, c, wantsnewline=True):
        self._output(2, c, wantsnewline)

    def progress(self, verbose=False):
        self._output(verbose and 2 or 1, '.',
                     wantsnewline=False, writenewline=False)

    def _output(self, verbosity, content,
                wantsnewline=True, writenewline=True):
        if verbosity > self.verbosity:
            return  # we're not that verbose
        if self._needsNewline and wantsnewline:
            self.stdout.write('\n', ending='')
        self.stdout.write(content, ending='')
        self._needsNewline = True
        if wantsnewline:
            self.stdout.write('\n', ending='')
            self._needsNewline = False
        self.stdout.flush()


def resolve(path):
    return os.path.join(settings.REPOSITORY_BASE, *path.split('/'))
