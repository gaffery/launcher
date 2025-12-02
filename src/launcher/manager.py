import os
from typing import List
from PySide2 import QtWidgets, QtCore, QtGui

import wish


class ApiWorkerSignals(QtCore.QObject):
    finished = QtCore.Signal(object)
    error = QtCore.Signal(Exception)


class ApiWorker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = ApiWorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(e)


class BaseManager(object):
    def __init__(self, cons):
        self.cons = cons
        self.view = cons.view
        self.model = cons.model
        self._task_id = None
        self._loading_dots = 0
        self._loading_timer = None
        self.thread_pool = QtCore.QThreadPool()

    def _show_loading(self):
        if self._loading_timer is None:
            self._loading_timer = QtCore.QTimer()
            self._loading_timer.timeout.connect(self._update_loading)
            self._loading_timer.start(500)
            self._loading_dots = 0

    def _hide_loading(self):
        if self._loading_timer:
            self._loading_timer.stop()
            self._loading_timer = None

    def _update_loading(self):
        if self.view.command_label.text().startswith("<span"):
            return
        message = self.view.loading_info
        self._loading_dots = (self._loading_dots + 1) % 4
        dots = "." * self._loading_dots
        self.view.command_label.setText(f"{message}{dots}")

    def run_api_task(
        self,
        api_func,
        *args,
        success_callback=None,
        error_callback=None,
        show_loading=True,
        **kwargs,
    ):
        if show_loading:
            self._show_loading()

        def wrapped_success(result):
            if show_loading:
                self._hide_loading()
            if success_callback:
                success_callback(result)

        def wrapped_error(error):
            if show_loading:
                self._hide_loading()
            if error_callback:
                error_callback(error)
            else:
                print(f"API error: {error}")

        worker = ApiWorker(api_func, *args, **kwargs)
        worker.signals.finished.connect(wrapped_success)
        worker.signals.error.connect(wrapped_error)
        self.thread_pool.start(worker)

    def format_users(self, all_users, current_members):
        processed_users = set()
        formatted_users = []

        if all_users is None:
            return formatted_users
        for member in all_users:
            if member["id"] not in processed_users:
                formatted_users.append(
                    {
                        "id": member["id"],
                        "text": f"{member['username']} ({member['role']})",
                        "is_member": any(m["id"] == member["id"] for m in current_members),
                    }
                )
                processed_users.add(member["id"])
        return formatted_users

    def get_project_task_path(self):
        project_id = None
        task_ids_list = list()
        current_task = self.view.task_lw.currentItem()
        current_project = self.view.project_lw.currentItem()
        if current_project:
            project_id = current_project.data(QtCore.Qt.UserRole)
        else:
            project_id = self.view.project_gbox.property("project_id")
        if current_task:
            item = current_task
            while item:
                item_id = item.data(0, QtCore.Qt.UserRole)
                if item_id:
                    task_ids_list.insert(0, str(item_id))
                item = item.parent()
        task_ids_list.insert(0, str(project_id))
        id_path = "/".join(task_ids_list)
        return id_path

    def get_current_id(self, current_item, config_key):
        current_id = None
        if current_item:
            if config_key == "task_id":
                current_id = current_item.data(0, QtCore.Qt.UserRole)
            else:
                current_id = current_item.data(QtCore.Qt.UserRole)
        else:
            current_id = self.cons.configParser.get("MainUI", config_key, fallback="")
            if current_id and current_id.isdigit():
                current_id = int(current_id)
        if not current_id:
            current_id = None
        return current_id

    def resetCurrentItem(self, parent_lw, selected_item):
        current_item = parent_lw.currentItem()
        if current_item == selected_item:
            parent_lw.currentItemChanged.emit(selected_item, None)
        else:
            parent_lw.setCurrentItem(selected_item)


class ProjectManager(BaseManager):
    def refresh_projects(self):
        def on_success(projects):
            if not projects:
                self.view.task_lw.clear()
                self.view.project_lw.clear()
                self.view.launcher_lw.clear()
                self.view.task_lw.setProperty("tasks", None)
                self.view.project_lw.setProperty("projects", None)
                self.view.launcher_lw.setProperty("launchers", None)
                return
            current_item = self.view.project_lw.currentItem()
            current_id = self.get_current_id(current_item, "project_id")
            if projects == self.view.project_lw.property("projects"):
                self.resetCurrentItem(self.view.project_lw, current_item)
                return
            self.view.project_lw.blockSignals(True)
            self.view.project_lw.clear()
            self.view.project_lw.blockSignals(False)
            for project in projects:
                item = QtWidgets.QListWidgetItem()
                item.setText(project["name"])
                item.setData(QtCore.Qt.UserRole, project["id"])
                self.view.project_lw.addItem(item)
                if project["id"] == current_id:
                    self.resetCurrentItem(self.view.project_lw, item)
            self.view.project_lw.setProperty("projects", projects)
            init_task_id = self.cons.configParser.get("MainUI", "task_id", fallback="")
            if init_task_id:
                self.view.task_lw.setProperty("init_task_id", init_task_id)
                self.cons.switch_task()

        self.run_api_task(
            self.model.get_all_projects,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to get project list: {e}"),
        )

    def add_project(self, name):
        def on_success(result):
            if result:
                print(f"{name} created successfully")
                self.refresh_projects()

        self.run_api_task(
            self.model.add_project,
            name,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to create project: {e}"),
        )

    def edit_project(self, project_id, project_name):
        def on_success(result):
            if result:
                print(f"Rename {project_name} successfully")
                self.cons.update_config("MainUI", "task_id", "")
                self.refresh_projects()

        self.run_api_task(
            self.model.update_project,
            project_id,
            project_name,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to edit project: {e}"),
        )

    def delete_project(self, project_id, project_name):
        def on_success(result):
            if result:
                print(f"{project_name} deleted successfully")
                self.refresh_projects()

        self.run_api_task(
            self.model.delete_project,
            project_id,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to delete project: {e}"),
        )

    def assign_members(self, project_id: int, project_name: str, selected_user_ids: List[int]):
        def on_success(result):
            if result:
                print(f"{project_name} assigned members successfully")

        self.run_api_task(
            self.model.assign_project,
            project_id,
            selected_user_ids,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to assign members: {e}"),
        )

    def show_switch_project_dialog(self):
        self.view.task_lw.hide()
        self.view.project_lw.show()
        self.view.project_gbox.show()
        self.view.project_gbox.setProperty("project_id", None)
        self.view.project_gbox.setTitle(self.view.tr("Projects"))
        self.view.task_lw.setProperty("task_id", None)
        self.view.task_lw.setCurrentItem(None)
        self.view.launcher_lw.setCurrentItem(None)
        self.refresh_projects()

    def show_add_project_dialog(self):
        dialog = self.view.createUI("BaseInputDialog", parent=self.view)
        dialog.setupProjectInput()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            name = dialog.textValue()
            self.add_project(name)

    def show_edit_project_dialog(self):
        current_item = self.view.project_lw.currentItem()
        project_id = current_item.data(QtCore.Qt.UserRole)
        dialog = self.view.createUI("BaseInputDialog", parent=self.view)
        dialog.setTextValue(current_item.text())
        dialog.setupEditProject()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_name = dialog.textValue()
            self.edit_project(project_id, new_name)

    def show_delete_project_dialog(self):
        current_item = self.view.project_lw.currentItem()
        project_id = current_item.data(QtCore.Qt.UserRole)
        project_name = current_item.text()
        dialog = self.view.createUI("BaseMessageBox", parent=self.view)
        dialog.deleteProjectMessage(project_name)
        if dialog.exec_() == QtWidgets.QMessageBox.Yes:
            self.delete_project(project_id, project_name)

    def show_assign_project_dialog(self):
        current_item = self.view.project_lw.currentItem()
        project_id = current_item.data(QtCore.Qt.UserRole)
        project_name = current_item.text()
        dialog = self.view.createUI("BaseDialog", parent=self.view)
        dialog.setupAssignUI([])
        dialog.show()

        def update_member_list(all_users, project_users):
            formatted_users = self.format_users(all_users, project_users)
            dialog.member_list.clear()
            project_member_ids = {member["id"] for member in project_users}
            for user in formatted_users:
                item = QtWidgets.QListWidgetItem(user["text"])
                item.setData(QtCore.Qt.UserRole, user["id"])
                dialog.member_list.addItem(item)
                if user["id"] in project_member_ids:
                    item.setSelected(True)

        def on_dialog_accepted():
            selected_user_ids = [item.data(QtCore.Qt.UserRole) for item in dialog.member_list.selectedItems()]
            self.assign_members(project_id, project_name, selected_user_ids)

        dialog.accepted.connect(on_dialog_accepted)

        self.run_api_task(
            self.model.get_all_users,
            success_callback=lambda all_users: self.run_api_task(
                self.model.get_project_members,
                project_id,
                success_callback=lambda project_users: update_member_list(all_users, project_users),
                error_callback=lambda e: print(f"Failed to get project members: {e}"),
            ),
            error_callback=lambda e: print(f"Failed to get user list: {e}"),
        )
        dialog.exec_()


class TaskManager(BaseManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_parents = dict()

    def refresh_tasks(self, project_id):
        if not project_id:
            self.view.task_lw.clear()
            self.view.task_lw.setProperty("tasks", None)
            return

        def on_success(tasks):
            if not tasks:
                self.view.task_lw.clear()
                self.view.task_lw.setProperty("tasks", None)
                return
            self.task_parents.clear()
            self.build_task_relations(tasks)
            current_item = self.view.task_lw.currentItem()
            current_id = self.get_current_id(current_item, "task_id")
            if tasks == self.view.task_lw.property("tasks"):
                if current_item:
                    self.resetCurrentItem(self.view.task_lw, current_item)
                else:
                    current_id = self.view.task_lw.property("pre_task_id")
                    if current_id:
                        root = self.view.task_lw.invisibleRootItem()
                        self.find_and_select_item(root, current_id)
                return
            self.view.task_lw.blockSignals(True)
            self.view.task_lw.clear()
            self.view.task_lw.blockSignals(False)
            self.build_task_tree(tasks)
            self.view.task_lw.expandAll()
            self.view.task_lw.setProperty("tasks", tasks)
            if current_id:
                root = self.view.task_lw.invisibleRootItem()
                self.find_and_select_item(root, current_id)
            else:
                self.view.task_lw.setCurrentItem(None)

        def on_error(error):
            print(f"Failed to get task list: {error}")
            self.view.task_lw.clear()
            self.view.task_lw.setProperty("tasks", None)
            self.cons.project_manager.show_switch_project_dialog()

        self.run_api_task(
            self.model.get_all_task,
            project_id,
            success_callback=on_success,
            error_callback=on_error,
        )

    def build_task_relations(self, tasks, parent_id=None):
        for task in tasks:
            task_id = task["id"]
            self.task_parents[task_id] = parent_id
            if task.get("children"):
                self.build_task_relations(task["children"], task_id)

    def find_and_select_item(self, item, current_id):
        for i in range(item.childCount()):
            child = item.child(i)
            if child.data(0, QtCore.Qt.UserRole) == current_id:
                self.resetCurrentItem(self.view.task_lw, child)
                return True
            if self.find_and_select_item(child, current_id):
                return True
        return False

    def build_task_tree(self, tasks, parent_item=None):
        for task in tasks:
            if parent_item is None:
                item = QtWidgets.QTreeWidgetItem(self.view.task_lw)
                self.view.task_lw.addTopLevelItem(item)
            else:
                item = QtWidgets.QTreeWidgetItem(parent_item)
                parent_item.addChild(item)

            item.setText(0, task["title"])
            item.setData(0, QtCore.Qt.UserRole, task["id"])

            if task.get("children"):
                self.build_task_tree(task["children"], item)

    def add_task(self, title, project_id, parent_id=None):
        def on_success(result):
            if result:
                print(f"Task {title} added successfully")
                self.refresh_tasks(project_id)

        self.run_api_task(
            self.model.add_task,
            title,
            project_id,
            parent_id,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to add task: {e}"),
        )

    def edit_task(self, title, project_id, task_id):
        def on_success(result):
            if result:
                print(f"Rename Task {title} successfully")
                self.refresh_tasks(project_id)

        self.run_api_task(
            self.model.update_task,
            project_id,
            task_id,
            title,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to edit task: {e}"),
        )

    def delete_task(self, task_name, project_id, task_id):
        def on_success(result):
            if result:
                print(f"Task {task_name} deleted successfully")
                self.refresh_tasks(project_id)
            else:
                print(f"Failed to delete task: {task_name}")

        self.run_api_task(
            self.model.delete_task,
            project_id,
            task_id,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to delete task: {e}"),
        )

    def assign_members(
        self,
        project_id,
        task_id,
        task_name,
        selected_user_ids,
    ):
        def on_success(result):
            if result:
                print(f"{task_name} assigned members successfully")

        self.run_api_task(
            self.model.assign_task,
            project_id,
            task_id,
            selected_user_ids,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to assign task members: {e}"),
        )

    def show_switch_task_dialog(self):
        current_item = self.view.project_lw.currentItem()
        if current_item:
            project_id = current_item.data(QtCore.Qt.UserRole)
            project_name = current_item.text()
            self.view.task_lw.show()
            self.view.project_lw.hide()
            self.view.project_gbox.setTitle(project_name)
            self.view.project_gbox.setProperty("project_id", project_id)
            self.refresh_tasks(project_id)

    def show_add_task_dialog(self):
        project_id = self.view.project_gbox.property("project_id")
        dialog = self.view.createUI("BaseInputDialog", parent=self.view)
        dialog.setupTaskInput()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            task_name = dialog.textValue()
            if task_name:
                self.add_task(task_name, project_id)

    def show_add_subtask_dialog(self):
        current_item = self.view.task_lw.currentItem()
        task_id = current_item.data(0, QtCore.Qt.UserRole)
        project_id = self.view.project_gbox.property("project_id")
        dialog = self.view.createUI("BaseInputDialog", parent=self.view)
        dialog.setupTaskInput()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            task_name = dialog.textValue()
            if task_name:
                self.add_task(task_name, project_id, parent_id=task_id)

    def show_edit_task_dialog(self):
        current_item = self.view.task_lw.currentItem()
        task_id = current_item.data(0, QtCore.Qt.UserRole)
        project_id = self.view.project_gbox.property("project_id")
        dialog = self.view.createUI("BaseInputDialog", parent=self.view)
        dialog.setTextValue(current_item.text(0))
        dialog.setupEditTask()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            task_name = dialog.textValue()
            if task_name:
                self.edit_task(task_name, project_id, task_id)

    def show_delete_task_dialog(self):
        current_item = self.view.task_lw.currentItem()
        task_id = current_item.data(0, QtCore.Qt.UserRole)
        project_id = self.view.project_gbox.property("project_id")
        task_name = current_item.text(0)
        dialog = self.view.createUI("BaseMessageBox", parent=self.view)
        dialog.deleteTaskMessage(task_name)
        if dialog.exec_() == QtWidgets.QMessageBox.Yes:
            self.delete_task(task_name, project_id, task_id)

    def show_assign_task_dialog(self):
        current_item = self.view.task_lw.currentItem()
        if not current_item:
            return

        task_id = current_item.data(0, QtCore.Qt.UserRole)
        task_name = current_item.text(0)
        project_id = self.view.project_gbox.property("project_id")

        dialog = self.view.createUI("BaseDialog", parent=self.view)
        dialog.setupAssignUI([])
        dialog.show()

        def update_member_list(all_users, task_users):
            formatted_users = self.format_users(all_users, task_users)
            task_member_ids = set()
            if task_users:
                for member in task_users:
                    task_member_ids.add(member["id"])
            dialog.member_list.clear()

            for user in formatted_users:
                item = QtWidgets.QListWidgetItem(user["text"])
                item.setData(QtCore.Qt.UserRole, user["id"])
                dialog.member_list.addItem(item)
                if user["id"] in task_member_ids:
                    item.setSelected(True)

        def on_dialog_accepted():
            selected_user_ids = [item.data(QtCore.Qt.UserRole) for item in dialog.member_list.selectedItems()]
            self.assign_members(project_id, task_id, task_name, selected_user_ids)

        dialog.accepted.connect(on_dialog_accepted)

        self.run_api_task(
            self.model.get_project_members,
            project_id,
            success_callback=lambda all_users: self.run_api_task(
                self.model.get_task_members,
                project_id,
                task_id,
                success_callback=lambda task_users: update_member_list(all_users, task_users),
                error_callback=lambda e: print(f"Failed to get task members: {e}"),
            ),
            error_callback=lambda e: print(f"Failed to get project members: {e}"),
        )
        dialog.exec_()


class LauncherManager(BaseManager):
    def __init__(self, cons):
        super().__init__(cons)
        self.pasteboard = None
        self.icon_manager = IconManager(cons)

    def refresh_launchers(self, id_path):
        if not id_path:
            self.view.launcher_lw.clear()
            self.view.launcher_lw.setProperty("launchers", None)
            return

        def on_success(launchers_data):
            if not launchers_data:
                self.view.launcher_lw.clear()
                self.view.launcher_lw.setProperty("launchers", None)
                return
            current_item = self.view.launcher_lw.currentItem()
            current_id = self.get_current_id(current_item, "launcher_id")
            if launchers_data == self.view.launcher_lw.property("launchers"):
                self.post_launchers(current_id)
                return

            self.view.launcher_lw.clear()
            for name, launcher_info in launchers_data.items():
                launcher_item = self.view.createUI("LauncherWindow", parent=self.view)
                app_item = QtWidgets.QListWidgetItem(self.view.launcher_lw)
                app_item.setSizeHint(launcher_item.minimumSizeHint())
                self.init_launcher(launcher_item, name, launcher_info, app_item)
                self.view.launcher_lw.setItemWidget(app_item, launcher_item)
                self.view.launcher_lw.addItem(app_item)
            self.view.launcher_lw.setProperty("launchers", launchers_data)
            self.post_launchers(current_id)

        self.run_api_task(
            self.model.get_launchers,
            id_path,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to get launcher configuration: {e}"),
        )

    def post_launchers(self, current_id):
        selected_item = None
        for i in range(self.view.launcher_lw.count()):
            lw_item = self.view.launcher_lw.item(i)
            launcher_item = self.view.launcher_lw.itemWidget(lw_item)
            mask_item = self.mask_launcher(launcher_item)
            if mask_item and self.model.user_role == self.model.UserRole.MEMBER:
                lw_item.setHidden(True)
            else:
                lw_item.setHidden(False)
                if launcher_item.launcher_id == current_id:
                    selected_item = lw_item
        if selected_item:
            self.view.launcher_lw.setCurrentItem(selected_item)
            self.resetCurrentItem(self.view.launcher_lw, selected_item)
        else:
            self.view.launcher_lw.setCurrentItem(None)
        filter_text = self.view.filter_line.text()
        if filter_text:
            self.cons.filter_launch(filter_text)

    def init_launcher(self, launcher_item, name, launcher_info, app_item):
        launcher_item.cmd = str()
        launcher_item.name = name
        launcher_item.name_label.setText(name)
        launcher_item.launcher_id = launcher_info.get("id")
        launcher_item.launcher_info = launcher_info
        vdata = launcher_info.get("vdata", {})
        launcher_item.version_comb.clear()
        launcher_item.version_comb.data = vdata
        for version in reversed(vdata.keys()):
            launcher_item.version_comb.addItem(version)
        self.switch_version(launcher_item, app_item)
        app_item.setData(QtCore.Qt.UserRole, launcher_item.launcher_id)
        launcher_item.version_comb.activated.connect(lambda: self.switch_version(launcher_item, app_item))

    def switch_version(self, launcher_item, app_item):
        version = launcher_item.version_comb.currentText()
        if not version or not launcher_item.version_comb.data:
            return
        version_data = launcher_item.version_comb.data.get(version)
        if not version_data:
            return
        launcher_item.version = version
        launcher_item.cmd = version_data.get("cmd", "")
        icon_path = version_data.get("icon")
        if icon_path:
            self.icon_manager.load_icon(icon_path, launcher_item.icon_label)
        self.view.launcher_lw.setCurrentItem(app_item)
        app_item.setSelected(True)
        self.cons.launch_info()

    def mask_launcher(self, launcher_item):
        relations = launcher_item.launcher_info.get("relations", {})
        disabled_paths = relations.get("disabled", [])
        enabled_paths = relations.get("enabled", [])
        current_path = self.get_project_task_path()
        final_status = True
        matched_path_length = 0
        for path in disabled_paths + enabled_paths:
            if current_path.startswith(path) and len(path) > matched_path_length:
                matched_path_length = len(path)
                final_status = path in enabled_paths

        if not final_status:
            gray_effect = QtWidgets.QGraphicsColorizeEffect(launcher_item.icon_label)
            gray_effect.setColor(QtGui.QColor("#000000"))
            gray_effect.setStrength(1.0)
            launcher_item.icon_label.setGraphicsEffect(gray_effect)
            launcher_item.setStyleSheet("QWidget {color: #666666;}")
        else:
            launcher_item.icon_label.setGraphicsEffect(None)
            launcher_item.setStyleSheet("")
        return not final_status

    def add_launcher(self, dialog):
        software_name = dialog.software_edit.text().strip()
        if not software_name:
            print("Launcher name cannot be empty")
            return
        if not dialog.version_data:
            print("At least one version is required")
            return
        self.create_launcher(software_name, dialog.version_data)

    def create_launcher(self, name, vdata):
        id_path = self.get_project_task_path()
        upload_queue = []
        for version_key, version_data in vdata.items():
            icon_path = version_data.get("icon", "")
            if icon_path and not icon_path.startswith("/resources/"):
                upload_queue.append((version_key, icon_path))

        def process_uploads():
            if not upload_queue:
                self.run_api_task(
                    self.model.create_launcher,
                    name,
                    id_path,
                    vdata,
                    success_callback=lambda _: self.refresh_launchers(id_path),
                    error_callback=lambda e: print(f"Failed to create launcher: {e}"),
                )
                return

            version_key, icon_path = upload_queue.pop(0)

            def on_icon_uploaded(resource_path):
                vdata[version_key]["icon"] = resource_path
                process_uploads()

            self.icon_manager.upload_icon(icon_path, on_icon_uploaded)

        process_uploads()

    def delete_launcher(self, launcher_id: int):
        id_path = self.get_project_task_path()

        def on_success(result):
            if result and result.get("success"):
                self.refresh_launchers(id_path)
                print("Launcher deleted successfully")
            else:
                print("Failed to delete launcher")

        self.run_api_task(
            self.model.delete_launcher,
            launcher_id,
            id_path,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to delete launcher: {e}"),
        )

    def edit_launcher(self, launcher_id: int, dialog):
        software_name = dialog.software_edit.text().strip()
        if not software_name:
            print("Launcher name cannot be empty")
            return
        if not dialog.version_data:
            print("At least one version is required")
            return

        upload_queue = []
        id_path = self.get_project_task_path()
        for version_key, version_data in dialog.version_data.items():
            icon_path = version_data.get("icon", "")
            if icon_path and not icon_path.startswith("/resources/"):
                upload_queue.append((version_key, icon_path))

        def process_uploads():
            if not upload_queue:
                self.run_api_task(
                    self.model.update_launcher,
                    launcher_id,
                    software_name,
                    id_path,
                    dialog.version_data,
                    success_callback=lambda _: self.refresh_launchers(id_path),
                    error_callback=lambda e: print(f"Failed to update launcher: {e}"),
                )
                return

            version_key, icon_path = upload_queue.pop(0)

            def on_icon_uploaded(resource_path):
                dialog.version_data[version_key]["icon"] = resource_path
                process_uploads()

            self.icon_manager.upload_icon(icon_path, on_icon_uploaded)

        process_uploads()

    def toggle_launcher(self, launcher_id: int, action: str):
        id_path = self.get_project_task_path()

        def on_success(result):
            if result and result.get("success"):
                self.refresh_launchers(id_path)
                print(f"Launcher {'enabled' if action == 'enable' else 'disabled'} successfully")
            else:
                print(f"Failed to {'enable' if action == 'enable' else 'disable'} launcher")

        self.run_api_task(
            self.model.toggle_launcher,
            launcher_id,
            id_path,
            action,
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to {'enable' if action == 'enable' else 'disable'} launcher: {e}"),
        )

    def show_switch_launcher_dialog(self):
        self.view.launcher_gbox.show()
        current_task = self.view.task_lw.currentItem()
        if current_task:
            task_id = current_task.data(0, QtCore.Qt.UserRole)
            self.view.task_lw.setProperty("pre_task_id", task_id)
        id_path = self.get_project_task_path()
        self.refresh_launchers(id_path)

    def show_add_launcher_dialog(self):
        dialog = self.view.createUI("BaseDialog", parent=self.view)
        dialog.setupLauncherUI(self.cons, None)
        dialog.accepted.connect(lambda: self.add_launcher(dialog))
        dialog.show()

    def show_edit_launcher_dialog(self):
        current_item = self.view.launcher_lw.currentItem()
        launcher_item = self.view.launcher_lw.itemWidget(current_item)
        launcher_data = {
            launcher_item.name: {
                "id": launcher_item.launcher_id,
                "vdata": launcher_item.version_comb.data,
            }
        }
        dialog = self.view.createUI("BaseDialog", parent=self.view)
        dialog.setupLauncherUI(self.cons, launcher_data)
        dialog.accepted.connect(lambda: self.edit_launcher(launcher_item.launcher_id, dialog))
        dialog.show()

    def show_copy_launcher_dialog(self):
        current_item = self.view.launcher_lw.currentItem()
        launcher_item = self.view.launcher_lw.itemWidget(current_item)
        self.pasteboard = {
            launcher_item.name: {
                "id": launcher_item.launcher_id,
                "vdata": launcher_item.version_comb.data,
            }
        }

    def show_paste_launcher_dialog(self):
        if not self.pasteboard:
            print("No copied launcher found on the clipboard!!!")
            return
        for name, data in self.pasteboard.items():
            launchers_datas = self.view.launcher_lw.property("launchers")
            if launchers_datas:
                while name in launchers_datas:
                    name += " - Copy"
            self.create_launcher(name, data.get("vdata"))

    def show_toggle_launcher_dialog(self):
        current_item = self.view.launcher_lw.currentItem()
        launcher_item = self.view.launcher_lw.itemWidget(current_item)
        if launcher_item.styleSheet():
            self.toggle_launcher(launcher_item.launcher_id, "enable")
        else:
            self.toggle_launcher(launcher_item.launcher_id, "disable")

    def show_delete_launcher_dialog(self):
        current_item = self.view.launcher_lw.currentItem()
        launcher_item = self.view.launcher_lw.itemWidget(current_item)
        dialog = self.view.createUI("BaseMessageBox", parent=self.view)
        dialog.deleteLauncherMessage(launcher_item.name)
        if dialog.exec_() == QtWidgets.QMessageBox.Yes:
            self.delete_launcher(launcher_item.launcher_id)


class UserManager(BaseManager):
    def refresh_users(self, dialog):
        dialog.user_list.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        def on_complete():
            dialog.user_list.setEnabled(True)

        def on_success(users):
            dialog.user_list.clear()
            for user in users:
                item = QtWidgets.QListWidgetItem()
                item.setText(f"{user['username']} ({user['role']})")
                item.setData(QtCore.Qt.UserRole, user)
                dialog.user_list.addItem(item)
            on_complete()

        def on_error(error):
            print(f"Failed to get user list: {error}")
            on_complete()

        self.run_api_task(
            self.model.get_all_users,
            success_callback=on_success,
            error_callback=on_error,
        )

    def add_user(self, dialog, parent_dialog):
        username = dialog.username_edit.text().strip()
        password = dialog.password_edit.text().strip()
        email = dialog.email_edit.text().strip() or f"{username}@wish.com"
        role = self.model.ROLE_MAP.get(dialog.role_combo.currentIndex(), "member")

        if not username:
            print("Username cannot be empty")
            return

        if not password:
            print("Password cannot be empty")
            return

        if not email:
            print("Email cannot be empty")
            return

        def on_success(result):
            if result:

                def on_get_user_success(users):
                    user = next((u for u in users if u["username"] == username), None)
                    if user:
                        item = QtWidgets.QListWidgetItem()
                        item.setText(f"{username} ({role})")
                        item.setData(QtCore.Qt.UserRole, user)
                        parent_dialog.user_list.addItem(item)
                        print(f"User {username} added successfully")
                    else:
                        print(f"Failed to get user information for {username}")

                def on_get_user_error(error):
                    print(f"Failed to get user information: {error}")

                self.run_api_task(
                    self.model.get_all_users,
                    success_callback=on_get_user_success,
                    error_callback=on_get_user_error,
                )
            else:
                print(f"Failed to add user {username}")

        def on_error(error):
            print(f"Failed to add user: {error}")

        self.run_api_task(
            self.model.add_user,
            username,
            password,
            email,
            role,
            success_callback=on_success,
            error_callback=on_error,
        )

    def delete_user(self, current_item, parent_dialog):
        user_info = current_item.data(QtCore.Qt.UserRole)
        user_id = user_info["id"]
        username = user_info["username"]

        def on_error(error):
            print(f"Failed to delete user {username}: {error}")

        def on_success(result):
            if result:
                print(f"User {username} deleted successfully")
                parent_dialog.user_list.takeItem(parent_dialog.user_list.row(current_item))
            else:
                on_error(result)

        self.run_api_task(
            self.model.delete_user,
            user_id,
            success_callback=on_success,
            error_callback=on_error,
        )

    def edit_user(self, dialog, current_item, parent_dialog):
        user_info = current_item.data(QtCore.Qt.UserRole)
        new_username = dialog.username_edit.text().strip()
        new_password = dialog.password_edit.text() or None
        new_email = dialog.email_edit.text().strip() or None
        new_role = self.model.ROLE_MAP.get(dialog.role_combo.currentIndex())

        def on_success(result):
            if result:
                user_info.update({"username": new_username, "email": new_email, "role": new_role})
                current_item.setText(f"{new_username} ({new_role})")
                current_item.setData(QtCore.Qt.UserRole, user_info)
                print(f"User {user_info['username']} updated successfully")
                parent_dialog.user_list.update()
            else:
                print(f"Failed to update user {user_info['username']}")

        def on_error(error):
            print(f"Failed to update user: {error}")

        self.run_api_task(
            self.model.update_user,
            user_info["id"],
            (new_username if new_username != user_info["username"] else None),
            new_password,
            new_email,
            new_role,
            success_callback=on_success,
            error_callback=on_error,
        )

    def perform_login(self, username, password, dialog=None, init=False):
        def on_error(error):
            login_info = self.view.createUI("BaseMessageBox", parent=self.view)
            login_info.loginMessages(error)
            login_info.exec_()
            self.view.user_comb.setCurrentIndex(0)
            if dialog:
                dialog.reset_login_state()

        def on_success(result):
            if result:
                if self.model.user_role == self.model.UserRole.ADMIN:
                    self.view.user_comb.view().setRowHidden(3, False)
                else:
                    self.view.user_comb.view().setRowHidden(3, True)
                if dialog:
                    dialog.close()
                self.cons.update_config("Login", "username", username)
                self.cons.update_config("Login", "password", password)
                self.view.launcher_lw.setProperty("launcher_id", None)
                self.view.project_lw.setProperty("project_id", None)
                self.view.task_lw.setProperty("task_id", None)
                self.view.user_comb.setItemText(0, username)
                self.cons.project_manager.show_switch_project_dialog()
            else:
                if init:
                    print("Extra Info: Login failed, please check your networks.")
                else:
                    on_error(result)

        self.run_api_task(
            self.model.login,
            username,
            password,
            success_callback=on_success,
            error_callback=on_error,
        )

    def show_user_management(self):
        dialog = self.view.createUI("BaseDialog", parent=self.view)
        dialog.setupUserManagementUI()
        dialog.add_button.clicked.connect(lambda: self.show_add_user_dialog(dialog))
        dialog.delete_button.clicked.connect(lambda item: self.show_delete_user_dialog(dialog, item))
        dialog.user_list.itemDoubleClicked.connect(lambda item: self.show_edit_user_dialog(dialog, item))
        dialog.close_button.clicked.connect(dialog.close)
        self.refresh_users(dialog)
        dialog.exec_()

    def show_add_user_dialog(self, parent_dialog):
        dialog = self.view.createUI("BaseDialog", parent=self.view)
        dialog.setupAddUserUI()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.add_user(dialog, parent_dialog)

    def show_delete_user_dialog(self, parent_dialog, item=None):
        if not item:
            item = parent_dialog.user_list.currentItem()
            name = item.data(QtCore.Qt.UserRole).get("username")
            dialog = self.view.createUI("BaseMessageBox", parent=self.view)
            dialog.deleteUserMessage(name)
            if dialog.exec_() == QtWidgets.QMessageBox.Yes:
                self.delete_user(item, parent_dialog)
        if not item:
            return

    def show_edit_user_dialog(self, parent_dialog, item=None):
        if not item:
            item = parent_dialog.user_list.currentItem()
        if not item:
            return

        user_info = item.data(QtCore.Qt.UserRole)
        if not user_info:
            print("Failed to get user information")
            return

        dialog = self.view.createUI("BaseDialog", parent=self.view)
        dialog.setupUserEditUI(user_info)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.edit_user(dialog, item, parent_dialog)


class IconManager(BaseManager):
    def __init__(self, cons):
        super().__init__(cons)
        self.icon_cache = {}
        self.pending_loads = {}
        self.loading_icons = set()

    def _safe_set_pixmap(self, label, pixmap):
        if not label:
            return False
        try:
            label.setPixmap(pixmap)
            return True
        except RuntimeError:
            return False
        except Exception:
            return False

    def _handle_resource_data(self, icon_path: str, icon_label: QtWidgets.QLabel, resource_data: dict):
        try:
            if resource_data and resource_data.get("data"):
                pixmap = QtGui.QPixmap()
                if pixmap.loadFromData(resource_data["data"]):
                    self.icon_cache[icon_path] = pixmap
                    self._safe_set_pixmap(icon_label, pixmap)
        finally:
            self.loading_icons.discard(icon_path)
            self._process_next_load()

    def _process_next_load(self):
        if not self.pending_loads:
            return

        icon_path, icon_label = self.pending_loads.popitem()
        if icon_path.startswith("/resources/"):
            self._load_resource_icon(icon_path, icon_label)
        else:
            self.loading_icons.discard(icon_path)
            self._process_next_load()

    def _load_resource_icon(self, icon_path: str, icon_label: QtWidgets.QLabel):
        def on_success(resource_data):
            self._handle_resource_data(icon_path, icon_label, resource_data)

        try:
            resource_id = int(icon_path.split("/")[-1])
            self.run_api_task(
                self.model.get_resource,
                resource_id,
                success_callback=on_success,
                error_callback=lambda _: self.loading_icons.discard(icon_path),
                show_loading=False,
            )
        except:
            self.loading_icons.discard(icon_path)

    def load_icon(self, icon_path: str, icon_label: QtWidgets.QLabel):
        if not icon_path:
            return

        if icon_path in self.icon_cache:
            if not self._safe_set_pixmap(icon_label, self.icon_cache[icon_path]):
                self.pending_loads[icon_path] = icon_label
            return

        if icon_path in self.loading_icons:
            self.pending_loads[icon_path] = icon_label
            return

        self.loading_icons.add(icon_path)
        if icon_path.startswith("/resources/"):
            self._load_resource_icon(icon_path, icon_label)
        else:
            self.loading_icons.discard(icon_path)
            self._process_next_load()

    def upload_icon(self, icon_path: str, on_complete):
        if icon_path.startswith("/resources/"):
            on_complete(icon_path)
            return

        if not icon_path or not os.path.exists(icon_path):
            on_complete(icon_path)
            return

        def on_success(resource_data):
            if resource_data and resource_data.get("url"):
                resource_path = resource_data["url"]
                on_complete(resource_path)
            else:
                on_complete(icon_path)

        self.run_api_task(
            self.model.upload_resource,
            icon_path,
            resource_type="image",
            success_callback=on_success,
            error_callback=lambda e: print(f"Failed to upload icon: {e}"),
        )


class TimerWorkerSignals(QtCore.QObject):
    stop_signal = QtCore.Signal()
    check_signal = QtCore.Signal()
    refresh_signal = QtCore.Signal()
    status_signal = QtCore.Signal(bool)


class UpdateCheckWorker(QtCore.QRunnable):
    def __init__(self, signals):
        super().__init__()
        self.signals = signals

    def run(self):
        try:
            acquire = wish.Acquire()
            acquire.load_syncer()
            if not acquire.syncer:
                return
            name = os.environ.get("LAUNCHER_NAME")
            tags = os.environ.get("LAUNCHER_TAGS")

            tags_list = acquire.syncer.get_tags(name)
            tags_list = acquire.custom_sort(tags_list)

            if tags != tags_list[-1]:
                self.signals.check_signal.emit()
        except Exception as e:
            print(f"Failed to check for updates: {e}")


class StatusCheckWorker(QtCore.QRunnable):
    def __init__(self, signals):
        super().__init__()
        self.signals = signals

    def run(self):
        import requests
        import urllib.parse

        api_env_name = os.environ.get("LAUNCHER_API_URL_NAME")
        wish_graphs_url = os.environ.get(api_env_name)
        parse = urllib.parse.urlparse(wish_graphs_url)
        wish_net_url = "{}://{}".format(parse.scheme, parse.netloc)
        try:
            resp = requests.get(f"{wish_net_url}/ping", timeout=3)
            if resp.status_code in (200, 204):
                self.signals.status_signal.emit(True)
            else:
                self.signals.status_signal.emit(False)
        except Exception:
            self.signals.status_signal.emit(False)


class CleanCachesWorker(QtCore.QRunnable):
    def __init__(self):
        super().__init__()

    def run(self):
        try:
            acquire = wish.Acquire()
            acquire.load_syncer()
            if not acquire.syncer:
                return
            acquire.load_dbmanage()
            if not acquire.dbmanage:
                return
            acquire.dbmanage.autoclean_caches(days=7)
        except Exception as e:
            print(f"Failed to Clean for Caches: {e}")


class TimerWorker(QtCore.QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = TimerWorkerSignals()
        self._is_running = True
        self._init_timers()

    def _init_timers(self):
        self.clean_timer = QtCore.QTimer()
        self.clean_timer.timeout.connect(self._clean_caches)
        QtCore.QTimer.singleShot(0, self._clean_caches)
        self.clean_timer.start(3600000)

        self.check_timer = QtCore.QTimer()
        self.check_timer.timeout.connect(self._check_updates)
        QtCore.QTimer.singleShot(0, self._check_updates)
        self.check_timer.start(600000)

        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self._refresh_ui)
        self.refresh_timer.start(30000)

        self.status_timer = QtCore.QTimer()
        self.status_timer.timeout.connect(self._check_status)
        QtCore.QTimer.singleShot(0, self._check_status)
        self.status_timer.start(3000)

        self.signals.stop_signal.connect(self.stop)

    def _clean_caches(self):
        if not self._is_running:
            return
        worker = CleanCachesWorker()
        QtCore.QThreadPool.globalInstance().start(worker)

    def _check_updates(self):
        if not self._is_running:
            return
        worker = UpdateCheckWorker(self.signals)
        QtCore.QThreadPool.globalInstance().start(worker)

    def _check_status(self):
        if not self._is_running:
            return
        worker = StatusCheckWorker(self.signals)
        QtCore.QThreadPool.globalInstance().start(worker)

    def _refresh_ui(self):
        if self._is_running:
            self.signals.refresh_signal.emit()

    def run(self):
        pass

    def stop(self):
        self._is_running = False
        self.clean_timer.stop()
        self.check_timer.stop()
        self.status_timer.stop()
        self.refresh_timer.stop()


class TimerManager(BaseManager):
    def __init__(self, cons):
        super().__init__(cons)
        self.timer_worker = TimerWorker()
        self.timer_worker.signals.check_signal.connect(self.cons.refresh_info)
        self.timer_worker.signals.refresh_signal.connect(self.cons.refresh_view)
        self.timer_worker.signals.status_signal.connect(self.cons.refresh_status)
        self.thread_pool.start(self.timer_worker)

    def stop(self):
        if self.timer_worker:
            self.timer_worker.signals.stop_signal.emit()
