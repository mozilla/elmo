Workflow
========

The workflow app allows elmo to display processes outside and inside of
bugs.

The concept is that there are *Tasks* that correspond to bugs. There is
a hierarchy of *Processes* putting those bugs into a structure, and
*Steps* that allow to keep track of details within bugs that need some
traction, but that don't really warrant their own bug necessarily.

These objects have prototypes, which on the one hand allow horizontal
filtering, but also allow to modify the process without having to recreate
the workflow for each locale.

Which leads to the next feature, all process elements are instantiated
*lazily*, that is, only when a team gets to work on them, they're actually
created. Up to then, the workflow shown is that of the prototypes, and 
adjusts as those modify over time.

Entry points to processes are marked up by XXX. They're also varying over time,
such that we can see that a particular process used to start here, but
is not available to be instantiated again.


Todos
-----

We might want to do meta processes to create processes for particular
campaigns. Think of a "project pages on bedrock", creating a process
for "15 years of Fx on bedrock", which is then instantiated for all
participating locales.

General priority queue:
1. dogfood
2. project (relate processes to Firefox, Fennec, others)
3. meta-processes
