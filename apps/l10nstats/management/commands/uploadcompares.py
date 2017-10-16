# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

'Save buildbot logs from disk into ElasticSearch'
from __future__ import absolute_import, division

from datetime import datetime
import itertools

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import elasticsearch
from elasticsearch.helpers import bulk
import json
import six

from l10nstats.models import Run
from mbdb.models import Master, Log, Step
from tinder.views import generateLog, NoLogFile
from .. import LoggingCommand


class Command(LoggingCommand):
    help = 'Save compare-locales data from disk into ElasticSearch'

    def add_arguments(self, parser):
        parser.add_argument('--chunksize', default=50, type=int,
                            help='Handle n runs at a time')
        parser.add_argument('--limit', default=None, type=int,
                            help='Limit the number of chunks')
        parser.add_argument('--backwards', action='store_true',
                            help='Go back in time')

    def handleWithLogging(self, **options):
        if not (hasattr(settings, 'ES_COMPARE_INDEX') and
                hasattr(settings, 'ES_COMPARE_HOST')):
            raise CommandError('ES_COMPARE_INDEX or ES_COMPARE_HOST'
                               ' not defined in settings')
        if (not hasattr(settings, 'LOG_MOUNTS')
            or not isinstance(settings.LOG_MOUNTS, dict)):
            raise CommandError('LOG_MOUNTS is not a dict in settings')

        for master in Master.objects.order_by('-pk').values_list('name',
                                                                 flat=True):
            if master not in settings.LOG_MOUNTS:
                raise CommandError('settings.LOG_MOUNTS not defined for %s' %
                                   master)
        self.chunksize = options['chunksize']
        self.es = elasticsearch.Elasticsearch(hosts=[settings.ES_COMPARE_HOST])
        self.index = settings.ES_COMPARE_INDEX
        # get the latest comparison, in the right direction
        direction = "asc" if options['backwards'] else "desc"
        rv = self.es.search(index=self.index,
                             doc_type='comparison',
                             body={
                                "from": 0,
                                "size": 1,
                                "sort": [{"run": direction}]}
                             )
        hits = rv['hits']['hits']
        offset = hits[0]['sort'][0] if hits else None
        if offset is None:
            if options['backwards']:
                # backwards says, let's take the last run + 1,
                # and go from there
                offset = (Run.objects
                          .order_by('-pk')
                          .values_list('pk', flat=True))[0] + 1
            else:
                offset = 0
        self.handleRuns(offset, options['backwards'], options['limit'])

    def handleRuns(self, offset, backwards, limit):
        all_runs = Run.objects
        self.offset = offset
        filter_field = 'id__lt' if backwards else 'id__gt'
        if backwards:
            all_runs = all_runs.order_by('-pk')
        else:
            all_runs = all_runs.order_by('pk')
        if limit is None:
            pagenums = itertools.count()
        else:
            pagenums = xrange(limit)
        for pagenum in pagenums:
            start = datetime.now()
            # self.offset is updated in generateDocs
            runs = all_runs.filter(**{filter_field:
                                      self.offset})[:self.chunksize]
            if not runs.exists():
                # no un-indexed runs, return
                return
            passed, errors = bulk(self.es, self.generateDocs(runs),
                                  chunk_size=self.chunksize)
            self.stdout.write('Successfully indexed %d logs, ' %
                              passed)
            ellapsed = (datetime.now() - start).total_seconds()
            if ellapsed:
                docs_per_sec = passed/ellapsed
                self.stdout.write('%.2f docs per second\n' % docs_per_sec)
            else:
                self.stdout.write('really quick\n')
            if errors:
                self.stdout.write(six.text_type(errors))
                raise CommandError('failed %d docs' % len(errors))

    def generateDocs(self, runs):
        run_master = dict(runs
                          .values_list('id',
                                       'build__builder__master__name'))
        for run in runs:
            self.offset = run.id
            data = ''
            for step in (Step.objects
                         .filter(name__startswith='moz_inspectlocales',
                                 build__run=run)):
                for log in step.logs.all():
                    try:
                        for chunk in generateLog(run_master[run.id],
                                                 log.filename,
                                                 channels=(Log.JSON,)):
                            data += chunk['data']
                    except NoLogFile:
                        pass
            if not data:
                continue
            comparison = json.loads(data)
            comparison['run'] = run.id
            # we have the summary in the database, drop it
            comparison.pop('summary')
            yield {
                "_index": self.index,
                "_type": "comparison",
                "_id": run.id,
                "_source": comparison
            }
