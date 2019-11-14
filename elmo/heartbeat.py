# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for the main navigation pages.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from datetime import datetime
import os

from django.conf import settings
from django.http import JsonResponse

import elasticsearch

from life.models import Repository, Forest

def heartbeat(request):
    data = {
        'timestamp': datetime.utcnow().isoformat(),
    }
    status_code = 200
    # check db, and repository access
    repos = Repository.objects.filter(archived=False)
    try:
        has_repos = repos.count()
        data['db'] = 'ok'
    except Exception as e:
        has_repos = False
        data['db'] = str(e)
        status_code = 500
    if has_repos:
        try:
            os.stat(repos[0].local_path())
            data['mouns'] = 'ok'
        except Exception as e:
            data['mounts'] = str(e)
            status_code = 500
    if hasattr(settings, 'ES_COMPARE_HOST'):
        es = elasticsearch.Elasticsearch(hosts=[settings.ES_COMPARE_HOST])
        try:
            es.search(
                index=settings.ES_COMPARE_INDEX,
                doc_type='comparison',
                body={'size': 1},
            )
            data['es'] = 'ok'
        except Exception as e:
            data['es'] = str(e)
            status_code = 500
    else:
        data['es'] = 'not configured'
        status_code = 500

    if hasattr(settings, 'LOG_MOUNTS'):
        if any(os.path.isdir(p) for p in settings.LOG_MOUNTS.values()):
            data['log_mounts'] = 'ok'
    if 'log_mounts' not in data:
        data['log_mounts'] = 'not found'
        status_code = 500
    
    return JsonResponse(data, status=status_code)
