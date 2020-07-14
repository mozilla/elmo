# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Consume data from pulse and insert it into the database.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

import logging

from django.conf import settings
from django.db import connection

from kombu import Queue, Exchange
from kombu.mixins import ConsumerMixin

from life.models import Forest, Repository
from pushes import utils


HGMO = Queue(
    f"queue/{settings.PULSE_USER}/hgmo",
    routing_key="#", expires=settings.PULSE_TTL,
    exchange=Exchange(
        "exchange/hgpushes/v2",
        durable=True, auto_delete=False, type="topic", passive=True,
    )
)


class ElmoConsumer(ConsumerMixin):
    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        return [
            Consumer([HGMO], callbacks=[self.on_message], accept=['json']),
        ]

    def on_message(self, body, message):
        if body['_meta']['exchange'] == HGMO.exchange.name:
            self.on_hgpushes(body['_meta'], body['payload'])
        else:
            print("UNHANDLED MESSAGE: {0!r}".format(body))
        message.ack()

    def on_hgpushes(self, meta, payload):
        repo_name = meta['routing_key']
        type_ = payload['type'].split('.', 1)[0]
        handler = getattr(self, f'on_hg_{type_}')
        if handler is None:
            logging.error(
                f"Bad message type \"{payload['type']}\" for {repo_name}"
            )
            return
        handler(repo_name, payload)
        # Close the django db connection, we won't need it until the next push
        connection.close()

    def on_hg_changegroup(self, repo_name, payload):
        try:
            repo = Repository.objects.get(name=repo_name)
        except Repository.DoesNotExist:
            logging.info(f"push:skipping {repo_name}")
            return
        new_pushid = max(
            p['pushid'] for p in payload['data']['pushlog_pushes']
        )
        print(f"push:handle {repo.url} {repo.last_known_push()}-{new_pushid}")
        pushes = utils.PushJS.pushes_for(repo, new_pushid)
        logging.info(f"push: found {len(pushes)} pushes for {repo_name}")
        utils.handlePushes(repo.id, pushes)

    def on_hg_newrepo(self, repo_name, payload):
        if '/' not in repo_name:
            return
        forest_name, locale_code = repo_name.rsplit('/', 1)
        try:
            forest = Forest.objects.get(name=forest_name)
        except Forest.DoesNotExist:
            logging.info(f"newrepo:skipping {repo_name}")
            return
        utils.handleRepo(
            repo_name, payload['data']['repo_url'], forest, locale_code
        )
