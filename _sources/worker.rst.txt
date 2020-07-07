Worker
======

The worker is implemented as a Django management command, and runs
out of the same Docker contains as the webserver. The instance is separate
from the webhead instances, though [#parallel_worker]_.

There are two functionalities the worker fulfills.

#. Update local clones in the shared storage and reflect it in the database.
#. Retrieve data from Taskcluster about finished compare-locales results
   and reflect it in the database.

Running
-------

The worker is run via

.. code-block:: bash

   ./manage.py consume-pulse

The required configuration setting is ``PULSE_USER``, which is also
used to create the queue names on pulse, ``f"queue/{settings.PULSE_USER}/*"``.

Taskcluster
-----------

To get results from Taskcluster, the worker will consume the
``exchange/taskcluster-queue/v1/task-completed`` exchange with the routing
key chose for elmo, for example ``project.l10n.elmo.v1``.

It will acknowledge the message once the meta data for all comparisons
has been created and are entered in the database.

.. note:: The Taskcluster artifacts API returns a redirect. Proposal:
   do not try to resolve the redirect immediately, but possibly do so
   on the first request through the webserver.

To be able to hook up the revisions, the worker needs to (softly) rely on
updating the clones in the jobs below.

With 'softly' we mean that we create lightweight placeholder objects
for revisions, with just the hash. The metadata and parents etc would
be set up independently.

hg.m.o
------

Elmo also consumes `hg push messages`_ from Pulse. The worker updates the
local clone and the repository metadata. This is done in parallel
to the builds triggered in Taskcluster by the pushes.

.. note:: Ensure to handle race conditions between push messages and build
   results.

Github
------

Similar infrastructure exists for `Github`_.

.. note::

   The details here will be filled out once we track projects on Github.

.. [#parallel_worker]

   It needs investigation if it's safe to run the worker in parallel.

.. _`hg push messages`: https://mozilla-version-control-tools.readthedocs.io/en/latest/hgmo/notifications.html#pulse-notifications
.. _`github`: https://mozilla-version-control-tools.readthedocs.io/en/latest/githubwebhooks.html#pulse-notifications
