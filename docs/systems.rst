Systems
=======

The systems involved in running elmo and feeding it with data are
as follows.

Pulse
-----

Pulse is Mozilla's RabbitMQ instance used to communicate between different
build and release automation workflows.

Taskcluster
-----------

This automation framework is used to run compare-locales and publish
the results as artifacts on tasks. The completion of such a task
is announced to the rest of the system via Pulse.

It should be possible to use both the firefox-ci-tc and the
community-tc cluster to generate data.

Worker
------

The worker listens to Pulse messages, and in response to them updates
the local clones and elmo's represenation of them.
It also inspects the Taskcluster task, retrieves meta data from
artifacts and stores them in the database.

The database also stores references to the artifacts with the detailed
information. The artifacts have a limited lifetime. It's OK for elmo
to try to load them and fail in the case that lifetime is exceeded.

There may be more than one worker.

Storage
-------

There's shared storage between to the worker and the webserver to keep
local clones of the repositories that we use to show diffs.

Webserver
---------

This is a django project, deployed as Docker container. Within the context
here, two apps and their models are of particular interest:

Life
^^^^

This models data that lives outside of elmo itself. Repositories are
represented here, as well as revisions. Also Locales are stored, and
Trees.

Trees represent an automation flow, say, Firefox on mozillla-central.
These are bound to repositories and one project or product in them.
The key information here is a project configuration file in a particular
repository.

L10nstats
^^^^^^^^^

This holds the actual statistics for a particular Tree, time, and
Revisions.
