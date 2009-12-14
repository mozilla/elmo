import ldap

from django.conf import settings
from django.contrib.auth.models import User, Group, check_password
from django.contrib.auth.backends import RemoteUserBackend
from django.forms.fields import email_re
import l10n_site.ldap_settings as ldap_settings
import os

class MozLdapBackend(RemoteUserBackend):
    """Creates the connvection to the server, and binds anonymously"""
    host = ""
    dn = ""
    password = ""
    certfile = "./auth/cacert.pem"
    ldo = None

    def __init__(self):
        self.host = ldap_settings.LDAP_HOST
        self.dn = ldap_settings.LDAP_DN
        self.password = ldap_settings.LDAP_PASS

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
            if email_re.search(username):
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
        return # if we did not return anything yet, we're probably not authenticated

    def _authenticate_ldap(self, username, password, user=None):
        try:
            record = self.__getRecord(username)
        except ldap.SERVER_DOWN, e:
            print "** debug: LDAP server is down"
            return
        if not record:
            print "** debug: LDAP did something funny"
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
            first_name =  record[0][1]['givenName'][0]
            last_name =  record[0][1]['sn'][0]
            email =  record[0][1]['mail'][0]
            if not user:
                user = User(username=username,
                            first_name=first_name,
                            last_name=last_name,
                            email=email)
                user.set_unusable_password()
                user.save()
                if 'localizers' in record[0][1]['groups']:
                    user.groups = (Group.objects.get(name='Localizers'),)
            else:
                changed = False
                if user.first_name != first_name:
                    user.first_name = first_name
                    changed = True
                if user.last_name != last_name:
                    user.las_tname = last_name
                    changed = True
                if user.email != email:
                    user.email = email
                    changed = True
                if changed:
                    user.save()
        self.ldo.unbind_s()
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
        if self.__isLocalizer(username):
            result[0][1]['groups'] = ('localizers',)
        else:
            result[0][1]['groups'] = ()
        self.ldo.unbind_s()
        return result

    def __isLocalizer(self, username):
        result = self.ldo.search_s("ou=groups,dc=mozilla", ldap.SCOPE_SUBTREE, "cn=hg_l10n")
        return username in result[0][1]['memberUid']
