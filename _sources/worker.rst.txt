Worker
======

The worker is implemented as a Django management command, and runs
out of the same Docker contains as the webserver. It's not the same instance,
though.

There are two functionalities the worker fulfills.

#. Update local clones in the shared storage and reflect it in the database.
#. Retrieve data from Taskcluster about finished compare-locales results
   and reflect it in the database.

Taskcluster
-----------

To get results from Taskcluster, the worker will consume the
``exchange/taskcluster-queue/v1/task-completed`` exchange with the routing
key chose for elmo, for example ``project.l10n.elmo.v1``.

It will acknowledge the message once the meta data for all comparisons
has been created, and all the revisions are entered in the database.

.. note:: The Taskcluster artifacts API returns a redirect. Proposal:
   do not try to resolve the redirect immediately, but possibly do so
   on the first request through the webserver.

To be able to hook up the revisions, the worker needs to

* either update the local clone and the repository metadata as part of this job,
* or (softly) rely on updating the clones in different jobs.

With 'softly' we mean that we could create lightweight placeholder objects
for revisions, with just the hash. The metadata and parents etc would
be set up independently.

hg.m.o
------

Taskcluster automation kicks off based on `hg push messages`_ in Pulse.
Thus the worker could consume an exchange of those notifications as well.

.. note:: How likely would we see race conditions?

Github
------

Similar infrastructure exists for `Github`_.

.. _`hg push messages`: https://mozilla-version-control-tools.readthedocs.io/en/latest/hgmo/notifications.html#pulse-notifications
.. _`github`: https://mozilla-version-control-tools.readthedocs.io/en/latest/githubwebhooks.html#pulse-notifications
