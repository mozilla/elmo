# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for compare-locales output and statistics, in particular dashboards
and progress graphs.
'''
from __future__ import absolute_import, division
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import Http404
from django.views.generic.base import TemplateView
import elasticsearch

from l10nstats.models import Run


class JSONAdaptor(object):
    """Helper class to make the json output from compare-locales
    easier to digest for the django templating language.
    """
    def __init__(self, node, base):
        self.fragment = node[0]
        self.base = base
        data = node[1]
        self.children = data.get('children', [])
        if 'value' in data:
            self.value = data['value']
            if 'obsoleteFile' in self.value:
                self.fileIs = 'obsolete'
            elif 'missingFile' in self.value:
                self.fileIs = 'missing'
            elif ('missingEntity' in self.value or
                  'obsoleteEntity' in self.value or
                  'warning' in self.value or
                  'error' in self.value):
                errors = [{'key': e, 'class': 'error'}
                          for e in self.value.get('error', [])]
                warnings = [{'key': e, 'class': 'warning'}
                            for e in self.value.get('warning', [])]
                entities = \
                    [{'key': e, 'class': 'missing'}
                     for e in self.value.get('missingEntity', [])] + \
                    [{'key': e, 'class': 'obsolete'}
                     for e in self.value.get('obsoleteEntity', [])]
                entities.sort(key=lambda d: d['key'])
                self.entities = errors + warnings + entities

    @classmethod
    def adaptChildren(cls, _lst, base=''):
        for node in _lst:
            yield JSONAdaptor(node, base)

    def __iter__(self):
        if self.base:
            base = self.base + '/' + self.fragment
        else:
            base = self.fragment
        return self.adaptChildren(self.children, base)

    @property
    def path(self):
        if self.base:
            return self.base + '/' + self.fragment
        return self.fragment


class JSON2Adaptor(JSONAdaptor):
    def __init__(self, node, fragment='', base=''):
        self.fragment = fragment
        self.base = base
        self.node = node
        self.children = isinstance(self.node, dict)
        if not self.children:
            self.entities = []
            for data in self.node:
                if 'obsoleteFile' in data:
                    self.fileIs = 'obsolete'
                elif 'missingFile' in data:
                    self.fileIs = 'missing'
                elif 'missingEntity' in data:
                    self.entities.append({
                        'key': data['missingEntity'],
                        'class': 'missing'
                    })
                elif 'obsoleteEntity' in data:
                    self.entities.append({
                        'key': data['obsoleteEntity'],
                        'class': 'obsolete'
                    })
                else:
                    # warning or error, just one, but loop regardless
                    for cls, key in data.items():
                        self.entities.append({
                            'key': key,
                            'class': cls
                        })

    def __iter__(self):
        if self.children:
            if self.base:
                base = self.base + '/' + self.fragment
            else:
                base = self.fragment
            for fragment, node in sorted(self.node.items()):
                yield JSON2Adaptor(node, fragment, base)


class Counter:
    count = 0

    def increment(self):
        self.count += 1
        return str(self.count)


class CompareView(TemplateView):
    """HTML pretty-fied output of compare-locales.
    """
    template_name = 'l10nstats/compare.html'

    def get_context_data(self, **kwargs):
        context = super(CompareView, self).get_context_data(**kwargs)
        try:
            run = get_object_or_404(Run, id=self.request.GET.get('run'))
        except ValueError:
            raise Http404('Invalid ID')
        doc = self.get_doc(run)
        # JSON data from compare-locales changed with version 2.
        if doc and 'details' in doc:
            # First detect legacy format
            if isinstance(doc['details'].get('children'), list):
                nodes = list(
                    JSONAdaptor.adaptChildren(doc['details']['children']))
            else:
                # Format for compare-locales 2.0
                nodes = list(
                    JSON2Adaptor(doc['details']))
        else:
            nodes = None

        # create table widths for the progress bar
        widths = {}
        if run.total:
            for k in ('changed', 'missing', 'missingInFiles', 'report',
                      'unchanged'):
                widths[k] = getattr(run, k) * 300 // run.total
        context.update({
            'run': run,
            'nodes': nodes,
            'widths': widths,
            'counter': Counter(),
        })
        return context

    def get_doc(self, run):
        if not hasattr(settings, 'ES_KWARGS'):
            return None
        es = elasticsearch.Elasticsearch(**settings.ES_KWARGS)
        try:
            rv = es.get(index=settings.ES_COMPARE_INDEX,
                        doc_type='comparison',
                        id=run.id)
        except elasticsearch.TransportError:
            rv = {'found': False}
        if rv['found']:
            return rv['_source']
        return None
