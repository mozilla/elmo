# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Command to fix any of the repositories in the database
that miss changeset mappings.
'''
from __future__ import absolute_import

from optparse import make_option

from ..base import RepositoryCommand

from life.models import Changeset


class Command(RepositoryCommand):
    option_list = RepositoryCommand.option_list + (
        make_option('--chunk-size', type='int', default=50,
                    help='Specify the chunk size to use for '\
                    'changeset queries [default=50]'),
        )
    help = 'Find repositories with missing changeset entries in the db.'

    def handleOptions(self, **kwargs):
        self.chunksize = kwargs.get('chunk_size', self.chunksize)

    def handleRepoWithCounts(self, dbrepo, hgrepo, dbcount, hgcount):
        """Just check if changesets counts in db and hg are the same
        """
        if dbcount >= hgcount:
            # nothing to be done
            self.verbose("%s\tin good shape" % dbrepo.name)
            return
        missing = hgcount - dbcount
        cnt = 0
        through = dbrepo.changesets.through

        self.verbose("%s\t%d missing" % (dbrepo.name, missing))
        for revisions in self.chunk(self.nodes(hgrepo)):
            self.progress()
            cs = Changeset.objects.filter(revision__in=revisions)
            cs = cs.exclude(repositories=dbrepo)
            csids = list(cs.values_list('id', flat=True))
            if not csids:
                continue
            through.objects.bulk_create([
                through(repository_id=dbrepo.id, changeset_id=csid)
                for csid in csids
            ])
            cnt += len(csids)
        self.normal("%s\tadded %d changesets" % (dbrepo.name, cnt))
        return

    chunksize = 50

    def chunk(self, _iter):
        while True:
            chunk = []
            for o in _iter:
                chunk.append(o)
                if self.chunksize is not None and len(chunk) >= self.chunksize:
                    break
            if chunk:
                yield chunk
            else:
                break

    def nodes(self, hgrepo):
        for i in hgrepo:
            yield hgrepo[i].hex()
