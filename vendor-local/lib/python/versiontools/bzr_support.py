#!/usr/bin/env python
#
# Copyright (C) 2010 Linaro Limited
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
Bazaar support for versiontools
"""
import logging
import sys


class BzrIntegration(object):
    """
    Bazaar integration for versiontools
    """
    def __init__(self, branch):
        self._revno = branch.last_revision_info()[0]
        self._branch_nick = branch.nick

    @property
    def revno(self):
        """
        Revision number of the branch
        """
        return self._revno

    @property
    def branch_nick(self):
        """
        Nickname of the branch

        .. versionadded:: 1.0.4
        """
        return self._branch_nick

    @classmethod
    def from_source_tree(cls, source_tree):
        """
        Initialize :class:`~versiontools.bzr_support.BzrIntegration` by
        pointing at the source tree.  Any file or directory inside the
        source tree may be used.
        """
        branch = None
        try:
            import bzrlib
            if bzrlib.__version__ >= (2, 2, 1):
                # Python 2.4 the with keyword is not supported
                # and so you need to use the context manager manually, sigh.
                library_state = bzrlib.initialize()
                library_state.__enter__()
                try:
                    from bzrlib import branch
                    branch = branch.Branch.open_containing(source_tree)[0]
                finally:
                    library_state.__exit__(None, None, None)
            else:
                from bzrlib import branch
                branch = branch.Branch.open_containing(source_tree)[0]
        except Exception:
            from versiontools import get_exception_message
            message = get_exception_message(*sys.exc_info())
            logging.debug("Unable to get branch revision because "
                          "directory %r is not a bzr branch. Erorr: %s",
                          (source_tree, message))
        if branch:
            return cls(branch)
