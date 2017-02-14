# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Command to fix any of the repositories in the database
that miss changeset mappings.
'''
from __future__ import absolute_import

from ..base import RepositoryCommand

from life.models import Changeset


class Command(RepositoryCommand):
    help = 'Find repositories with missing changeset entries in the db.'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--chunk-size', type=int, default=50,
                            help='Specify the chunk size to use for '
                            'changeset queries [default=50]')

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
        for revisions in self.chunk(hgrepo):
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

    def chunk(self, hgrepo):
        start = 0
        while True:
            chunk = [rev.node for rev in hgrepo.log(
                revrange='limit(rev(%d):,%d)' % (start, self.chunksize))]
            if not chunk:
                break
            yield chunk
            start += self.chunksize
