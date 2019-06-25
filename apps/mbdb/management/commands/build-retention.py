# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Execute build and log retention policy.

We're keeping log files for a day, and build data for seven.
'''
# We also need to keep the last build for each builder, so that
# BuilderStatus.determineNextBuildNumber still works.

from __future__ import absolute_import
from __future__ import unicode_literals
from datetime import datetime, timedelta
import os.path

from django.db.models import Max
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

from mbdb.models import Builder, Build, Log, BuildRequest


class Command(BaseCommand):
    chunksize = 1000
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', '-n', action='store_true',
                            help="Dry run, don't touch files and database")
        parser.add_argument(
            '--builds-before', type=int, default=1,
            help='Clean builds older than N days (-1 for None)'
        )
        parser.add_argument(
            '--logs-before', type=int, default=1,
            help='Clean builds older than N days (-1 for None)'
        )
        parser.add_argument(
            '-W', action='store_true',
            help='Error when files to delete are missing'
        )
        parser.add_argument(
            '--limit', default=None, type=int,
            help="Limit cycles, a cycle is %d builds" % self.chunksize
        )
        parser.add_argument(
            '--chunksize', default=self.chunksize, type=int, metavar='N',
            help="Take N objects at a time"
        )

    def handle(self, **options):
        dry_run = options['dry_run']
        chunksize = options['chunksize']
        break_on_missing = options['W']
        if not dry_run:
            unlink = os.remove
        else:
            # os.stat raises the same errors as os.remove, let's build on that.
            unlink = os.stat
        master_for_builder = dict(
            Builder.objects.values_list('name', 'master__name')
        )
        last_builds = [
            last_build
            for last_build in Builder.objects
            .annotate(last_build=Max('builds'))
            .values_list('last_build', flat=True)
            if last_build is not None
        ]
        now = datetime.utcnow()
        logtime = now - timedelta(days=options['logs_before'])
        buildtime = now - timedelta(days=options['builds_before'])

        logs = (
            Log.objects
            .exclude(filename__isnull=True)
        )
        if options['logs_before'] >= 0:
            logs = logs.filter(step__build__endtime__lt=logtime)
        else:
            logs = logs.none()
        builds = (
            Build.objects
            .exclude(id__in=last_builds)
        )
        if options['builds_before'] >= 0:
            builds = builds.filter(endtime__lt=buildtime)
        else:
            builds = builds.none()
        self.stdout.write(
            'Working on {} builds and {} logs.'.format(
                Build.objects.count(),
                Log.objects.count(),
            )
        )
        buildcount = files = objects = last_build_request = 0
        for chunk in self.chunk_query(logs, chunksize, options['limit']):
            objects += chunk.count()
            for filename, buildername in chunk.values_list(
                'filename',
                'step__build__builder__name',
            ):
                mount = settings.LOG_MOUNTS[master_for_builder[buildername]]
                filename = os.path.join(mount, filename)
                try:
                    unlink(filename)
                    files += 1
                except OSError:
                    try:
                        unlink(filename + '.bz2')
                        files += 1
                    except OSError:
                        if break_on_missing:
                            raise CommandError(
                                'Log file missing: {}'.format(filename)
                            )
            if not dry_run:
                chunk.delete()
        self.stdout.write('Removed %d logs with %d files\n' % (
            objects, files
        ))

        for buildquery in self.chunk_query(
            builds, chunksize, options['limit']
        ):
            thiscount = buildquery.count()
            if thiscount:
                buildcount += thiscount
                build_ids = list(buildquery.values_list('id', flat=True))
                last_build_request = max(
                    last_build_request,
                    BuildRequest.objects
                    .filter(builds__in=build_ids)
                    .order_by('-pk')
                    .values_list('id', flat=True)
                    .first()
                    or 0
                )
                self.stdout.write('Deleting builds between %d and %d\n' % (
                    min(build_ids), max(build_ids)
                ))
                for buildername, buildnumber in buildquery.values_list(
                    'builder__name',
                    'buildnumber',
                ):
                    builderpath = os.path.join(
                        settings.LOG_MOUNTS[master_for_builder[buildername]],
                        buildername,
                        str(buildnumber))
                    try:
                        unlink(builderpath)
                        files += 1
                    except OSError:
                        if break_on_missing:
                            raise CommandError(
                                'Builder file missing: {}'.format(builderpath)
                            )
            if not dry_run:
                buildquery.delete()
        self.stdout.write('Removed %d builds\n' % buildcount)
        if dry_run:
            self.stdout.write(
                'Might remove up to %d build requests\n' %
                BuildRequest.objects.filter(id__lte=last_build_request).count()
            )
        else:
            brc, _ = (
                BuildRequest.objects
                .filter(
                    id__lte=last_build_request,
                    builds__isnull=True,
                )
                .delete()
            )
            self.stdout.write('Removed %d build requests\n' % brc)
            self.stdout.write(
                '{} builds and {} logs kept.'.format(
                    Build.objects.count(),
                    Log.objects.count(),
                )
            )
        if dry_run:
            # skip clean_builds
            return
        # Let's try to run clean_builds.
        # This might error if our master isn't idle, but that's OK, we'll
        # clean up the rest next time.
        # Only the BuildRequests were really important.
        try:
            call_command('clean_builds', stdout=self.stdout)
        except CommandError:
            pass

    def chunk_query(self, q, chunksize, limit):
        q = q.order_by('id')
        last_id = None
        if limit is not None and limit <= 0:
            limit = None
        while True:
            this_query = q
            if last_id is not None:
                this_query = this_query.filter(id__gt=last_id)
            last_id = this_query[:chunksize].aggregate(max=Max('id'))['max']
            if last_id is not None:
                this_query = this_query.filter(id__lte=last_id)
            yield this_query
            if last_id is None:
                break
            if limit is not None:
                limit -= 1
                if not limit:
                    break
