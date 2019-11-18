# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Hacking around the commonware middlewares like everybody else does.

from django.utils.deprecation import MiddlewareMixin
import commonware.middleware


class FrameOptionsHeader(
    commonware.middleware.FrameOptionsHeader, MiddlewareMixin
):
    pass


class ScrubRequestOnException(
    commonware.middleware.ScrubRequestOnException, MiddlewareMixin
):
    pass
