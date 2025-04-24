import os
import urllib.parse
from functools import wraps
from typing import List, Dict, Any, Optional
from .client import APIClient
from .client import APIError


def authenticate(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.is_authenticated:
            return func(self, *args, **kwargs)
        else:
            raise APIError("User not authenticated")

    return wrapper


class AuthService:
    def __init__(self):
        api_env_name = os.environ.get("LAUNCHER_API_URL_NAME")
        wish_graphs_url = os.environ.get(api_env_name)
        parse = urllib.parse.urlparse(wish_graphs_url)
        wish_net_url = "{}://{}".format(parse.scheme, parse.netloc)
        self.api_client = APIClient(wish_net_url)
        self._token = None
        self._user = None
        self._role = None
        self._is_authenticated = False

    @property
    def is_authenticated(self):
        return self._is_authenticated

    @property
    def user(self):
        return self._user

    @property
    def role(self):
        return self._role

    def login(self, username: str, password: str) -> bool:
        try:
            response = self.api_client.login(username, password)
            if response and "token" in response:
                self._token = response["token"]
                self._user = username
                self._role = response.get("role", "member")
                self._is_authenticated = True
                self.api_client.token = self._token
                return True
            return False
        except Exception as e:
            print(f"Login error: {e}")
            return False

    def logout(self):
        self._token = None
        self._user = None
        self._role = None
        self._is_authenticated = False


class MainModel(object):
    class UserRole:
        ADMIN = "admin"
        MANAGER = "manager"
        MEMBER = "member"

    ROLE_MAP = {
        "成员": "member",
        "经理": "manager",
        "管理": "admin",
        "Member": "member",
        "Manager": "manager",
        "Admin": "admin",
    }

    def __init__(self):
        self.auth_service = AuthService()

    @property
    def is_authenticated(self):
        return self.auth_service.is_authenticated

    @property
    def user(self):
        return self.auth_service.user

    @property
    def user_role(self):
        return self.auth_service.role

    def auth_user(self, username: str, password: str) -> bool:
        try:
            response = self.auth_service.api_client.login(
                username=username, password=password
            )
            if response and "token" in response:
                self.auth_service._token = response["token"]
                self.auth_service._user = username
                self.auth_service._role = response.get("role", "member")
                self.auth_service._is_authenticated = True
                return True
            return False
        except Exception as e:
            return None

    @authenticate
    def get_all_users(self) -> List[Dict[str, Any]]:
        try:
            return self.auth_service.api_client.get_users()
        except Exception as e:
            print(f"Failed to get user list: {e}")
            return []

    @authenticate
    def get_all_proj(self):
        try:
            projects = self.auth_service.api_client.get_projects()
            if not projects:
                return []
            return projects
        except Exception as e:
            print(f"Failed to get project list: {e}")
            return []

    @authenticate
    def get_all_task(self, project_id):
        try:
            tasks = self.auth_service.api_client.get_project_tasks(project_id)
            if not tasks:
                return []

            task_dict = {}
            for task in tasks:
                task_dict[task["id"]] = {
                    "id": task["id"],
                    "title": task["title"],
                    "parent_id": task.get("parent_id"),
                    "children": [],
                }

            root_tasks = []
            for task_id, task in task_dict.items():
                if not task["parent_id"]:
                    root_tasks.append(task)
                else:
                    parent = task_dict.get(task["parent_id"])
                    if parent:
                        parent["children"].append(task)

            root_tasks.sort(key=lambda x: x["id"])

            def sort_children(task):
                task["children"].sort(key=lambda x: x["id"])
                for child in task["children"]:
                    sort_children(child)

            for task in root_tasks:
                sort_children(task)

            return root_tasks
        except Exception as e:
            print(f"Failed to get task list: {e}")
            return []

    @authenticate
    def add_project(self, project_name: str) -> Dict[str, Any]:
        try:
            return self.auth_service.api_client.create_project(name=project_name)
        except Exception as e:
            print(f"Failed to add project: {e}")
            return None

    @authenticate
    def delete_project(self, project_id: int) -> bool:
        try:
            response = self.auth_service.api_client.delete_project(project_id)
            if not response or not response.get("success"):
                print(
                    f"Failed to delete project: {response.get('message', 'Unknown error')}"
                )
                return False
            return True
        except Exception as e:
            print(f"Failed to delete project: {e}")
            return False

    @authenticate
    def add_task(
        self, title: str, project_id: int = None, parent_id: int = None
    ) -> Dict[str, Any]:
        try:
            response = self.auth_service.api_client.create_task(
                title=title,
                project_id=project_id,
                description="",
                priority=1,
                parent_id=parent_id,
            )
            return response
        except Exception as e:
            print(f"Failed to add task: {e}")
            return {}

    @authenticate
    def delete_task(self, project_id: int, task_id: int) -> bool:
        try:
            response = self.auth_service.api_client.delete_task(project_id, task_id)
            if not response or not response.get("success"):
                print(
                    f"Failed to delete task: {response.get('message', 'Unknown error')}"
                )
                return False
            return True
        except Exception as e:
            print(f"Failed to delete task: {e}")
            return False

    @authenticate
    def get_project_users(self, project_id: int) -> List[Dict[str, Any]]:
        try:
            return self.auth_service.api_client.get_project_members(project_id)
        except Exception as e:
            print(f"Failed to get project users: {e}")
            return []

    @authenticate
    def assign_project(self, project_id: int, user_ids: List[int]) -> bool:
        try:
            response = self.auth_service.api_client.update_project_members(
                project_id, user_ids
            )
            if not response or not response.get("success"):
                print(
                    f"Failed to update project members: {response.get('message', 'Unknown error')}"
                )
                return False
            return True
        except Exception as e:
            print(f"Failed to update project members: {e}")
            return False

    @authenticate
    def assign_task(self, project_id: int, task_id: int, user_ids: List[int]) -> bool:
        try:
            response = self.auth_service.api_client.update_task_members(
                project_id, task_id, user_ids
            )
            if not response or not response.get("success"):
                print(
                    f"Failed to update task members: {response.get('message', 'Unknown error')}"
                )
                return False
            return True
        except Exception as e:
            print(f"Failed to update task members: {e}")
            return False

    @authenticate
    def add_user(
        self, username: str, password: str, email: str, role: str = "member"
    ) -> bool:
        try:
            if self.user_role != self.UserRole.ADMIN:
                return False
            response = self.auth_service.api_client.create_user(
                username=username, password=password, email=email, role=role
            )
            return bool(response and "id" in response)
        except Exception as e:
            print(f"Failed to add user: {e}")
            return False

    @authenticate
    def delete_user(self, user_id: int) -> bool:
        try:
            if self.user_role != self.UserRole.ADMIN:
                return False
            response = self.auth_service.api_client.delete_user(user_id)
            if not response or not response.get("success"):
                print(
                    f"Failed to delete user: {response.get('message', 'Unknown error')}"
                )
                return False
            return True
        except Exception as e:
            print(f"Failed to delete user: {e}")
            return False

    def update_user(
        self,
        user_id: int,
        username: str = None,
        password: str = None,
        email: str = None,
        role: str = None,
    ) -> bool:
        try:
            response = self.auth_service.api_client.update_user(
                user_id, username=username, password=password, email=email, role=role
            )
            return bool(response and "id" in response)
        except Exception as e:
            print(f"Failed to update user: {e}")
            return False

    @authenticate
    def update_user_role(self, user_id: int, new_role: str) -> bool:
        try:
            if self.user_role != self.UserRole.ADMIN:
                return False
            response = self.auth_service.api_client.update_user(
                user_id=user_id, role=new_role
            )
            return bool(response and "id" in response)
        except Exception as e:
            print(f"Failed to update user role: {e}")
            return False

    @authenticate
    def get_project_members(self, project_id: int) -> List[Dict[str, Any]]:
        try:
            response = self.auth_service.api_client.get_project_members(project_id)
            if not response:
                return []
            return response
        except Exception as e:
            print(f"Failed to get project members: {e}")
            return []

    @authenticate
    def get_task_members(self, project_id: int, task_id: int) -> List[Dict[str, Any]]:
        try:
            response = self.auth_service.api_client.get_task_members(
                project_id, task_id
            )
            if not response:
                return []
            return response
        except Exception as e:
            print(f"Failed to get task members: {e}")
            return []

    @authenticate
    def get_launchers(
        self, project_id: int, task_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            return self.auth_service.api_client.get_launchers(project_id, task_id)
        except Exception as e:
            print(f"Failed to get launcher configuration: {e}")
            return {}

    @authenticate
    def add_launcher(
        self, project_id: int, task_id: Optional[int], name: str, vdata: dict
    ) -> Dict[str, Any]:
        try:
            return self.auth_service.api_client.create_launcher(
                project_id=project_id,
                task_id=task_id,
                name=name,
                vdata=vdata,
            )
        except Exception as e:
            print(f"Failed to add launcher: {e}")
            return {}

    @authenticate
    def update_launcher(
        self,
        launcher_id: int,
        project_id: int,
        task_id: Optional[int],
        name: str,
        vdata: dict,
    ) -> Dict[str, Any]:
        try:
            return self.auth_service.api_client.update_launcher(
                launcher_id=launcher_id,
                project_id=project_id,
                task_id=task_id,
                name=name,
                vdata=vdata,
            )
        except Exception as e:
            print(f"Failed to update launcher: {e}")
            return {}

    @authenticate
    def delete_launcher(
        self, launcher_id: int, project_id: int, task_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            return self.auth_service.api_client.delete_launcher(
                launcher_id=launcher_id, project_id=project_id, task_id=task_id
            )
        except Exception as e:
            print(f"Failed to delete launcher: {e}")
            return {"success": False}

    @authenticate
    def toggle_launcher(
        self, launcher_id: int, project_id: int, task_id: Optional[int], action: str
    ) -> Dict[str, Any]:
        try:
            return self.auth_service.api_client.toggle_launcher(
                launcher_id=launcher_id,
                project_id=project_id,
                task_id=task_id,
                action=action,
            )
        except Exception as e:
            print(
                f"Failed to {'enable' if action == 'enable' else 'disable'} launcher: {e}"
            )
            return {"success": False}
