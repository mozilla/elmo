# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Django field implementations used in mbdb.
'''
from __future__ import absolute_import

from django.db import models
from django.conf import settings
database_engine = settings.DATABASES['default']['ENGINE'].split('.')[-1]

try:
    import cPickle as pickle
    pickle  # silence pyflakes
except ImportError:
    import pickle


class PickledObject(str):
    """A subclass of string so it can be told whether a string is
       a pickled object or not (if the object is an instance of this class
       then it must [well, should] be a pickled one)."""
    pass


class PickledObjectField(models.Field):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        super(PickledObjectField, self).__init__(*args, **kwargs)
        # By default, South will make this field an index. MySQL doesn't
        # accept TEXT fields to be indexed, and will raise an error.
        # We thus need to force this to *not* be indexed by MySQL.
        self.db_index = False

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, PickledObject):
            # If the value is a definite pickle; and an error is raised in
            # de-pickling it should be allowed to propogate.
            return pickle.loads(str(value))
        else:
            try:
                return pickle.loads(str(value))
            except:
                # If an error was raised, just return the plain value
                return value

    def get_db_prep_save(self, value, connection):
        if value is not None and not isinstance(value, PickledObject):
            if isinstance(value, str):
                # normalize all strings to unicode, like django does
                value = unicode(value)
            value = PickledObject(pickle.dumps(value))
        return value

    def get_internal_type(self):
        return 'TextField'

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        if lookup_type in ['exact', 'isnull']:
            if lookup_type != 'isnull':
                value = self.get_db_prep_save(value, connection=connection)
        elif lookup_type == 'in':
            value = [self.get_db_prep_save(v, connection=connection)
                     for v in value]
        else:
            raise TypeError('Lookup type %s is not supported.' % lookup_type)
        return (super(PickledObjectField, self)
                .get_db_prep_lookup(lookup_type, value,
                                    connection=connection, prepared=True))


class ListField(models.Field):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        super(ListField, self).__init__(*args, **kwargs)
        # By default, South will make this field an index. MySQL doesn't
        # accept TEXT fields to be indexed, and will raise an error.
        # We thus need to force this to *not* be indexed by MySQL.
        self.db_index = False

    def to_python(self, value):
        if value is not None:
            if not value:
                return []
            if hasattr(value, 'split'):
                if database_engine != 'mysql':
                    value = value.decode('unicode-escape')
                return value.split('\0')
        return value

    def get_db_prep_save(self, value, connection):
        if value is not None:
            value = '\0'.join(value)
            if database_engine != 'mysql':
                value = value.encode('unicode-escape')
        return value

    def get_internal_type(self):
        return 'TextField'

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        if lookup_type in ['exact']:
            value = self.get_db_prep_save(value, connection=connection)
        elif lookup_type == 'isnull':
            pass
        elif lookup_type == 'in':
            value = [self.get_db_prep_save(v, connection=connection)
                     for v in value]
        else:
            raise TypeError('Lookup type %s is not supported.' % lookup_type)
        return super(ListField, self).get_db_prep_lookup(lookup_type, value,
                                                         connection=connection,
                                                         prepared=True)
