# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

'Save buildbot logs from disk into ElasticSearch'

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.paginator import Paginator
import pyelasticsearch
import simplejson

from l10nstats.models import Run
from mbdb.models import Master, Log, Step
from tinder.views import generateLog


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--chunksize', default=50, type='int',
                    help='Handle n runs at a time'),
        make_option('--limit', default=None, type='int',
                    help='Limit the number of chunks'),
        make_option('--backwards', action='store_true',
                    help='Go back in time'),
        )
    help = 'Save compare-locales data from disk into ElasticSearch'

    def handle(self, *args, **options):
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
        self.es = pyelasticsearch.ElasticSearch(settings.ES_COMPARE_HOST)
        self.index = settings.ES_COMPARE_INDEX
        # get the latest comparison, in the right direction
        direction = "asc" if options['backwards'] else "desc"
        rv = self.es.search({"from": 0,
                             "size": 1,
                             "sort": [{"run": direction}]},
                             index=self.index,
                             doc_type='comparison')
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
        if backwards:
            all_runs = all_runs.filter(id__lt=offset).order_by('-pk')
        else:
            all_runs = all_runs.filter(id__gt=offset).order_by('pk')
        pages = Paginator(all_runs, self.chunksize)
        for pagenum in pages.page_range:
            if limit and pagenum > limit:
                return
            docs = []
            runs = pages.page(pagenum).object_list
            if not runs.exists():
                # no un-indexed runs, return
                return
            run_master = dict(runs
                              .values_list('id',
                                           'build__builder__master__name'))
            for run in runs:
                json = ''
                for step in (Step.objects
                             .filter(name__startswith='moz_inspectlocales',
                                     build__run=run)):
                    for log in step.logs.all():
                        for chunk in generateLog(run_master[run.id],
                                                 log.filename,
                                                 channels=(Log.JSON,)):
                            json += chunk['data']
                if not json:
                    continue
                comparison = simplejson.loads(json)
                comparison['run'] = run.id
                # we have the summary in the database, drop it
                comparison.pop('summary')

                docs.append(comparison)
            rv = self.es.bulk_index(self.index, 'comparison', docs,
                                    id_field='run')
            good = 0
            bad = []
            for item in rv['items']:
                item = item['index']
                if item.get('ok'):
                    good += 1
                else:
                    bad.append(item)
            if bad:
                self.stderr.write(json.dumps(bad, indent=2) + '\n')
                raise CommandError()
            self.stdout.write('wrote %d good comparisons in %d ms\n' %
                              (good, rv['took']))
