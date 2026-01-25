# type: ignore
import os
import sys

req(
    "wish",
    "python",
    "pyside2",
    "requests",
)

req(
    "ldap3",
    "pycryptodome",
)

env("LAUNCHER_NAME").setenv(this.name)
env("LAUNCHER_TAGS").setenv(this.tags)
env("LAUNCHER_TEMP").setenv(os.path.join(os.path.dirname(this.root), ".tmp"))
env("LAUNCHER_COMMAND").setenv("wish " + (" ").join(sys.argv[1:]))
env("LAUNCHER_PKGROOT_NAME").setenv("WISH_PACKAGE_ROOT")
env("LAUNCHER_OFFLINE_NAME").setenv("WISH_OFFLINE_MODE")
env("LAUNCHER_DEVELOP_NAME").setenv("WISH_DEVELOP_MODE")
env("LAUNCHER_API_URL_NAME").setenv("WISH_RESTAPI_URL")
env("LAUNCHER_SYS_SHELL_NAME").setenv("SHELL")
#env("LAUNCHER_LDAP_SERVER").setenv("ldap://192.168.1.227")
#env("LAUNCHER_LDAP_DOMAIN").setenv("DY3DANIMATION")
env("PYTHONPATH").insert(os.path.join(this.root, "src"))
alias("launcher", "python -m launcher")