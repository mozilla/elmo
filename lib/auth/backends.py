# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import ldap
from ldap.filter import filter_format

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.auth.backends import RemoteUserBackend
from django.core.validators import email_re
from django.utils.hashcompat import md5_constructor
from django.utils.encoding import force_unicode
import os

HERE = os.path.abspath(os.path.dirname(__file__))

# List all ldap errors that are our fault (not the client's)
AUTHENTICATION_SERVER_ERRORS = (ldap.SERVER_DOWN,)

GROUP_MAPPINGS = {
    # Django name:  LDAP name,
    'Localizers': 'scm_l10n',
    'build': 'buildteam',
}


class MozLdapBackend(RemoteUserBackend):
    """Creates the connvection to the server, and binds anonymously"""
    host = ""
    dn = ""
    password = ""
    certfile = os.path.join(HERE, "cacert.pem")
    ldo = None

    def __init__(self):
        # Note, any exceptions that happen here will be swallowed by Django's
        # core handler for middleware classes. Ugly truth :)
        self.host = settings.LDAP_HOST
        self.dn = settings.LDAP_DN
        self.password = settings.LDAP_PASSWORD
        self.localizers = None

    #
    # This is the path we take here:
    # *) Try to find the user locally
    # *) If the user exists, authenticate him locally
    # *) If authentication is granted return his object
    # *) If not, try to authenticate against LDAP
    # *) If authentication is granted create/update his local account and
    #    return the *local* one
    #
    # Important note:
    #  We don't store LDAP password locally, so LDAP accounts will
    #  never be authenticated locally
    def authenticate(self, username=None, password=None):
        try:  # Let's see if we have such user
            if email_re.match(username):
                local_user = User.objects.get(email=username)
            else:
                local_user = User.objects.get(username=username)

            if local_user.has_usable_password():
                if local_user.check_password(password):
                    return local_user
                else:
                    return
            else:
                return self._authenticate_ldap(username, password, local_user)
        except User.DoesNotExist:
            return self._authenticate_ldap(username, password)

    @staticmethod
    def make_search_filter(data, any_parameter=False):
        params = []
        for key, value in data.items():
            if not isinstance(value, (list, tuple)):
                value = [value]
            for v in value:
                params.append(filter_format('(%s=%s)', (key, v)))
        search_filter = ''.join(params)
        if len(params) > 1:
            if any_parameter:
                search_filter = '(|%s)' % search_filter
            else:
                search_filter = '(&%s)' % search_filter
        return search_filter

    def _authenticate_ldap(self, mail, password, user=None):
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, self.certfile)
        self.ldo = ldap.initialize(self.host)
        self.ldo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

        # first, figure out the uid
        search_filter = self.make_search_filter(dict(mail=mail))

        # open a connection using the bind user
        self.ldo.simple_bind_s(self.dn, self.password)
        try:
            # get the uid (first and foremost) but also pick up the other
            # essential attributes which we'll need later on.
            results = self.ldo.search_s(
                "dc=mozilla",
                ldap.SCOPE_SUBTREE,
                search_filter,
                ['uid', 'givenName', 'sn', 'mail']
            )
            if not results:
                # that means there is no user with this email address
                return

            uid, result = results[0]

            # search by groups
            group_names = GROUP_MAPPINGS.values()
            search_filter1 = self.make_search_filter(
                dict(cn=group_names),
                any_parameter=True
            )

            # When searching by group you need to be more delicate with how you
            # search.
            # This pattern :jabba helped me find.
            search_filter2 = self.make_search_filter({
                'memberUID': [uid, mail],
                'member': ['mail=%s,o=com,dc=mozilla' % mail,
                           'mail=%s,o=org,dc=mozilla' % mail,
                           'mail=%s,o=net,dc=mozillacom' % mail],
            }, any_parameter=True)
            # combine the group part with the mail part
            search_filter = '(&%s%s)' % (search_filter1, search_filter2)

            group_results = self.ldo.search_s(
                "ou=groups,dc=mozilla",
                ldap.SCOPE_SUBTREE,
                search_filter,
                ['cn']
            )
            groups = []
            for __, each in group_results:
                for names in each.values():
                    groups.extend(names)
        finally:
            self.ldo.unbind_s()

        # Now we know everything we need to know about the user but lastly we
        # need to check if their password is correct
        self.ldo = ldap.initialize(self.host)
        self.ldo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        try:
            self.ldo.simple_bind_s(uid, password)
        except ldap.INVALID_CREDENTIALS:  # Bad password, credentials are bad.
            return
        except ldap.UNWILLING_TO_PERFORM:  # Bad password, credentials are bad.
            return

        first_name = result['givenName'][0]
        last_name = result['sn'][0]
        email = result['mail'][0]
        first_name = force_unicode(first_name)
        last_name = force_unicode(last_name)

        # final wrapper that returns the user
        return self._update_local_user(
            user,
            mail,
            first_name,
            last_name,
            email,
            in_groups=groups
        )

    def _update_local_user(self, user, username, first_name, last_name, email,
                           in_groups=None):
        if in_groups is None:
            in_groups = []
        # Because the username field on model User is capped to 30
        # characters we need to assign a butchered username here.
        # It's not a problem because the user can be found by email
        # anyway.
        # 30 is the default max length of the username field for
        # django.contrib.auth.models.User
        if not user:
            django_username = username
            if email_re.match(django_username):
                if isinstance(username, unicode):
                    # md5 chokes on non-ascii characters
                    django_username = username.encode('ascii', 'ignore')
                django_username = (md5_constructor(django_username)
                                   .hexdigest()[:30])
            user = User(username=django_username,
                        first_name=first_name,
                        last_name=last_name,
                        email=email)
            user.set_unusable_password()
            user.save()
        else:
            changed = False
            if user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if user.last_name != last_name:
                user.last_name = last_name
                changed = True
            if user.email != email:
                user.email = email
                changed = True
            if changed:
                user.save()

        for django_name, ldap_name in GROUP_MAPPINGS.items():
            if ldap_name in in_groups:
                # make sure the user is in this django group
                if not user.groups.filter(name=django_name).exists():
                    user.groups.add(Group.objects.get(name=django_name))
            else:
                user.groups.remove(Group.objects.get(name=django_name))

        return user
