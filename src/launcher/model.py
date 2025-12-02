import os
import json
import pickle
import hashlib
import importlib.util
from functools import wraps


def loaderplugin():
    client = None
    if os.environ.get("LAUNCHER_CLIENT_PLUGINS"):
        for plugin_path in os.environ["LAUNCHER_CLIENT_PLUGINS"].split(os.pathsep):
            if not plugin_path:
                continue
            try:
                plugin_path_file = os.path.join(plugin_path, "client.py")
                spec = importlib.util.spec_from_file_location("client", plugin_path_file)
                client = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(client)
                break
            except Exception as e:
                print(f"Failed to load launcher client plugin from {plugin_path}: {e}")
                client = None
    if client is None:
        from . import client
    if not hasattr(client, "APIClient"):
        raise ImportError("No APIClient found in launcher client module")
    return client.APIClient()


def authenticate(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.authenticated:
            return func(self, *args, **kwargs)
        else:
            raise Exception("User not authenticated")

    return wrapper


def onlineable(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.online:
            result = func(self, *args, **kwargs)
            return result
        else:
            raise Exception("Client is offline")

    return wrapper


def cacheable(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._cache_model:
            return func(self, *args, **kwargs)
        cache_key = self._cache_model._make_cache_key(func.__name__, args, kwargs)
        cache_path = os.path.join(self._cache_model.CACHE_DIR, f"{cache_key}.pkl")
        if self.online:
            result = func(self, *args, **kwargs)
            with open(cache_path, "wb") as f:
                pickle.dump(result, f)
            return result
        else:
            if os.path.exists(cache_path):
                with open(cache_path, "rb") as f:
                    result = pickle.load(f)
                    return result

    return wrapper


class CacheModel(object):
    if os.environ.get("LAUNCHER_TEMP"):
        CACHE_DIR = os.environ["LAUNCHER_TEMP"]
    else:
        CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

    def __init__(self):
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    def _make_cache_key(self, func_name, args, kwargs):
        try:
            params_str = json.dumps({"args": args, "kwargs": kwargs})
        except Exception:
            params_str = str((args, kwargs))
        key_raw = func_name + params_str
        key_hash = hashlib.md5(key_raw.encode("utf-8")).hexdigest()
        return key_hash


class AuthModel(object):
    def __init__(self):
        self._api_client = loaderplugin()
        self._online = False
        self.logout()

    def logout(self):
        self._role = None
        self._username = None
        self._password = None
        self._response = None
        self._authenticated = False

    def login(self, username=None, password=None, response=None, perform=True):
        if username:
            self._username = username
        if password:
            self._password = password
        if response:
            self._response = response
        if self._online and self._username and self._password and perform:
            self.response = self._api_client.login(self._username, self._password)
        if self._response and "token" in self._response:
            self._role = self._response.get("role", "member")
            self._authenticated = True
            return True


class MainModel(object):
    class UserRole:
        MEMBER = "member"
        MANAGER = "manager"
        ADMIN = "admin"

    ROLE_MAP = {
        0: "member",
        1: "manager",
        2: "admin",
    }

    def __init__(self):
        self._auth_model = AuthModel()
        self._cache_model = CacheModel()

    def logout(self):
        return self._auth_model.logout()

    @property
    def user_role(self):
        return self._auth_model._role

    @property
    def authenticated(self):
        return self._auth_model._authenticated

    @property
    def online(self):
        return self._auth_model._online

    @online.setter
    def online(self, status):
        self._auth_model._online = status
        self._auth_model.login()

    def login(self, username, password):
        response = self.prelogin(username, password)
        if response and "token" in response:
            return self._auth_model.login(username, password, response, perform=False)
        raise Exception("User not authenticated")

    @cacheable
    def prelogin(self, username, password):
        response = self._auth_model._api_client.login(username, password)
        if response and "token" in response:
            return response
        raise Exception("User not authenticated")

    @cacheable
    @authenticate
    def get_all_users(self):
        return self._auth_model._api_client.get_users()

    @onlineable
    @authenticate
    def add_user(self, username, password, email, role="member"):
        return self._auth_model._api_client.create_user(username, password, email, role)

    @onlineable
    @authenticate
    def delete_user(self, user_id):
        return self._auth_model._api_client.delete_user(user_id)

    @onlineable
    @authenticate
    def update_user(self, user_id, username, password, email, role):
        return self._auth_model._api_client.update_user(user_id, username, password, email, role)

    @cacheable
    @authenticate
    def get_all_projects(self):
        return self._auth_model._api_client.get_projects()

    @cacheable
    @authenticate
    def get_project_members(self, project_id):
        return self._auth_model._api_client.get_members(project_id, None)

    @onlineable
    @authenticate
    def add_project(self, project_name):
        return self._auth_model._api_client.create_project(project_name)

    @onlineable
    @authenticate
    def update_project(self, project_id, project_name):
        return self._auth_model._api_client.update_project(project_id, project_name)

    @onlineable
    @authenticate
    def delete_project(self, project_id):
        return self._auth_model._api_client.delete_project(project_id)

    @onlineable
    @authenticate
    def assign_project(self, project_id, user_ids):
        return self._auth_model._api_client.update_project_members(project_id, user_ids)

    @cacheable
    @authenticate
    def get_all_task(self, project_id):
        return self._auth_model._api_client.get_tasks(project_id)

    @cacheable
    @authenticate
    def get_task_members(self, project_id, task_id):
        return self._auth_model._api_client.get_members(project_id, task_id)

    @onlineable
    @authenticate
    def add_task(self, title, project_id, parent_id):
        return self._auth_model._api_client.create_task(title, project_id, parent_id)

    @onlineable
    @authenticate
    def update_task(self, project_id, task_id, task_name):
        return self._auth_model._api_client.update_task(project_id, task_id, task_name)

    @onlineable
    @authenticate
    def delete_task(self, project_id, task_id):
        return self._auth_model._api_client.delete_task(project_id, task_id)

    @onlineable
    @authenticate
    def assign_task(self, project_id, task_id, user_ids):
        return self._auth_model._api_client.update_task_members(project_id, task_id, user_ids)

    @cacheable
    @authenticate
    def get_resource(self, resource_id):
        return self._auth_model._api_client.get_resource(resource_id)

    @onlineable
    @authenticate
    def upload_resource(self, icon_path, resource_type="image"):
        return self._auth_model._api_client.upload_resource(icon_path, resource_type)

    @cacheable
    @authenticate
    def get_launchers(self, path):
        return self._auth_model._api_client.get_launchers(path)

    @onlineable
    @authenticate
    def create_launcher(self, name, path, vdata):
        return self._auth_model._api_client.create_launcher(name, path, vdata)

    @onlineable
    @authenticate
    def update_launcher(self, launcher_id, name, path, vdata):
        return self._auth_model._api_client.update_launcher(launcher_id, name, path, vdata)

    @onlineable
    @authenticate
    def delete_launcher(self, launcher_id, path):
        return self._auth_model._api_client.delete_launcher(launcher_id, path)

    @onlineable
    @authenticate
    def toggle_launcher(self, launcher_id, path, action="disable"):
        return self._auth_model._api_client.toggle_launcher(launcher_id, path, action)
