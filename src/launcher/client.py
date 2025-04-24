import os
import requests
from requests.adapters import HTTPAdapter
from typing import Optional, Dict, List, Any
from datetime import datetime


class APIError(Exception):
    def __init__(self, message: str, status_code: int = None, error_code: int = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=3, pool_maxsize=300, max_retries=3)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self._token = None

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        if value:
            self.session.headers.update({"Authorization": f"Bearer {value}"})
        else:
            self.session.headers.pop("Authorization", None)

    def login(self, username: str, password: str) -> Dict[str, Any]:
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password},
                timeout=5,
            )
            result = self._handle_response(response)
            if result and "token" in result:
                self.token = result["token"]
            return result
        except requests.Timeout:
            raise
        except requests.ConnectionError:
            raise
        except Exception:
            raise

    def _handle_response(self, response: requests.Response, raw: bool = False) -> Any:
        if response.status_code == 401:
            raise APIError("Authentication failed")
        elif response.status_code == 403:
            raise APIError("Permission denied")
        elif response.status_code >= 400:
            if not raw:
                data = response.json()
                raise APIError(
                    data.get("error", "Unknown error"),
                    status_code=response.status_code,
                    error_code=data.get("error_code"),
                )
            raise APIError("Failed to get resource", status_code=response.status_code)

        return response.content if raw else response.json()

    def create_user(
        self, username: str, password: str, email: str, role: str = "member"
    ) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/users",
            json={
                "username": username,
                "password": password,
                "email": email,
                "role": role,
            },
        )
        return self._handle_response(response)

    def get_users(self) -> List[Dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/users")
        return self._handle_response(response)

    def delete_user(self, user_id: int) -> Dict[str, Any]:
        try:
            response = self.session.delete(f"{self.base_url}/users/{user_id}")
            return self._handle_response(response)
        except Exception as e:
            raise

    def update_user(self, user_id: int, **kwargs) -> Dict[str, Any]:
        response = self.session.put(
            f"{self.base_url}/users/{user_id}",
            json={k: v for k, v in kwargs.items() if v is not None},
        )
        return self._handle_response(response)

    def create_project(self, name: str) -> Dict[str, Any]:
        response = self.session.post(f"{self.base_url}/projects", json={"name": name})
        return self._handle_response(response)

    def delete_project(self, project_id: int) -> Dict[str, Any]:
        response = self.session.delete(f"{self.base_url}/projects/{project_id}")
        return self._handle_response(response)

    def get_projects(self) -> List[Dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/projects")
        return self._handle_response(response)

    def get_project(self, project_id: int) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/projects/{project_id}")
        return self._handle_response(response)

    def update_project(
        self, project_id: int, name: str = None, description: str = None
    ) -> Dict[str, Any]:
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description

        response = self.session.put(
            f"{self.base_url}/projects/{project_id}", json=payload
        )
        return self._handle_response(response)

    def get_project_tasks(self, project_id: int) -> List[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/projects/{project_id}/tasks")
            return self._handle_response(response)
        except Exception as e:
            print(f"Failed to get project tasks: {e}")
            raise

    def get_project_members(self, project_id: int) -> List[Dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/projects/{project_id}/members")
        return self._handle_response(response)

    def create_task(
        self,
        project_id: int,
        title: str,
        description: Optional[str] = None,
        priority: int = 1,
        due_date: Optional[datetime] = None,
        parent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload = {
            "title": title,
            "description": description,
            "priority": priority,
            "due_date": due_date.isoformat() if due_date else None,
            "parent_id": parent_id,
        }
        response = self.session.post(
            f"{self.base_url}/projects/{project_id}/tasks", json=payload
        )
        return self._handle_response(response)

    def get_tasks(self) -> List[Dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/tasks")
        return self._handle_response(response)

    def delete_task(self, project_id: int, task_id: int) -> Dict[str, Any]:
        response = self.session.delete(
            f"{self.base_url}/projects/{project_id}/tasks/{task_id}"
        )
        return self._handle_response(response)

    def get_task(self, task_id: int) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/tasks/{task_id}")
        return self._handle_response(response)

    def update_task(
        self,
        project_id: int,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        status: Optional[str] = None,
        due_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        payload = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if priority is not None:
            payload["priority"] = priority
        if status is not None:
            payload["status"] = status
        if due_date is not None:
            payload["due_date"] = due_date.isoformat()

        response = self.session.put(
            f"{self.base_url}/projects/{project_id}/tasks/{task_id}", json=payload
        )
        return self._handle_response(response)

    def create_subtask(
        self, parent_id: int, title: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {"title": title, "description": description}
        response = self.session.post(
            f"{self.base_url}/tasks/{parent_id}/subtasks", json=payload
        )
        return self._handle_response(response)

    def get_task_subtasks(self, task_id: int) -> List[Dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/tasks/{task_id}/subtasks")
        return self._handle_response(response)

    def get_my_projects(self) -> List[Dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/users/me/projects")
        return self._handle_response(response)

    def get_my_tasks(self) -> List[Dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/users/me/tasks")
        return self._handle_response(response)

    def update_user_role(self, user_id: int, role: str) -> Dict[str, Any]:
        response = self.session.put(
            f"{self.base_url}/users/{user_id}/role", json={"role": role}
        )
        return self._handle_response(response)

    def add_project_member(
        self, project_id: int, user_id: int, role: str = "member"
    ) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/projects/{project_id}/members",
            json={"user_id": user_id, "role": role},
        )
        return self._handle_response(response)

    def remove_project_member(self, project_id: int, user_id: int) -> Dict[str, Any]:
        response = self.session.delete(
            f"{self.base_url}/projects/{project_id}/members/{user_id}"
        )
        return self._handle_response(response)

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> Dict[str, Any]:
        response = self.session.put(
            f"{self.base_url}/users/{user_id}/password",
            json={"old_password": old_password, "new_password": new_password},
        )
        return self._handle_response(response)

    def get_task_members(self, project_id: int, task_id: int) -> List[Dict[str, Any]]:
        response = self.session.get(
            f"{self.base_url}/projects/{project_id}/tasks/{task_id}/members"
        )
        return self._handle_response(response)

    def add_task_member(
        self, project_id: int, task_id: int, user_id: int, role: str = "assignee"
    ) -> Dict[str, Any]:
        payload = {"user_id": user_id, "role": role}
        response = self.session.post(
            f"{self.base_url}/projects/{project_id}/tasks/{task_id}/members",
            json=payload,
        )
        return self._handle_response(response)

    def remove_task_member(
        self, project_id: int, task_id: int, user_id: int
    ) -> Dict[str, Any]:
        response = self.session.delete(
            f"{self.base_url}/projects/{project_id}/tasks/{task_id}/members/{user_id}"
        )
        return self._handle_response(response)

    def remove_project_member(self, project_id: int, user_id: int) -> Dict[str, Any]:
        response = self.session.delete(
            f"{self.base_url}/projects/{project_id}/members/{user_id}"
        )
        return self._handle_response(response)

    def upload_resource(
        self, file_path: str, resource_type: str = "unknown"
    ) -> Dict[str, Any]:
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {"type": resource_type}
                response = self.session.post(
                    f"{self.base_url}/resources/upload", files=files, data=data
                )
                return self._handle_response(response)
        except Exception as e:
            print(f"Failed to upload resource: {e}")
            return None

    def get_resource_url(self, resource_id: int) -> str:
        return f"{self.base_url}/resources/{resource_id}"

    def get_resource(self, resource_id: int) -> Dict[str, Any]:
        try:
            response = self.session.get(f"{self.base_url}/resources/{resource_id}")
            if response.status_code == 200:
                return {
                    "data": response.content,
                    "format": response.headers.get("X-Resource-Format", "PNG"),
                }
            return None
        except Exception as e:
            print(f"Failed to get resource: {e}")
            return None

    def update_project_members(
        self, project_id: int, user_ids: List[int]
    ) -> Dict[str, Any]:
        payload = {"user_ids": user_ids}
        response = self.session.put(
            f"{self.base_url}/projects/{project_id}/members/batch", json=payload
        )
        return self._handle_response(response)

    def get_members(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        status: str = "active",
    ) -> List[Dict[str, Any]]:
        params = {}
        if search:
            params["search"] = search
        if role:
            params["role"] = role
        if status:
            params["status"] = status

        response = self.session.get(f"{self.base_url}/members", params=params)
        return self._handle_response(response)

    def get_member_stats(self) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/members/stats")
        return self._handle_response(response)

    def search_members(
        self,
        query: str,
        project_id: Optional[int] = None,
        exclude_project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params = {"q": query}
        if project_id:
            params["project_id"] = project_id
        if exclude_project_id:
            params["exclude_project_id"] = exclude_project_id

        response = self.session.get(f"{self.base_url}/members/search", params=params)
        return self._handle_response(response)

    def get_member_stats(self) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/members/stats")
        return self._handle_response(response)

    def search_members(
        self,
        query: str,
        project_id: Optional[int] = None,
        exclude_project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params = {"q": query}
        if project_id:
            params["project_id"] = project_id
        if exclude_project_id:
            params["exclude_project_id"] = exclude_project_id

        response = self.session.get(f"{self.base_url}/members/search", params=params)
        return self._handle_response(response)

    def get_project_members(self, project_id: int) -> List[Dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/projects/{project_id}/members")
        return self._handle_response(response)

    def add_project_member(
        self, project_id: int, user_id: int, role: str = "member"
    ) -> Dict[str, Any]:
        payload = {"user_id": user_id, "role": role}
        response = self.session.post(
            f"{self.base_url}/projects/{project_id}/members", json=payload
        )
        return self._handle_response(response)

    def update_task_members(
        self, project_id: int, task_id: int, user_ids: List[int]
    ) -> Dict[str, Any]:
        payload = {"user_ids": user_ids}
        response = self.session.put(
            f"{self.base_url}/projects/{project_id}/tasks/{task_id}/members/batch",
            json=payload,
        )
        return self._handle_response(response)

    def get_task_members(self, project_id: int, task_id: int) -> List[Dict[str, Any]]:
        response = self.session.get(
            f"{self.base_url}/projects/{project_id}/tasks/{task_id}/members"
        )
        return self._handle_response(response)

    def get_launchers(
        self, project_id: int, task_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            params = {"project_id": project_id}
            if task_id:
                params["task_id"] = task_id
            response = self.session.get(f"{self.base_url}/launchers", params=params)
            return self._handle_response(response)
        except Exception as e:
            print(f"Failed to get launcher configuration: {e}")
            return {}

    def create_launcher(
        self,
        name: str,
        vdata: Dict[str, Any],
        project_id: Optional[int] = None,
        task_id: Optional[int] = None,
        icon_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            processed_vdata = {}
            for version, data in vdata.items():
                version_data = data.copy()
                if icon_path and os.path.exists(icon_path):
                    result = self.upload_resource(
                        icon_path, resource_type="launcher_icon"
                    )
                    if result and "path" in result:
                        version_data["icon"] = result["path"]
                processed_vdata[version] = version_data

            payload = {
                "name": name,
                "vdata": processed_vdata,
                "project_id": project_id,
                "task_id": task_id,
            }

            response = self.session.post(f"{self.base_url}/launchers", json=payload)
            return self._handle_response(response)
        except Exception as e:
            print(f"Failed to create launcher: {e}")
            return None

    def update_launcher(
        self,
        launcher_id: int,
        name: str,
        vdata: Dict[str, Any],
        project_id: int,
        task_id: Optional[int] = None,
        icon_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            processed_vdata = {}
            for version, data in vdata.items():
                version_data = data.copy()
                if icon_path and os.path.exists(icon_path):
                    result = self.upload_resource(
                        icon_path, resource_type="launcher_icon"
                    )
                    if result and "id" in result:
                        version_data["icon"] = f"/resources/{result['id']}"
                processed_vdata[version] = version_data

            payload = {"name": name, "vdata": processed_vdata, "project_id": project_id}
            if task_id:
                payload["task_id"] = task_id

            response = self.session.put(
                f"{self.base_url}/launchers/{launcher_id}", json=payload
            )
            result = self._handle_response(response)
            if result:
                result["vdata"] = result.pop("versions", {})
            return result
        except Exception as e:
            print(f"Failed to update launcher: {e}")
            return None

    def delete_launcher(
        self, launcher_id: int, project_id: int, task_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            params = {"project_id": project_id}
            if task_id:
                params["task_id"] = task_id

            response = self.session.delete(
                f"{self.base_url}/launchers/{launcher_id}", params=params
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"Failed to delete launcher: {e}")
            return None

    def toggle_launcher(
        self,
        launcher_id: int,
        project_id: int,
        task_id: Optional[int] = None,
        action: str = "disable",
    ) -> Dict[str, Any]:
        try:
            params = {"project_id": project_id, "action": action}
            if task_id:
                params["task_id"] = task_id

            response = self.session.post(
                f"{self.base_url}/launchers/{launcher_id}/toggle", params=params
            )
            return self._handle_response(response)
        except Exception as e:
            print(
                f"Failed to {'enable' if action == 'enable' else 'disable'} launcher: {e}"
            )
            return None
