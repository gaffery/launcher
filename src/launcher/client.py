import os
import requests
import urllib.parse
from requests.adapters import HTTPAdapter
from .ldap import ldap_login


class APIClient:
    def __init__(self):
        wish_graphs_url = os.environ.get("WISH_RESTAPI_URL")
        parse = urllib.parse.urlparse(wish_graphs_url)
        wish_net_url = "{}://{}".format(parse.scheme, parse.netloc)
        self.base_url = wish_net_url.rstrip("/")
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=3, pool_maxsize=300, max_retries=3)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _handle_token(self, value):
        if value:
            self.session.headers.update({"Authorization": f"Bearer {value}"})
        else:
            self.session.headers.pop("Authorization", None)

    def _handle_status(self, response, raw=False):
        if response.status_code == 401:
            raise Exception("Authentication failed")
        elif response.status_code == 403:
            raise Exception("Permission denied")
        elif response.status_code >= 400:
            if not raw:
                data = response.json()
                raise Exception(data.get("error", "Unknown error"))
            raise Exception("Failed to get resource")

        return response.content if raw else response.json()

    def _sorted_launchers(self, launchers):
        if not isinstance(launchers, dict):
            return launchers

        def launcher_id_key(info: dict):
            lid = info.get("id", None)
            try:
                return (0, int(lid))
            except Exception:
                return (1, str(lid) if lid is not None else "")

        sorted_items = sorted(launchers.items(), key=lambda item: launcher_id_key(item[1] or {}))
        launchers = {k: v for k, v in sorted_items}
        return launchers

    def _sorted_projects(self, projects):
        def safe_int_id(p):
            try:
                pid = p.get("id") if isinstance(p, dict) else p
                if pid is None:
                    return float("inf")
                return int(pid)
            except Exception:
                return float("inf")

        if isinstance(projects, list):
            return sorted(projects, key=lambda p: safe_int_id(p))
        if isinstance(projects, dict):
            try:
                pid = projects.get("id")
                return int(pid) if pid is not None else float("inf")
            except Exception:
                return float("inf")
        return projects

    def _sorted_tasks(self, tasks):
        def safe_int(v):
            try:
                return int(v)
            except Exception:
                return float("inf")

        def sort_list(lst):
            lst.sort(key=lambda t: safe_int(t.get("id")))
            for t in lst:
                children = t.get("children") or []
                if isinstance(children, list) and children:
                    sort_list(children)

        if isinstance(tasks, list):
            sort_list(tasks)
        return tasks

    def login(self, username, password):
        ldap_authenticator = ldap_login(username, password)
        if ldap_authenticator:
            self.create_or_update_ldap_user(username, password, ldap_authenticator)
        url = f"{self.base_url}/auth/login"
        payload = {"username": username, "password": password}
        response = self.session.post(url=url, json=payload, timeout=3)
        response = self._handle_status(response)
        if "token" in response:
            self._handle_token(response["token"])
        return response

    def create_or_update_ldap_user(self, username, password, ldap_authenticator):
        url = f"{self.base_url}/users/sync"
        payload = {
            "username": username,
            "fullName": ldap_authenticator.fullName,
            "email": ldap_authenticator.mail,
            "password": password,
        }
        response = self.session.post(url=url, json=payload, timeout=3)
        response = self._handle_status(response)
        return response

    def get_users(self):
        response = self.session.get(f"{self.base_url}/users")
        return self._handle_status(response)

    def get_launchers(self, path):
        params = {"path": path}
        response = self.session.get(f"{self.base_url}/launchers", params=params)
        launchers = self._handle_status(response)
        launchers = self._sorted_launchers(launchers)
        return launchers

    def get_projects(self):
        response = self.session.get(f"{self.base_url}/projects")
        projects = self._handle_status(response)
        projects = self._sorted_projects(projects)
        return projects

    def get_tasks(self, project_id):
        response = self.session.get(f"{self.base_url}/projects/{project_id}/tasks")
        tasks = self._handle_status(response)
        task_dict = {}
        for task in tasks:
            task_dict[task["id"]] = {
                "id": task["id"],
                "title": task["title"],
                "parent_id": task.get("parent_id"),
                "children": [],
            }

        tasks = list()
        for _, task in task_dict.items():
            if not task["parent_id"]:
                tasks.append(task)
            else:
                parent = task_dict.get(task["parent_id"])
                if parent:
                    parent["children"].append(task)
        tasks = self._sorted_tasks(tasks)
        return tasks

    def get_members(self, project_id, task_id):
        if task_id is None:
            response = self.session.get(f"{self.base_url}/projects/{project_id}/members")
        else:
            response = self.session.get(f"{self.base_url}/projects/{project_id}/tasks/{task_id}/members")
        return self._handle_status(response)

    def get_resource(self, resource_id):
        response = self.session.get(f"{self.base_url}/resources/{resource_id}")
        if response.status_code == 200:
            return {
                "data": response.content,
                "format": response.headers.get("X-Resource-Format", "PNG"),
            }
        return None

    def create_project(self, name):
        response = self.session.post(f"{self.base_url}/projects", json={"name": name})
        return self._handle_status(response)

    def update_project(self, project_id, project_name):
        payload = {"name": project_name}
        response = self.session.put(f"{self.base_url}/projects/{project_id}", json=payload)
        return self._handle_status(response)

    def delete_project(self, project_id):
        response = self.session.delete(f"{self.base_url}/projects/{project_id}")
        return self._handle_status(response)

    def create_task(self, title, project_id, parent_id):
        payload = {
            "title": title,
            "description": "",
            "priority": 1,
            "parent_id": parent_id,
        }
        response = self.session.post(f"{self.base_url}/projects/{project_id}/tasks", json=payload)
        return self._handle_status(response)

    def update_task(self, project_id, task_id, task_name):
        payload = {"title": task_name}
        response = self.session.put(f"{self.base_url}/projects/{project_id}/tasks/{task_id}", json=payload)
        return self._handle_status(response)

    def delete_task(self, project_id, task_id):
        response = self.session.delete(f"{self.base_url}/projects/{project_id}/tasks/{task_id}")
        return self._handle_status(response)

    def update_project_members(self, project_id, user_ids):
        payload = {"user_ids": user_ids}
        response = self.session.put(f"{self.base_url}/projects/{project_id}/members/batch", json=payload)
        return self._handle_status(response)

    def update_task_members(self, project_id, task_id, user_ids):
        payload = {"user_ids": user_ids}
        response = self.session.put(
            f"{self.base_url}/projects/{project_id}/tasks/{task_id}/members/batch",
            json=payload,
        )
        return self._handle_status(response)

    def create_user(self, username, password, email, role):
        response = self.session.post(
            f"{self.base_url}/users",
            json={
                "username": username,
                "password": password,
                "email": email,
                "role": role,
            },
        )
        return self._handle_status(response)

    def update_user(self, user_id, username, password, email, role):
        data = {"username": username, "password": password, "email": email, "role": role}
        data = {k: v for k, v in data.items() if v is not None}
        response = self.session.put(f"{self.base_url}/users/{user_id}", json=data)
        return self._handle_status(response)

    def delete_user(self, user_id):
        response = self.session.delete(f"{self.base_url}/users/{user_id}")
        return self._handle_status(response)

    def upload_resource(self, file_path, resource_type):
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"type": resource_type}
            response = self.session.post(f"{self.base_url}/resources/upload", files=files, data=data)
            return self._handle_status(response)

    def create_launcher(self, name, path, vdata):
        processed_vdata = {}
        for version, data in vdata.items():
            version_data = data.copy()
            processed_vdata[version] = version_data
        payload = {"name": name, "path": path, "vdata": processed_vdata}
        response = self.session.post(f"{self.base_url}/launchers", json=payload)
        return self._handle_status(response)

    def update_launcher(self, launcher_id, name, path, vdata):
        processed_vdata = {}
        for version, data in vdata.items():
            version_data = data.copy()
            processed_vdata[version] = version_data

        payload = {"name": name, "path": path, "vdata": processed_vdata}
        response = self.session.put(f"{self.base_url}/launchers/{launcher_id}", json=payload)
        result = self._handle_status(response)
        if result:
            result["vdata"] = result.pop("versions", {})
        return result

    def delete_launcher(self, launcher_id, path):
        params = {"path": path}
        response = self.session.delete(f"{self.base_url}/launchers/{launcher_id}", params=params)
        return self._handle_status(response)

    def toggle_launcher(self, launcher_id, path, action):
        params = {"path": path, "action": action}
        response = self.session.post(f"{self.base_url}/launchers/{launcher_id}/toggle", params=params)
        return self._handle_status(response)
