import os
from ldap3 import Server, Connection, ALL, NTLM


class LDAPAuthenticator:
    def __init__(self, ldap_server, domain=None):
        self.ldap_server = ldap_server
        self.domain = domain
        self.mail = None
        self.fullName = None

    def authenticate(self, username, password):
        try:
            server = Server(self.ldap_server, get_info=ALL)
            user_dn = f"{self.domain}\\{username}"
            connection = Connection(server, user=user_dn, password=password, authentication=NTLM)
            if connection.bind():
                entry = None
                try:
                    connection.search(
                        search_base="DC=dy3danimation,DC=com",
                        search_filter=f"(sAMAccountName={username})",
                        attributes=["displayName", "userPrincipalName"],
                    )
                    entry = connection.entries[0]
                    self.fullName = entry.displayName.value
                    self.mail = entry.userPrincipalName.value
                except Exception as e:
                    print(f"LDAP search error: {str(e)}", flush=True)
                connection.unbind()
                return True
            else:
                connection.unbind()
                return False
        except Exception as e:
            print(f"LDAP authentication error: {str(e)}", flush=True)
            return False


def ldap_login(username, password):
    print("Attempting LDAP authentication...", flush=True)
    ldap_server = os.environ.get("LAUNCHER_LDAP_SERVER")
    domain = os.environ.get("LAUNCHER_LDAP_DOMAIN")
    if not ldap_server or not domain:
        print("LDAP server or domain not configured.", flush=True)
        return
    ldap_authenticator = LDAPAuthenticator(ldap_server=ldap_server, domain=domain)
    if ldap_authenticator.authenticate(username, password):
        return ldap_authenticator
