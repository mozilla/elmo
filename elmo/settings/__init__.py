# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import os

from .base import *  # noqa
try:
    from .local import *  # noqa
except ImportError:
    pass

# overload configuration from environment, as far as we have it
try:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ['ELMO_DB_NAME'],
            'USER': os.environ['ELMO_DB_USER'],
            'PASSWORD': os.environ['ELMO_DB_PASSWORD'],
            'HOST': os.environ['ELMO_DB_HOST'],
            'PORT': '',
            'CONN_MAX_AGE': 500,
            'OPTIONS': {
                'charset': 'utf8',
                'use_unicode': True,
            },
            'TEST': {
                'CHARSET': "utf8",
                'COLLATION': 'utf8_general_ci',
            },
        },
    }
except KeyError:
    pass
for local_var, env_var in (
            ('ES_COMPARE_HOST', 'ES_COMPARE_HOST'),
            ('ES_COMPARE_INDEX', 'ES_COMPARE_INDEX'),
            ('LDAP_HOST', 'ELMO_LDAP_HOST'),
            ('LDAP_DN', 'ELMO_DN'),
            ('LDAP_PASSWORD', 'ELMO_LDAP_PASSWORD'),
            ('REPOSITORY_BASE', 'ELMO_REPOSITORY_BASE'),
            ('SECRET_KEY', 'ELMO_SECRET_KEY'),
):
    if env_var in os.environ:
        globals()[local_var] = os.environ[env_var]

if 'ELMO_BUILD_BASE' in os.environ:
    _log_base = os.environ['ELMO_BUILD_BASE']
    LOG_MOUNTS = {
      'l10n-master': _log_base + 'l10n-master',
      'test-master': _log_base + 'test-master',
    }

if 'ELMO_SENTRY_DSN' in os.environ:
    RAVEN_CONFIG = {
        'dsn': os.environ['ELMO_SENTRY_DSN']
    }

if 'ELMO_INCLUDE_ANALYTICS' in os.environ:
    INCLUDE_ANALYTICS = True

# check ldap config
if all('LDAP_{}'.format(s) in globals() for s in ('HOST', 'DN', 'PASSWORD')):
    import ldap
    AUTHENTICATION_BACKENDS = ('lib.auth.backends.MozLdapBackend',)
else:
    import warnings
    warnings.warn("No LDAP authentication")

# generic django settings, good for DEBUG etc
boolmapper = {
    'true': True,
    '1': True,
    'false': False,
    '0': False,
}
for key, value in os.environ.items():
    if not key.startswith('DJANGO_'):
        continue
    globals()[key[len('DJANGO_'):]] = boolmapper.get(value.lower(), value)

__all__ = [
    setting for setting in globals().keys() if setting.isupper()
]