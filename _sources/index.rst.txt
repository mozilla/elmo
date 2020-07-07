Elmo
====

Elmo is the software behind https://l10n.mozilla.org/. This documentation
describes the architecture that powers the functionality on the site.
Elmo primarily tracks the translation of Firefox and other Gecko-based
products. Expanding coverage to other projects, also ones hosted on
Github, is planned.

Key features are:

* Translation statistics over time.
* Detailed reports on errors, warnings, and stats.
* Review of translations.
* Sign-offs to keep track of revisions that passed incremental reviews.

The translation metrics and reports are created with compare-locales.
The review functionality is using local clones of the repositories, and
displays l10n-aware diffs.

Thus elmo needs to know about repositories, revisions, compare-locales
results and what actually got compared.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   systems
   taskcluster
   worker


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
