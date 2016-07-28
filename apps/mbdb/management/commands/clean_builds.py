# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Clean up mbdb data that doesn't connect to data that elmo needs.
'''
from __future__ import absolute_import

from django.core.management.base import BaseCommand, CommandError

from mbdb.models import (Builder, BuildRequest, SourceStamp, NumberedChange,
                         Change, Tag, File)


def freeze(cls):
    return (cls.objects
            .filter(id__lte=(cls.objects
                             .order_by('-pk')
                             .values_list('pk', flat=True)[0])))


class Command(BaseCommand):

    help = 'Clean up build data with no impact on elmo'

    def handle(self, *args, **options):
        # We might have race conditions with data that hasn't yet generated
        # builds that matter. Reduce the risk by only running on
        # idle builders, and limiting all queries to the data we have at
        # that point.
        if Builder.objects.exclude(bigState='idle').count():
            raise CommandError('Wait for all builders to be idle')
        buildrequests = freeze(BuildRequest)
        sourcestamps = freeze(SourceStamp)
        numberedchanges = freeze(NumberedChange)
        changes = freeze(Change)
        tags = freeze(Tag)
        files = freeze(File)

        # find build requests without builds
        q = buildrequests.filter(builds__isnull=True)
        cnt = q.count()
        if cnt:
            self.stdout.write('Deleting %d build requests\n' % cnt)
            q.delete()
        else:
            self.stdout.write('No orphaned build requests\n')

        # find source stamps without requests or builds
        q = sourcestamps.filter(builds__isnull=True, requests__isnull=True)
        cnt = q.count()
        if cnt:
            self.stdout.write('Deleting %d sourcestamps\n' % cnt)
            cnt = numberedchanges.count()
            q.delete()
            self.stdout.write('Deleted %d numbered changes, too\n' %
                              (cnt-numberedchanges.count()))
        else:
            self.stdout.write('No orphaned sourcestamps found\n')

        # find changes without sourcestamps, via numbered_changes
        q = changes.filter(numbered_changes__isnull=True)
        cnt = q.count()
        if cnt:
            self.stdout.write('Deleting %d changes\n' % cnt)
            q.delete()
        else:
            self.stdout.write('No orphaned changes found\n')
        # fall-out, we may have tags without changes now
        q = tags.filter(change__isnull=True)
        cnt = q.count()
        if cnt:
            self.stdout.write('Deleting %d tags\n' % cnt)
            q.delete()

        # find files without changes or changesets
        q = files.filter(change__isnull=True, changeset__isnull=True)
        cnt = q.count()
        if cnt:
            self.stdout.write('Deleting %d files\n' % cnt)
            q.delete()
        else:
            self.stdout.write('No orphaned files found\n')
