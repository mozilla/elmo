# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This is imported by our test runner just before tests are run and your chance
# to assure certain settings are set for every test run.


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}

# disable loading homepage feeds over the wire for tests
L10N_FEED_URL = '''<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>
'''

# this way, you don't need to have static files collected
COMPRESS_ENABLED = True
COMPRESS_OFFLINE = False

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

# don't accidentally do anything whilst running tests
RAVEN_CONFIG = {}
SENTRY_DSN = None
