# type: ignore
import os
import sys

req(
    "wish",
    "python",
    "pyside2",
    "requests",
)

env("LAUNCHER_NAME").setenv(this.name)
env("LAUNCHER_TAGS").setenv(this.tags)
src_path = os.path.join(this.root, "src")
env("LAUNCHER_INHERIT").setenv("python", "wish")
env("PYTHONPATH").insert(os.path.join(this.root, "src"))
env("LAUNCHER_COMMAND").setenv("wish " + (" ").join(sys.argv[1:]))
env("LAUNCHER_PKGROOT_NAME").setenv("WISH_PACKAGE_ROOT")
env("LAUNCHER_PKGMODE_NAME").setenv("WISH_PACKAGE_MODE")
env("LAUNCHER_API_URL_NAME").setenv("WISH_RESTAPI_URL")
env("LAUNCHER_PROJECT_ID_NAME").setenv("WISH_PROJECT_ID")
env("LAUNCHER_TASK_ID_NAME").setenv("WISH_TASK_ID")
env("LAUNCHER_SYS_SHELL_NAME").setenv("SHELL")
env("LAUNCHER_LANGUAGE").unset()
env("LAUNCHER_KEYPATH").unset()
alias("launcher", "python -m launcher")
