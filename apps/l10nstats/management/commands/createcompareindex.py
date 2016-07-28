# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

'Save buildbot logs from disk into ElasticSearch'
from __future__ import absolute_import

from django.conf import settings
from django.core.management.base import CommandError
import elasticsearch

from .. import LoggingCommand

properties = {
    # the actual compare-locales data, just store as object
    "details": {
        "type": "object",
        "enabled": False
    },
    "run": {"type": "integer"}  # match SQL INT()
}


class Command(LoggingCommand):
    help = 'Create an ElasticSearch index for compare-locales data'

    def add_arguments(self, parser):
        parser.add_argument('--delete', action="store_true",
                            help="Delete an existing index (DATALOSS!)")
        parser.add_argument('--shards',
                            help="Number of shards to create")
        parser.add_argument('--replicas',
                            help="Number of replicas to create")

    def handleWithLogging(self, *args, **options):
        if not (hasattr(settings, 'ES_COMPARE_INDEX') and
                hasattr(settings, 'ES_COMPARE_HOST')):
            raise CommandError('ES_COMPARE_INDEX or ES_COMPARE_HOST'
                               ' not defined in settings')
        do_delete = options['delete']
        es = elasticsearch.Elasticsearch(hosts=[settings.ES_COMPARE_HOST])
        if do_delete:
            try:
                es.indices.delete(settings.ES_COMPARE_INDEX)
                self.stdout.write('Deleted index %s\n' %
                                  settings.ES_COMPARE_INDEX)
            except elasticsearch.TransportError:
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
            es.indices.create(index=settings.ES_COMPARE_INDEX,
                              body=indexargs)
            self.stdout.write('Created index %s\n' %
                              settings.ES_COMPARE_INDEX)
        except Exception as e:
            # this is fatal in some way, but we don't need the stack trace
            raise CommandError(e)
