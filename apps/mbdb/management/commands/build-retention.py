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
import tarfile

from django.db.models import Min, Max
from django.conf import settings
from django.core.management.base import BaseCommand

from mbdb.models import Builder, Build, Log


class Command(BaseCommand):
    chunksize = 100
    help = __doc__
    logsoffset = timedelta(days=1)
    buildoffset = timedelta(days=7)

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', '-n', action='store_true',
                            help="Dry run, don't touch files and database")
        parser.add_argument('--backup', default=None,
                            help="Back up logs in this directory")
        parser.add_argument(
            '--limit', default=None, type=int,
            help="Limit cycles, a cycle is %d builds" % self.chunksize
        )

    def handle(self, **options):
        dry_run = options['dry_run']
        backup_dir = options['backup']
        master_for_builder = dict(
            Builder.objects.values_list('id', 'master__name')
        )
        last_builds = [
            last_build
            for last_build in Builder.objects
            .annotate(last_build=Max('builds'))
            .values_list('last_build', flat=True)
            if last_build is not None
        ]
        now = datetime.utcnow()
        logtime = now - self.logsoffset
        buildtime = now - self.buildoffset

        builds = (
            Build.objects
            .exclude(id__in=last_builds)
            .filter(endtime__lt=max(buildtime, logtime))
            .values_list('id', 'endtime', 'buildnumber',
                         'builder', 'builder__name')
        )
        if not dry_run and backup_dir:
            if not os.path.isdir(backup_dir):
                os.makedirs(backup_dir)
        buildcount = files = objects = 0
        for chunk in self.chunkBuilds(builds, options['limit']):
            if not dry_run and backup_dir:
                tarball = tarfile.open(
                    name=os.path.join(
                        backup_dir,
                        'logs-%d-%d.tar.bz2' % (chunk[0][0], chunk[-1][0])),
                    mode='w:bz2'
                )
            for buildid, endtime, buildnumber, builderid, buildername in chunk:
                if endtime >= logtime:
                    continue
                mount = settings.LOG_MOUNTS[master_for_builder[builderid]]
                logs = Log.objects.filter(step__build=buildid)
                for log in logs:
                    if log.filename:
                        arcname = log.filename
                        filename = os.path.join(mount, log.filename)
                        if not os.path.exists(filename):
                            filename += '.bz2'
                            arcname += '.bz2'
                        if os.path.exists(filename):
                            files += 1
                            if not dry_run:
                                if backup_dir:
                                    tarball.add(filename, arcname=arcname)
                                os.remove(filename)
                objects += logs.count()
                if not dry_run:
                    logs.delete()
                    builderpath = os.path.join(
                        mount,
                        buildername,
                        str(buildnumber))
                    if os.path.exists(builderpath):
                        os.remove(builderpath)
            if not dry_run and backup_dir:
                tarball.close()

            buildquery = (
                Build.objects
                     .filter(id__in=[t[0] for t in chunk],
                             endtime__lt=buildtime)
            )
            thiscount = buildquery.count()
            if thiscount:
                buildcount += thiscount
                minmax = buildquery.aggregate(min=Min('id'), max=Max('id'))
                if not dry_run:
                    buildquery.delete()
                self.stdout.write('Deleting builds from %d to %d\n' % (
                    minmax['min'], minmax['max']
                ))
            else:
                self.stdout.write('No builds to delete in this chunk\n')
        self.stdout.write('Removed %d logs with %d files\n' % (
            objects, files
        ))
        self.stdout.write('Removed %d builds\n' % buildcount)

    def chunkBuilds(self, q, limit):
        q = q.order_by('id')
        start = 0
        if limit is not None and limit <= 0:
            limit = None
        while True:
            result = list(q.filter(id__gt=start)[:self.chunksize])
            if not result:
                break
            start = result[-1][0]
            yield result
            if limit is not None:
                limit -= 1
                if not limit:
                    break
