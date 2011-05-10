import ldap

from django.conf import settings
from django.contrib.auth.models import User, Group, check_password
from django.contrib.auth.backends import RemoteUserBackend
from django.core.validators import email_re
from django.utils.encoding import force_unicode, DjangoUnicodeDecodeError
import os

HERE = os.path.abspath(os.path.dirname(__file__))

assert settings.LDAP_HOST
assert settings.LDAP_DN
assert settings.LDAP_PASS

class MozLdapBackend(RemoteUserBackend):
    """Creates the connvection to the server, and binds anonymously"""
    host = ""
    dn = ""
    password = ""
    certfile = os.path.join(HERE, "cacert.pem")
    ldo = None

    def __init__(self):
        self.host = settings.LDAP_HOST
        self.dn = settings.LDAP_DN
        self.password = settings.LDAP_PASS
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
    def authenticate(self,username=None,password=None):
        try: # Let's see if we have such user
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

    def _authenticate_ldap(self, username, password, user=None):
        try:
            record = self.__getRecord(username)
        except ldap.SERVER_DOWN, e: # pragma: no cover
            print "** debug: LDAP server is down"
            return
        if not record:
            # wrong login
            return

        dn = record[0][0]
        #ldap.set_option(ldap.OPT_DEBUG_LEVEL,4095)
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, self.certfile)
        self.ldo = ldap.initialize(self.host)
        self.ldo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        try:
            self.ldo.simple_bind_s(dn, password)
        except ldap.INVALID_CREDENTIALS: # Bad password, credentials are bad.
            return
        except ldap.UNWILLING_TO_PERFORM: # Bad password, credentials are bad.
            return
        else:
            self.ldo.unbind_s()
            first_name =  record[0][1]['givenName'][0]
            last_name =  record[0][1]['sn'][0]
            email =  record[0][1]['mail'][0]
            first_name = force_unicode(first_name)
            last_name = force_unicode(last_name)
            if not user:
                user = User(username=username,
                            first_name=first_name,
                            last_name=last_name,
                            email=email)
                user.set_unusable_password()
                user.save()
                if self.__isLocalizer(username):
                    user.groups = (Group.objects.get(name='Localizers'),)
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
        return user

    def __getRecord(self, username):
        """Private method to find the distinguished name for a given username"""
        #ldap.set_option(ldap.OPT_DEBUG_LEVEL,4095)
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, self.certfile)
        self.ldo = ldap.initialize(self.host)
        self.ldo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        self.ldo.simple_bind_s(self.dn, self.password)
        result = self.ldo.search_s("dc=mozilla", ldap.SCOPE_SUBTREE, "mail="+username)
        self.ldo.unbind_s()
        return result

    def __isLocalizer(self, username):
        if self.localizers is None:
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, self.certfile)
            self.ldo = ldap.initialize(self.host)
            self.ldo.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            self.ldo.simple_bind_s(self.dn, self.password)
            result = self.ldo.search_s("ou=groups,dc=mozilla",
                                       ldap.SCOPE_SUBTREE,
                                       "cn=scm_l10n")
            self.localizers = result
            self.ldo.unbind_s()
        return username in self.localizers[0][1]['memberUid']
