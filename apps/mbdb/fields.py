# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Django field implementations used in mbdb.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

import six.moves.cPickle as pickle
import six

from django.db import models
from django.conf import settings


database_engine = settings.DATABASES['default']['ENGINE'].split('.')[-1]


class PickledObject(str):
    """A subclass of string so it can be told whether a string is
       a pickled object or not (if the object is an instance of this class
       then it must [well, should] be a pickled one)."""
    pass


class PickledObjectField(models.Field):

    def __init__(self, *args, **kwargs):
        super(PickledObjectField, self).__init__(*args, **kwargs)
        # MySQL doesn't accept TEXT fields to be indexed,
        # and will raise an error.
        # We thus need to force this to *not* be indexed by MySQL.
        self.db_index = False

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        if isinstance(value, six.text_type):
            value = value.encode('ascii')
        return pickle.loads(value)

    def to_python(self, value):
        if value is None:
            return value
        try:
            if isinstance(value, six.text_type):
                b_value = value.encode('ascii')
            else:
                b_value = value
            return pickle.loads(b_value)
        except pickle.UnpicklingError:
            # If an error was raised, just return the plain value
            return value

    def get_prep_value(self, value):
        value = super(PickledObjectField, self).get_prep_value(value)
        if value is None:
            return value
        if isinstance(value, six.binary_type):
            # normalize all strings to bytes for pickle
            value = six.text_type(value)
        value = pickle.dumps(value, protocol=0)
        # convert to unicode, like django does
        return value.decode('ascii')

    def get_internal_type(self):
        return 'TextField'

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type not in ['exact', 'isnull']:
            raise TypeError('Lookup type %s is not supported.' % lookup_type)

        return (super(PickledObjectField, self)
                .get_prep_lookup(lookup_type, value))


class ListField(models.Field):

    def __init__(self, *args, **kwargs):
        super(ListField, self).__init__(*args, **kwargs)
        # MySQL doesn't accept TEXT fields to be indexed,
        # and will raise an error.
        # We thus need to force this to *not* be indexed by MySQL.
        self.db_index = False

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        if not value:
            return []
        if connection.vendor != 'mysql':
            value = value.decode('unicode-escape')
        return value.split('\0')

    def to_python(self, value):
        if value is None:
            return value
        if not value:
            return []
        if hasattr(value, 'split'):
            if database_engine != 'mysql':
                value = value.decode('unicode-escape')
            return value.split('\0')
        return value

    def get_prep_value(self, value):
        if value is not None:
            value = '\0'.join(value)
            if database_engine != 'mysql':
                value = value.encode('unicode-escape')
        return value

    def get_internal_type(self):
        return 'TextField'

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type not in ['exact', 'isnull', 'in']:
            raise TypeError('Lookup type %s is not supported.' % lookup_type)
        return super(ListField, self).get_prep_lookup(lookup_type, value)
