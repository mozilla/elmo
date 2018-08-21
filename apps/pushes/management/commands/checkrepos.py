# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Command to check if any of the repositories in the database
that miss changeset mappings.
'''
from __future__ import unicode_literals

from ..base import RepositoryCommand


class Command(RepositoryCommand):
    help = 'Find repositories with missing changeset entries in the db.'

    def handleRepoWithCounts(self, dbrepo, hgrepo, dbcount, hgcount):
        """Just check if changesets counts in db and hg are the same
        """
        self.verbose("Checking " + dbrepo.name)
        if dbcount != hgcount:
            self.minimal("%s:\thg: %d\tdb: %d" %
                         (dbrepo.name, hgcount, dbcount))
