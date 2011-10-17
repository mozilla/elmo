# Copyright (C) 2010, 2011 Linaro Limited
#
# Author: Zygmunt Krynicki <zygmunt.krynicki@linaro.org>
#
# This file is part of versiontools.
#
# versiontools is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation
#
# versiontools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with versiontools.  If not, see <http://www.gnu.org/licenses/>.

"""
About
=====

Define *single* and *useful* ``__version__`` of a project.

.. Note: Since version 1.1 we should conform to PEP 386

"""


__version__ = (1, 8, 0, "final", 0)


import inspect
import operator
import os
import sys


class Version(tuple):
    """
    Version class suitable to be used in module's __version__

    Version class is a tuple and has the same logical components as
    :data:`sys.version_info`.
    """

    _RELEASELEVEL_TO_TOKEN = {
        "alpha": "a",
        "beta": "b",
        "candidate": "c",
    }

    def __new__(cls, major, minor, micro=0, releaselevel="final", serial=0):
        """
        Construct a new version tuple.

        There is some extra logic when initializing tuple elements. All
        variables except for releaselevel are silently converted to integers
        That is::

            >>> Version("1.2.3.dev".split("."))
            (1, 2, 3, "dev", 0)

        :param major:
            Major version number

        :type major:
            :class:`int` or :class:`str`

        :param minor:
            Minor version number

        :type minor:
            :class:`int` or :class:`str`

        :param micro:
            Micro version number, defaults to ``0``.

        :type micro:
            :class:`int` or :class:`str`

        :param releaselevel:
            Release level name.

            There is a constraint on allowed values of releaselevel. Only the
            following values are permitted:

            * 'dev'
            * 'alpha'
            * 'beta'
            * 'candidate'
            * 'final'

        :type releaselevel:
            :class:`str`

        :param serial:
            Serial number, usually zero, only used for alpha, beta and
            candidate versions where it must be greater than zero.

        :type micro:
            :class:`int` or :class:`str`

        :raises ValueError:
            If releaselevel is incorrect, a version component is negative or
            serial is 0 and releaselevel is alpha, beta or candidate.
        """
        def to_int(v):
            v = int(v)
            if v < 0:
                raise ValueError("Version components cannot be negative")
            return v

        major = to_int(major)
        minor = to_int(minor)
        micro = to_int(micro)
        serial = to_int(serial)
        if releaselevel not in ('dev', 'alpha', 'beta', 'candidate', 'final'):
            raise ValueError(
                "releaselevel %r is not permitted" % (releaselevel,))
        if releaselevel in ('alpha', 'beta', 'candidate') and serial == 0:
            raise ValueError(
                ("serial must be greater than zero for"
                 " %s releases") % releaselevel)
        obj = tuple.__new__(cls, (major, minor, micro, releaselevel, serial))
        object.__setattr__(obj, '_source_tree', cls._find_source_tree())
        object.__setattr__(obj, '_vcs', None)
        return obj

    major = property(
        operator.itemgetter(0),
        doc="Major version number")

    minor = property(
        operator.itemgetter(1),
        doc="Minor version number")

    micro = property(
        operator.itemgetter(2),
        doc="Micro version number")

    releaselevel = property(
        operator.itemgetter(3),
        doc="Release level string")

    serial = property(
        operator.itemgetter(4),
        doc="Serial number")

    @property
    def vcs(self):
        """
        Return VCS integration object, if any.

        Accessing this attribute for the first time will query VCS lookup (may
        be slower, will trigger imports of various VCS plugins).

        The returned object, if not None, should have at least `revno`
        property. For details see your particular version control integration
        plugin.

        .. note::
            This attribute is **not** an element of the version tuple
            and thus does not break sorting.

        .. versionadded:: 1.0.4
        """
        if self._vcs is None:
            self._vcs = self._query_vcs()
        return self._vcs

    @classmethod
    def from_tuple(cls, version_tuple):
        """
        Create version from 5-element tuple

        .. note::
            This method is identical to the constructor, just spelled in a way
            that is more obvious to use.

        .. versionadded:: 1.1
        """
        return cls(*version_tuple)

    @classmethod
    def from_tuple_and_hint(cls, version_tuple, hint):
        """
        Create version from a 5-element tuple and VCS location hint.

        Similar to :meth:`~versiontools.Version.from_tuple` but uses the hint
        object to locate the source tree if needed. A good candidate for hint
        object is the module that contains the version_tuple. In general
        anything that works with :meth:`inspect.getsourcefile()` is good.

        .. versionadded:: 1.4
        """
        self = cls.from_tuple(version_tuple)
        if self._source_tree is None:
            path = inspect.getsourcefile(hint)
            if path is not None:
                self._source_tree = os.path.dirname(os.path.abspath(path))
        return self

    def __str__(self):
        """
        Return a string representation of the version tuple.

        The string is not a direct concatenation of all version components.
        Instead it's a more natural 'human friendly' version where components
        with certain values are left out.

        The following table shows how a version tuple gets converted to a
        version string.

        +-------------------------------+-------------------+
        | __version__                   | Formatter version |
        +===============================+===================+
        | ``(1, 2, 0, "final", 0)``     | ``"1.2"``         |
        +-------------------------------+-------------------+
        | ``(1, 2, 3, "final", 0)``     | ``"1.2.3"``       |
        +-------------------------------+-------------------+
        | ``(1, 3, 0, "alpha", 1)``     | ``"1.3a1"``       |
        +-------------------------------+-------------------+
        | ``(1, 3, 0, "beta", 1)``      | ``"1.3b1"``       |
        +-------------------------------+-------------------+
        | ``(1, 3, 0, "candidate", 1)`` | ``"1.3c1"``       |
        +-------------------------------+-------------------+
        | ``(1, 3, 0, "dev", 0)``       | ``"1.3.dev"``     |
        +-------------------------------+-------------------+

        Now when release level is set to ``"dev"`` then interesting things
        start to happen.  When possible, version control system is queried for
        revision or changeset identifier. This information gets used to create
        a more useful version string. The suffix gets appended to the base
        version string. So for example a full version string, when using Bazaar
        might look like this: ``"1.3.dev54"`` which indicates that the tree was
        at revision 54 at that time.

        The following table describes what gets appended by each version
        control system.

        +-----------+------------------------------------------------+
        | VCS       | Formatted version suffix                       |
        +===========+================================================+
        | Bazaar    | Revision number (revno),  e.g. ``54``          |
        +-----------+------------------------------------------------+
        | Git       | Head commit ID (sha1), e.g.                    |
        |           | ``"e40105c58a162de822b63d28b63f768a9763fbe3"`` |
        +-----------+------------------------------------------------+
        | Mercurial | Tip revision number, e.g. ``54``               |
        +-----------+------------------------------------------------+

        .. note::
            This logic is implemented in :meth:`versiontools.Version.__str__()`
            and can be overridden by sub-classes. You can use project-specific
            logic if required. To do that replace __version__ with an instance
            of your sub-class.
        """
        version = "%s.%s" % (self.major, self.minor)
        if self.micro != 0:
            version += ".%s" % self.micro
        token = self._RELEASELEVEL_TO_TOKEN.get(self.releaselevel)
        if token:
            version += "%s%d" % (token, self.serial)
        if self.releaselevel == "dev":
            if self.vcs is not None:
                version += ".dev%s" % self.vcs.revno
            else:
                version += ".dev"
        return version

    @classmethod
    def _find_source_tree(cls):
        """
        Find the absolute pathname of the tree that contained the file that
        called our __init__()
        """
        frame = inspect.currentframe()
        outer_frames = inspect.getouterframes(frame)
        for index0, record in enumerate(outer_frames):
            frame, filename, lineno, func_name, context, context_index = record
            if context is None or context_index >= len(context):
                continue
            if (func_name == "<module>" and "__version__" in
                context[context_index]):
                caller = frame
                break
        else:
            caller = None
        if caller:
            return os.path.dirname(
                os.path.abspath(
                    inspect.getsourcefile(caller)))

    def _query_vcs(self):
        """
        Attempt to build a VCS object for the directory refrenced in
        self._source_tree.

        The actual version control integration is pluggable, anything that
        provides an entrypoint for ``versintools.vcs_integration`` is
        considered. The first version control system that indicates support for
        the directory wins.

        In practice you'd want to use the vcs property.
        """
        import pkg_resources
        if self._source_tree is None:
            return
        for entrypoint in pkg_resources.iter_entry_points(
            "versiontools.vcs_integration"):
            try:
                integration_cls = entrypoint.load()
                integration = integration_cls.from_source_tree(
                    self._source_tree)
                if integration:
                    return integration
            except ImportError:
                pass


def format_version(version, hint=None):
    """
    Pretty formatting for 5-element version tuple.

    :param version:
        The version to format

    :type version:
        A :class:`tuple` with five elements, as the one provided to
        :meth:`versiontools.Version.from_tuple`, or an existing instance of
        :class:`versiontools.Version`.

    :param hint:
        The hint object, if provided, helps versiontools to locate the
        directory which might host the project's source code. The idea is to
        pass `module.__version__` as the first argument and `module` as the
        hint. This way we can loookup where module came from, and look for
        version control system data in that directory. Technicallally passing
        hint will make us call
        :meth:`~versiontools.Version.from_tuple_and_hint()` instead of
        :meth:`~versiontools.Version.from_tuple()`.

    :type hint:
        either :obj:`None`, or a module.

    .. versionadded:: 1.1
    """
    if isinstance(version, Version):
        return str(version)
    elif isinstance(version, tuple) and len(version) == 5 and hint is not None:
        return str(Version.from_tuple_and_hint(version, hint))
    elif isinstance(version, tuple) and len(version) == 5:
        return str(Version.from_tuple(version))
    else:
        raise ValueError("version must be a tuple of five items")


if sys.version_info[:1] < (3,):
    isstring = lambda string: isinstance(string, basestring)
else:
    isstring = lambda string: isinstance(string, str)


def handle_version(dist, attr, value):
    """
    Handle version keyword as used by setuptools.

    .. note::
        This function is normally called by setuptools, it is advertised in the
        entry points of versiontools as setuptools extension. There is no need
        to call in manually.

    .. versionadded:: 1.3
    """
    from distutils.errors import DistutilsSetupError
    # We need to look at dist.metadata.version to actually see the version
    # that was passed to setup. Something in between does not seem to like our
    # version string and we get 0 here, odd.
    if value == 0:
        value = dist.metadata.version
    if not (isstring(value)
            and value.startswith(":versiontools:")):
        return
    # Peel away the magic tag
    value = value[len(":versiontools:"):]
    # Check if the syntax of the version is okay
    if ":" not in value:
        raise DistutilsSetupError(
            "version must be of the form `module_or_package:identifier`")
    # Parse the version string
    module_or_package, identifier = value.split(":", 1)
    # Use __version__ unless specified otherwise
    if identifier == "":
        identifier = "__version__"
    # Import the module or package indicated by the version tag
    try:
        obj = __import__(module_or_package, globals(), locals(), [''])
    except ImportError:
        message = get_exception_message(*sys.exc_info())
        raise DistutilsSetupError(
            "Unable to import %r%s" % (module_or_package, message))
    # Look up the version identifier.
    try:
        version = getattr(obj, identifier)
    except AttributeError:
        message = get_exception_message(*sys.exc_info())
        raise DistutilsSetupError(
            "Unable to access %r in %r%s" %
            (identifier, module_or_package, message))
    # Yay we have it! Let's format it correctly and overwrite the old value
    dist.metadata.version = format_version(version, obj)


def get_exception_message(exception, value, traceback):
    if value is not None:  # the exception value
        return ": %s" % value
    return ""
