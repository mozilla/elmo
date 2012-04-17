# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#  Axel Hecht <l10n@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''Command base class to do a task for a given set of repositories.
'''

import os.path
import sys
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
                print
                logging.error('%s\tError while processing' % dbrepo.name,
                              exc_info=True)
                self._needsNewline = False
        if self._needsNewline:
            print

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
            sys.stdout.write('\n')
        sys.stdout.write(content)
        self._needsNewline = True
        if wantsnewline:
            sys.stdout.write('\n')
            self._needsNewline = False
        sys.stdout.flush()


def resolve(path):
    return os.path.join(settings.REPOSITORY_BASE, *path.split('/'))
