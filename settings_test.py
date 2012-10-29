# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This is imported by test-utils just before tests are run and your chance to
# assure certain settings are set for every test run.


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}

# this way, you don't need to have static files collected
COMPRESS_ENABLED = True
COMPRESS_OFFLINE = False

# ensure that ARECIBO is never used in tests
ARECIBO_SERVER_URL = None

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
