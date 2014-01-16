# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

'Save buildbot logs from disk into ElasticSearch'

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import pyelasticsearch

properties = {
    # the actual compare-locales data, just store as object
    "details": {
        "type": "object",
        "enabled": False
    },
    "run": {"type": "integer"}  # match SQL INT()
}


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--delete', action="store_true",
                    help="Delete an existing index (DATALOSS!)"),
        make_option('--shards',
                    help="Number of shards to create"),
        make_option('--replicas',
                    help="Number of replicas to create"),
        )
    help = 'Create an ElasticSearch index for compare-locales data'

    def handle(self, *args, **options):
        if not (hasattr(settings, 'ES_COMPARE_INDEX') and
                hasattr(settings, 'ES_COMPARE_HOST')):
            raise CommandError('ES_COMPARE_INDEX or ES_COMPARE_HOST'
                               ' not defined in settings')
        do_delete = options['delete']
        es = pyelasticsearch.ElasticSearch(settings.ES_COMPARE_HOST)
        if do_delete:
            try:
                es.delete_index(settings.ES_COMPARE_INDEX)
                self.stdout.write('Deleted index %s\n' %
                                  settings.ES_COMPARE_INDEX)
            except pyelasticsearch.ElasticHttpNotFoundError:
                self.stderr.write('Index %s not found, ignoring\n' %
                                  settings.ES_COMPARE_INDEX)
        indexargs = {
            'mappings': {
                'comparison': {
                    'properties': properties
                 }
             },
             'settings': {}
            }
        if 'shards' in options:
            indexargs['settings']['number_of_shards'] = options['shards']
        if 'replicas' in options:
            indexargs['settings']['number_of_replicas'] = \
                options['replicas']
        try:
            es.create_index(settings.ES_COMPARE_INDEX, indexargs)
        except Exception, e:
            # this is fatal in some way, but we don't need the stack trace
            raise CommandError(e)
