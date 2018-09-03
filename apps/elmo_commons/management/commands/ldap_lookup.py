# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Tool for doing local LDAP lookups
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils.encoding import force_text
from django.core.management.base import BaseCommand
from lib.auth.backends import (
    MozLdapBackend,
    GROUP_MAPPINGS,
    flatten_group_names
)
import ldap
import six

LDAP_IGNORE_ATTRIBUTES = (
    'uidNumber',
    'rid',
    'fakeHome',
    'svnShell',
    'loginShell',
    'hgShell',
    'gidNumber',
    'homeDirectory'
)


class Command(BaseCommand):
    help = 'Look up users in LDAP'

    def add_arguments(self, parser):
        parser.add_argument('mailaddress')

    def handle(self, **options):
        mail = options['mailaddress']

        def show(key, value):
            if (
                    isinstance(value, list) and value
            ):
                value = ', '.join(force_text(v) for v in value)
            self.stdout.write(key.ljust(20) + " " + force_text(value))

        self.stdout.write("\nLOCAL USER ".ljust(79, '-'))
        try:
            user = User.objects.get(email=mail)
            show("Username", user.username)
            show("Email", user.email)
            show("First name", user.first_name)
            show("Last name", user.last_name)
            show("Active", user.is_active)
            show("Superuser", user.is_superuser)
            show("Staff", user.is_staff)
            self.stdout.write("Groups:".ljust(20), ending='')
            if user.groups.all():
                self.stdout.write(
                    ', '.join([x.name for x in user.groups.all()])
                )
            else:
                self.stdout.write("none")

        except User.DoesNotExist:
            self.stdout.write("Does NOT exist locally")

        backend = MozLdapBackend()
        backend.connect()
        try:
            search_filter = backend.make_search_filter(dict(mail=mail))

            results = backend.ldo.search_s(
                    "dc=mozilla",
                    ldap.SCOPE_SUBTREE,
                    search_filter,
                )

            self.stdout.write("\nIN LDAP ".ljust(79, '-'))
            uid = None
            for uid, data in results:
                for key, value in six.iteritems(data):
                    if key in LDAP_IGNORE_ATTRIBUTES:
                        continue
                    show(key, value)

            if uid:
                group_names = flatten_group_names(GROUP_MAPPINGS.values())
                search_filter1 = backend.make_search_filter(
                    dict(cn=group_names),
                    any_parameter=True
                )
                search_filter2 = backend.make_search_filter({
                    'memberUID': [uid, mail],
                    'member': ['mail=%s,o=com,dc=mozilla' % mail,
                               'mail=%s,o=org,dc=mozilla' % mail,
                               'mail=%s,o=net,dc=mozilla' % mail],
                }, any_parameter=True)
                # combine the group part with the mail part
                search_filter = '(&%s%s)' % (search_filter1, search_filter2)

                group_results = backend.ldo.search_s(
                    "ou=groups,dc=mozilla",
                    ldap.SCOPE_SUBTREE,
                    search_filter,
                    ['cn']
                )
                self.stdout.write("\nLDAP GROUPS ".ljust(79, '-'))
                _group_mappings_reverse = {}
                for django_name, ldap_names in GROUP_MAPPINGS.items():
                    ldap_names = flatten_group_names(ldap_names)
                    for name in ldap_names:
                        _group_mappings_reverse[name] = django_name

                groups = [force_text(x[1]['cn'][0]) for x in group_results]
                for group in groups:
                    self.stdout.write(
                        group.ljust(16) + ' -> ' +
                        _group_mappings_reverse.get(
                            group,
                            '*not a Django group*'
                        )
                    )

        finally:
            backend.disconnect()
