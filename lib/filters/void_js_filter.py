# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This callback is created so that we don't actually do anything with the
Javascript files are they are passed around by django_compressor.

Once we're confident that django_compressor works we can disable this
filter and start using a real compressor package.

To use this filter set this in your settings:

    COMPRESS_JS_FILTERS = (
      'lib.filters.void_js_filter.VoidJSFilter',
    )

"""

from compressor.filters import CallbackOutputFilter


class VoidJSFilter(CallbackOutputFilter):
    callback = "lib.filters.void_js_filter.jsvoid"


def jsvoid(content):
    return content
