__package__ = 'archivebox.plugins_auth.ldap'

import sys

from typing import Dict, List, Optional
from pydantic import Field, model_validator, computed_field

from abx.archivebox.base_configset import BaseConfigSet

LDAP_LIB = None
try:
    import ldap
    from django_auth_ldap.config import LDAPSearch
    LDAP_LIB = ldap
except ImportError:
    pass

###################### Config ##########################


class LdapConfig(BaseConfigSet):
    """
    LDAP Config gets imported by core/settings.py very early during startup.
    It needs to be in a separate file from apps.py so that it can be imported
    during settings.py initialization before the apps are loaded.
    """

    LDAP_ENABLED: bool                  = Field(default=False, alias='LDAP')
    
    LDAP_SERVER_URI: str                = Field(default=None)
    LDAP_BIND_DN: str                   = Field(default=None)
    LDAP_BIND_PASSWORD: str             = Field(default=None)
    LDAP_USER_BASE: str                 = Field(default=None)
    LDAP_USER_FILTER: str               = Field(default=None)
    LDAP_CREATE_SUPERUSER: bool         = Field(default=False)

    LDAP_USERNAME_ATTR: str             = Field(default='username')
    LDAP_FIRSTNAME_ATTR: str            = Field(default='first_name')
    LDAP_LASTNAME_ATTR: str             = Field(default='last_name')
    LDAP_EMAIL_ATTR: str                = Field(default='email')
    
    @model_validator(mode='after')
    def validate_ldap_config(self):
        # Check that LDAP libraries are installed
        if self.LDAP_ENABLED and LDAP_LIB is None:
            sys.stderr.write('[X] Error: LDAP Authentication is enabled but LDAP libraries are not installed. You may need to run: pip install archivebox[ldap]\n')
            # dont hard exit here. in case the user is just running "archivebox version" or "archivebox help", we still want those to work despite broken ldap
            # sys.exit(1)
            self.update(LDAP_ENABLED=False)

        # Check that all required LDAP config options are set
        if self.LDAP_ENABLED and not self.LDAP_CONFIG_IS_SET:
            missing_config_options = [
                key for key, value in self.model_dump().items()
                if value is None and key != 'LDAP_ENABLED'
            ]
            sys.stderr.write('[X] Error: LDAP_* config options must all be set if LDAP_ENABLED=True\n')
            sys.stderr.write(f'    Missing: {", ".join(missing_config_options)}\n')
            self.update(LDAP_ENABLED=False)
        return self
    
    @computed_field
    @property
    def LDAP_CONFIG_IS_SET(self) -> bool:
        """Check that all required LDAP config options are set"""
        return bool(LDAP_LIB) and self.LDAP_ENABLED and bool(
            self.LDAP_SERVER_URI
            and self.LDAP_BIND_DN
            and self.LDAP_BIND_PASSWORD
            and self.LDAP_USER_BASE
            and self.LDAP_USER_FILTER
        )

    @computed_field
    @property
    def LDAP_USER_ATTR_MAP(self) -> Dict[str, str]:
        return {
            'username': self.LDAP_USERNAME_ATTR,
            'first_name': self.LDAP_FIRSTNAME_ATTR,
            'last_name': self.LDAP_LASTNAME_ATTR,
            'email': self.LDAP_EMAIL_ATTR,
        }

    @computed_field
    @property
    def AUTHENTICATION_BACKENDS(self) -> List[str]:
        return [
            'django.contrib.auth.backends.ModelBackend',
            'django_auth_ldap.backend.LDAPBackend',
        ]

    @computed_field
    @property
    def AUTH_LDAP_USER_SEARCH(self) -> Optional[object]:
        return self.LDAP_USER_FILTER and LDAPSearch(
            self.LDAP_USER_BASE,
            LDAP_LIB.SCOPE_SUBTREE,                                                                         # type: ignore
            '(&(' + self.LDAP_USERNAME_ATTR + '=%(user)s)' + self.LDAP_USER_FILTER + ')',
        )


LDAP_CONFIG = LdapConfig()
