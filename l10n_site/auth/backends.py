import ldap

from django.conf import settings
from django.contrib.auth.models import User, check_password
from django.contrib.auth.backends import RemoteUserBackend
import ldap_settings
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

    def authenticate(self,username=None,password=None):
        try: # Let's see if we have such user
            local_user = User.objects.get(username=username)
            if local_user.check_password(password):
                return local_user
        except User.DoesNotExist:
            try:
                record = self.__getRecord(username)
            except ldap.SERVER_DOWN, e:
                print "** debug: LDAP server is down"
                return
            if not record:
                print "** debug: LDAP did something funny"
                return
            dn = record[0][0]
            ldap.set_option(ldap.OPT_DEBUG_LEVEL,4095)
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
            else: # No exceptions: the connection succeeded and the user exists!
                first_name =  record[0][1]['givenName'][0]
                last_name =  record[0][1]['sn'][0]
                email =  record[0][1]['mail'][0]
                user = User(username=username,first_name=first_name,last_name=last_name,email=email)
                user.is_staff = False
                user.is_superuser = False
                user.set_password(password)
                user.save()
            self.ldo.unbind_s()
            return user
        return # if we did not return anything yet, we're probably not authenticated

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
