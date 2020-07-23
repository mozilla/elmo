Taskcluster
===========

`Taskcluster`_ is used to automate the data generation for elmo.

Tasks that elmo is supposed to pick up and analyze need to publish
to a well-known route on Pulse.

.. note:: The actual route is TBD. ``project.l10n.elmo.v1`` ?

The artifact that the worker picks up needs to be called ``elmo.json``.

.. note:: Do we need the ``public/`` directory in artifacts?


From this file, the worker will find:

* The version of the file, currently ``"1.0"``.
* The version of compare-locales that generated the data, as string.
* The repository (optional).
* The list of generated comparisons.

Each artifact will contain data for all locales for a Tree, and may
contain data for more than one Tree.

.. code-block:: json

   {
     "version": "1.0",
     "compare-locales": "8.0.0",
     "repository": "https://hg.mozilla.org/l10n/gecko-strings/",
     "comparisons": []
   }

If the repository with the configurations is also the repository that
controls the Taskcluster automation, the information for that repository
is deduced from the ``task_definition["metadata"]["source"]`` metadata
from the task.

Each entry in ``comparisons`` is an object like

.. code-block:: json

   {
     "locale": "ab-CD",
     "config": "_configs/browser.toml",
     "artifact": "compares/browser.ab-CD.json",
     "revisions": {
        "/l10n/gecko-strings/": "40chars",
        "/l10n-central/ab-CD/": "40chars"
     },

     "summary": {
        "errors": 0,
        "warnings": 0,
        "missing": 2914,
        "missing_w": 18651,
        "report": 0,
        "obsolete": 0,
        "changed": 8493,
        "changed_w": 46266,
        "unchanged": 1093,
        "unchanged_w": 1419,
        "keys": 877
     }
   }

The ``locale`` value is a BCP47 locale code, ``config`` is a local path
inside the repository. ``artifact`` is the name of an artifact on the task
containing the detail compare-locales data as JSON. ``revisions`` holds the
full hash of the revision of each repository that went into this comparison.
The keys are resolved against the repository url to get the full repository
location. ``summary`` is the full summary data from compare-locales.

.. note:: In the case of a monorepo, should we deduce the revision from the source metadata?

Discovering compare-locales
---------------------------

One downside of distributed automation for elmo is that each individual
automation needs to be updated when we want a new version of compare-locales.
How can we make this discoverable?

.. _taskcluster: https://docs.taskcluster.net/docs
