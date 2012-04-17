# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''Django field implementations used in mbdb.
'''

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
