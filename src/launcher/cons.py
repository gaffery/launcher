import os
import sys
import locale

import configparser
from PySide2 import QtGui, QtCore, QtWidgets

from .manager import (
    UserManager,
    TaskManager,
    TimerManager,
    ProjectManager,
    LauncherManager,
)


class RedirectStream(QtCore.QObject):
    textWritten = QtCore.Signal(str)

    def write(self, text):
        self.textWritten.emit(str(text))

    def flush(self):
        pass


class FocusTracker(QtCore.QObject):
    def __init__(self, app):
        super(FocusTracker, self).__init__(app)
        self.last_focused_textedit = None
        app.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.FocusIn:
            if isinstance(obj, QtWidgets.QTextEdit):
                if obj.objectName():
                    if self.last_focused_textedit is not None:
                        self.last_focused_textedit.destroyed.disconnect(self.on_textedit_destroyed)
                    self.last_focused_textedit = obj
                    self.last_focused_textedit.destroyed.connect(self.on_textedit_destroyed)

        return super(FocusTracker, self).eventFilter(obj, event)

    def on_textedit_destroyed(self):
        self.last_focused_textedit = None


class MainCons(object):
    def __init__(self, view, model):
        self.app = QtWidgets.QApplication.instance()
        self.model = model
        self.view = view

    def initialize(self):
        self.initVariables()
        self.initAttributes()
        self.customShortcut()
        self.connectActions()
        self.redirectConsole()

    def initVariables(self):
        self.sync_mode = "1"
        self.layout_mode = None
        self.language_name = "LAUNCHER_LANGUAGE"
        self.launcher_command = os.environ.get("LAUNCHER_COMMAND")
        self.sys_shell_name = os.environ.get("LAUNCHER_SYS_SHELL_NAME")
        self.launcher_pkgroot_name = os.environ.get("LAUNCHER_PKGROOT_NAME")
        self.launcher_offline_name = os.environ.get("LAUNCHER_OFFLINE_NAME")
        self.launcher_develop_name = os.environ.get("LAUNCHER_DEVELOP_NAME")

    def initAttributes(self):
        self.translator = QtCore.QTranslator()
        self.timer_manager = TimerManager(self)
        self.project_manager = ProjectManager(self)
        self.launcher_manager = LauncherManager(self)
        self.user_manager = UserManager(self)
        self.task_manager = TaskManager(self)

        self.focusTracker = FocusTracker(self.app)
        self.configParser = configparser.ConfigParser(interpolation=None)
        self.config_path = os.path.join(os.path.expanduser("~"), ".launcher")
        self.view.launcher_lw.setObjectName("launcher_box")
        self.view.project_lw.setObjectName("project_box")
        self.view.task_lw.setObjectName("task_box")
        self.view.filter_line.setObjectName("search_box")
        self.view.args_edit.setObjectName("command_box")
        self.view.launch_bt.setObjectName("button_box")
        self.view.activated()
        self.initConfigs()

    def initConfigs(self):
        self.switch_lang(None, init=True)
        self.switch_mode("0", init=True)
        self.switch_user("0", init=True)
        self.switch_config(None, init="0")
        if not os.path.exists(self.config_path):
            return
        config_file = os.path.join(self.config_path, "launcher.ini")
        if not os.path.exists(config_file):
            return
        self.configParser.read(config_file)
        index = int(self.configParser.get("MainUI", "languages", fallback="0"))
        self.switch_lang(index)
        index = int(self.configParser.get("MainUI", "layout", fallback="0"))
        self.switch_mode(index, init=True)
        index = int(self.configParser.get("MainUI", "environment", fallback="0"))
        self.switch_config(None, init=index)
        index = int(self.configParser.get("MainUI", "account", fallback="0"))
        self.switch_user(index, init=True)
        cmd = self.configParser.get("MainUI", "command", fallback="")
        self.view.args_edit.setPlainText(cmd)

    def connectActions(self):
        self.view.launch_bt.clicked.connect(self.launch_cmd)
        self.view.user_comb.activated.connect(self.switch_user)
        self.view.mode_comb.activated.connect(self.switch_mode)
        self.view.lang_comb.activated.connect(self.switch_lang)
        self.view.option_comb.activated.connect(self.switch_option)
        self.view.launcher_lw.itemDoubleClicked.connect(self.launch_cmd)
        self.view.launcher_lw.currentItemChanged.connect(self.launch_info)
        self.view.project_lw.itemDoubleClicked.connect(self.switch_task)
        self.view.project_lw.currentItemChanged.connect(self.switch_launch)
        self.view.project_gbox.mouseDoubleClickEvent = lambda _: self.toggle_proj()
        self.view.launcher_gbox.mouseDoubleClickEvent = lambda _: self.toggle_lach()
        self.view.command_gbox.mouseDoubleClickEvent = lambda _: self.toggle_input()
        self.view.console_gbox.mouseDoubleClickEvent = lambda _: self.toggle_input()
        self.view.config_comb.currentTextChanged.connect(self.switch_config)
        self.view.task_lw.currentItemChanged.connect(self.switch_launch)
        self.view.filter_line.textChanged.connect(self.filter_launch)
        self.view.tray_restart.triggered.connect(self.tryIconRestart)
        self.view.trayIcon.activated.connect(self.tryIconActivated)
        self.view.tray_quit.triggered.connect(self.tryIconQuit)

        self.view.project_lw.customContextMenuRequested.connect(self.show_project_menu)
        self.view.add_project_action.triggered.connect(self.add_project)
        self.view.edit_project_action.triggered.connect(self.edit_project)
        self.view.delete_project_action.triggered.connect(self.delete_project)
        self.view.assign_project_action.triggered.connect(self.assign_project)

        self.view.task_lw.customContextMenuRequested.connect(self.show_task_menu)
        self.view.add_task_action.triggered.connect(self.add_task)
        self.view.edit_task_action.triggered.connect(self.edit_task)
        self.view.add_subtask_action.triggered.connect(self.add_subtask)
        self.view.delete_task_action.triggered.connect(self.delete_task)
        self.view.assign_task_action.triggered.connect(self.assign_task)

        self.view.launcher_lw.customContextMenuRequested.connect(self.show_launch_menu)
        self.view.send_command_action.triggered.connect(self.send_command)
        self.view.add_launcher_action.triggered.connect(self.add_launcher)
        self.view.edit_launcher_action.triggered.connect(self.edit_launcher)
        self.view.copy_launcher_action.triggered.connect(self.copy_launcher)
        self.view.paste_launcher_action.triggered.connect(self.paste_launcher)
        self.view.toggle_launcher_action.triggered.connect(self.toggle_launcher)
        self.view.delete_launcher_action.triggered.connect(self.delete_launcher)

    def refresh_info(self):
        span_text = '<span style="color:red;">%s</span>' % self.view.upgrade_info
        self.view.option_comb.setItemText(1, self.view.upgrade_comb)
        self.view.command_label.setText(span_text)
        self.sync_mode = "0"

    def refresh_view(self):
        if not self.model.authenticated:
            return
        if self.view.task_lw.isVisible():
            self.task_manager.refresh_tasks(self.view.project_gbox.property("project_id"))
        if self.view.project_lw.isVisible():
            self.project_manager.refresh_projects()

    def refresh_status(self, status):
        self.view.online = status
        self.view.translateTitle()
        if os.environ[self.launcher_offline_name] == "1":
            status = False
        if status == self.model.online:
            return
        self.model.online = status
        self.refresh_view()

    def switch_config(self, _, init=None):
        if init:
            index = int(init)
            self.view.config_comb.setCurrentIndex(index)
        else:
            index = self.view.config_comb.currentIndex()
            self.update_config("MainUI", "environment", str(index))
        os.environ[self.launcher_offline_name] = str(index)
        os.environ[self.launcher_develop_name] = str(index)
        status = getattr(self.view, "online", False)
        self.refresh_status(status)

    def switch_user(self, index, init=None):
        if init:
            self.switch_login(init=init)
            return
        if index == 0:
            return
        elif index == 1:
            dialog = self.view.createUI("BaseDialog", parent=self.view)
            dialog.setupLoginUI()
            dialog.connects_login(self.handle_login)
            dialog.exec_()
        elif index == 2:
            self.logout()
        elif index == 3:
            if self.model.user_role == self.model.UserRole.ADMIN:
                self.user_manager.show_user_management()
        self.update_config("MainUI", "account", str(index))
        self.view.user_comb.setCurrentIndex(0)

    def switch_mode(self, index, init=False):
        if index == 0:
            return
        if index == -1:
            self.modify_mode(0, 0, 1, 1)
        if index == 1:
            self.modify_mode(1, 1, 0, 1)
        if index == 2:
            self.modify_mode(0, 1, 1, 1)
        self.view.mode_comb.setCurrentIndex(0)
        if init:
            return
        self.update_config("MainUI", "layout", str(index))
        self.layout_mode = str(index)

    def modify_mode(self, *args):
        gbox_list = (
            self.view.project_gbox,
            self.view.launcher_gbox,
            self.view.command_gbox,
            self.view.console_gbox,
        )
        for i in range(len(args)):
            if args[i] == 0:
                args_name = "hide"
            else:
                args_name = "show"
            method = getattr(gbox_list[i], args_name)
            method()

    def switch_option(self, index):
        if index == 0:
            return
        if index == 1:
            self.tryIconRestart()
        if index == 2:
            self.tryIconQuit()
        self.view.option_comb.setCurrentIndex(0)

    def switch_lang(self, index, init=None):
        if index == 0:
            return
        current_user = self.view.user_comb.currentText()
        res_dir = os.path.join(os.path.dirname(__file__), "resource")
        locale = QtCore.QLocale.system().name()
        if index == 1:
            locale = "en_US"
        if index == 2:
            locale = "zh_CN"
        os.environ[self.language_name] = locale
        qm_path = os.path.join(res_dir, "{}.qm".format(locale))
        self.translator.load(qm_path)
        self.app.installTranslator(self.translator)
        self.app.processEvents()
        self.view.translateUI()
        if self.model.authenticated:
            if self.model.user_role == self.model.UserRole.ADMIN:
                self.view.user_comb.view().setRowHidden(3, False)
            self.view.user_comb.setItemText(0, current_user)
        if self.view.command_label.text().startswith("<span"):
            span_text = '<span style="color:red;">%s</span>' % self.view.upgrade_info
            self.view.option_comb.setItemText(1, self.view.upgrade_comb)
            self.view.command_label.setText(span_text)
        if init:
            return
        self.update_config("MainUI", "languages", str(index))
        self.view.lang_comb.setCurrentIndex(0)

    def launch_info(self):
        if self.view.command_label.text().startswith("<span"):
            return
        src_info = str()
        pre_info = self.view.command_label.text()
        item = self.view.launcher_lw.currentItem()
        if item:
            widget = self.view.launcher_lw.itemWidget(item)
            if widget:
                src_info = widget.cmd
        if src_info == pre_info:
            return
        label_width = self.view.command_label.width()
        metrics = QtGui.QFontMetrics(self.view.command_label.font())
        text_width = metrics.horizontalAdvance(src_info)
        if text_width > label_width:
            src_info = metrics.elidedText(src_info, QtCore.Qt.ElideMiddle, label_width)
        self.view.command_label.setText(src_info)
        self.view.command_label.show()

    def launch_cmd(self, item=None):
        cmd = str()
        item = self.view.launcher_lw.currentItem()
        focus_widget = QtWidgets.QApplication.focusWidget()
        if focus_widget.objectName() == "launcher_box":
            if item:
                widget = self.view.launcher_lw.itemWidget(item)
                if not widget.styleSheet():
                    cmd = widget.cmd
        if focus_widget.objectName() in ("button_box", "command_box", "splitCommand_box"):
            if self.focusTracker.last_focused_textedit:
                cmd = self.focusTracker.last_focused_textedit.toPlainText()
            elif self.view.args_edit.toPlainText():
                cmd = self.view.args_edit.toPlainText()
            if cmd:
                self.update_config("MainUI", "command", cmd)
        if cmd:
            self.view.console_browser.clear()
            self.process_start(cmd)
        self.view.launch_bt.clearFocus()

    def logout(self):
        self.view.user_comb.view().setRowHidden(3, True)
        self.model.logout()
        self.update_config("Login", "username", "")
        self.update_config("Login", "password", "")
        self.view.user_comb.setItemText(0, self.view.tr("Account"))
        self.view.project_gbox.setTitle(self.view.tr("Projects"))
        self.view.launcher_lw.setProperty("launchers", None)
        self.view.project_lw.setProperty("projects", None)
        self.view.task_lw.setProperty("tasks", None)
        self.view.command_label.clear()
        self.view.launcher_lw.clear()
        self.view.project_lw.clear()
        self.view.task_lw.clear()
        self.switch_mode(-1)

    def switch_login(self, init=None):
        if init:
            username = self.configParser.get("Login", "username", fallback="")
            password = self.configParser.get("Login", "password", fallback="")
            if not all((username, password)):
                return
            self.user_manager.perform_login(username, password, init=True)
            return

        dialog = self.view.createUI("BaseDialog", parent=self.view)
        dialog.setupLoginUI()
        dialog.connects_login(lambda: self.handle_login(dialog))
        dialog.exec_()

    def handle_login(self, dialog):
        username = dialog.user_ledit.text().strip()
        password = dialog.key_ledit.text().strip()
        if not all((username, password)):
            dialog.reset_login_state()
            return
        self.user_manager.perform_login(username, password, dialog)
        self.switch_mode(1)

    def toggle_lach(self):
        if self.view.project_gbox.isVisible():
            self.view.project_gbox.hide()
        else:
            self.view.project_gbox.show()

    def toggle_proj(self):
        if self.view.project_gbox.isVisible():
            if self.view.project_lw.isVisible():
                self.view.project_gbox.hide()
            else:
                self.project_manager.show_switch_project_dialog()
                self.view.project_lw.setFocus()
        else:
            self.project_manager.show_switch_project_dialog()
            self.view.project_lw.setFocus()

    def toggle_input(self):
        if self.view.command_gbox.isVisible():
            self.view.command_gbox.hide()
        else:
            self.view.command_gbox.show()

    def add_project(self):
        self.project_manager.show_add_project_dialog()

    def edit_project(self):
        self.project_manager.show_edit_project_dialog()

    def delete_project(self):
        self.project_manager.show_delete_project_dialog()

    def assign_project(self):
        self.project_manager.show_assign_project_dialog()

    def add_task(self):
        self.task_manager.show_add_task_dialog()

    def add_subtask(self):
        self.task_manager.show_add_subtask_dialog()

    def edit_task(self):
        self.task_manager.show_edit_task_dialog()

    def delete_task(self):
        self.task_manager.show_delete_task_dialog()

    def assign_task(self):
        self.task_manager.show_assign_task_dialog()

    def switch_task(self):
        self.task_manager.show_switch_task_dialog()

    def switch_launch(self):
        self.launcher_manager.show_switch_launcher_dialog()
        if not self.model.authenticated:
            self.switch_mode(-1)
        elif not self.layout_mode:
            index = int(self.configParser.get("MainUI", "layout", fallback="0"))
            self.switch_mode(index)

    def update_preset(self):
        task_id = None
        project_id = None
        current_task = self.view.task_lw.currentItem()
        if current_task:
            task_id = current_task.data(0, QtCore.Qt.UserRole)
        else:
            task_id = self.view.task_lw.property("task_id")
        current_project = self.view.project_lw.currentItem()
        if current_project:
            project_id = current_project.data(QtCore.Qt.UserRole)
        else:
            project_id = self.view.project_gbox.property("project_id")
        if project_id:
            self.update_config("MainUI", "project_id", str(project_id))
        else:
            self.update_config("MainUI", "project_id", "")
        if task_id:
            self.update_config("MainUI", "task_id", str(task_id))
        else:
            self.update_config("MainUI", "task_id", "")

    def filter_launch(self, text):
        text = text.strip()
        if text:
            for x in range(self.view.launcher_lw.count()):
                lw_item = self.view.launcher_lw.item(x)
                widget = self.view.launcher_lw.itemWidget(lw_item)
                if text.lower() in widget.name_label.text().lower():
                    lw_item.setHidden(False)
                else:
                    lw_item.setHidden(True)
        else:
            for x in range(self.view.launcher_lw.count()):
                lw_item = self.view.launcher_lw.item(x)
                lw_item.setHidden(False)
        for x in range(self.view.launcher_lw.count()):
            lw_item = self.view.launcher_lw.item(x)
            if not lw_item.isHidden():
                self.view.launcher_lw.setCurrentItem(lw_item)
                break

    def tryIconActivated(self, event):
        if event in (
            QtWidgets.QSystemTrayIcon.DoubleClick,
            QtWidgets.QSystemTrayIcon.MiddleClick,
            QtWidgets.QSystemTrayIcon.Trigger,
        ):
            self.view.activated()

    def tryIconQuit(self):
        self.view.trayIcon.setVisible(False)
        self.timer_manager.stop()
        self.update_preset()
        self.app.quit()
        os._exit(0)

    def tryIconRestart(self):
        if self.launcher_command:
            self.process_start(self.launcher_command, detach=True)
        self.tryIconQuit()

    def update_config(self, section, name, value):
        if not self.configParser.has_section(section):
            self.configParser.add_section(section)
        self.configParser.set(section, name, value)
        if not os.path.exists(self.config_path):
            os.mkdir(self.config_path)
        config_file = os.path.join(self.config_path, "launcher.ini")
        with open(config_file, "w") as f:
            self.configParser.write(f)

    def process_start(self, cmd, detach=False):
        process = QtCore.QProcess(self.view)
        process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        shell = os.environ.get(self.sys_shell_name)
        if sys.platform.startswith("win"):
            flag = "/c"
            cmd = cmd.replace(">", r"^^^>")
            cmd = cmd.replace("<", r"^^^<")
        else:
            flag = "-c"
            cmd = cmd.replace(">", r"\>")
            cmd = cmd.replace("<", r"\<")
        if detach:
            os.environ[self.launcher_offline_name] = self.sync_mode
            process.startDetached(shell, [flag, cmd])
        else:
            process.start(shell, [flag, cmd])
        encoding = locale.getpreferredencoding()
        process.readyReadStandardOutput.connect(
            lambda: self.outputConsole(process.readAllStandardOutput().data().decode(encoding, "ignore"))
        )

    def splitCommand(self):
        split_command = self.view.createUI("BaseTextEdit")
        split_command.setObjectName("splitCommand_box")
        split_command.setMinimumHeight(50)
        self.view.cmd_layout.addWidget(split_command)

    def splitClosed(self):
        focus_widget = QtWidgets.QApplication.focusWidget()
        if focus_widget:
            if focus_widget.objectName() == "splitCommand_box":
                focus_widget.deleteLater()

    def doubleEnter(self):
        focus_widget = QtWidgets.QApplication.focusWidget()
        if focus_widget:
            if focus_widget.objectName() in ("command_box", "splitCommand_box"):
                self.launch_cmd()

    def singleEnter(self):
        focus_widget = QtWidgets.QApplication.focusWidget()
        if focus_widget:
            if focus_widget.objectName() in ("launcher_box", "button_box"):
                self.launch_cmd()
            if focus_widget.objectName() == "project_box":
                self.switch_task()

    def backSpace(self):
        focus_widget = QtWidgets.QApplication.focusWidget()
        if focus_widget and self.view.task_lw.isVisible():
            self.toggle_proj()

    def customShortcut(self):
        command = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+E"), self.view)
        command.activated.connect(self.splitCommand)
        closed = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+D"), self.view)
        closed.activated.connect(self.splitClosed)
        double_enter = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self.view)
        double_enter.activated.connect(self.doubleEnter)
        switch_up = QtWidgets.QShortcut(QtGui.QKeySequence("Right"), self.view.launcher_lw)
        switch_up.activated.connect(lambda: self.switchVersion("Right"))
        switch_up.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        switch_down = QtWidgets.QShortcut(QtGui.QKeySequence("Left"), self.view.launcher_lw)
        switch_down.activated.connect(lambda: self.switchVersion("Left"))
        switch_down.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        single_enter = QtWidgets.QShortcut(QtGui.QKeySequence("Return"), self.view)
        single_enter.activated.connect(self.singleEnter)
        switch_proj = QtWidgets.QShortcut(QtGui.QKeySequence("Backspace"), self.view)
        switch_proj.activated.connect(self.backSpace)

    def switchVersion(self, direction):
        item = self.view.launcher_lw.currentItem()
        if item:
            launcher_item = self.view.launcher_lw.itemWidget(item)
            current_index = launcher_item.version_comb.currentIndex()
            total_versions = launcher_item.version_comb.count()
            if direction == "Right":
                if current_index > 0:
                    launcher_item.version_comb.setCurrentIndex(current_index - 1)
                else:
                    launcher_item.version_comb.setCurrentIndex(total_versions - 1)
                launcher_item.version_comb.activated.emit(launcher_item.version_comb.currentIndex())

            elif direction == "Left":
                if current_index < total_versions - 1:
                    launcher_item.version_comb.setCurrentIndex(current_index + 1)
                else:
                    launcher_item.version_comb.setCurrentIndex(0)
                launcher_item.version_comb.activated.emit(launcher_item.version_comb.currentIndex())

    def redirectConsole(self):
        sys.stdout = RedirectStream()
        sys.stderr = RedirectStream()
        self.view.connect(
            sys.stderr,
            QtCore.SIGNAL("textWritten(QString)"),
            self.outputConsole,
        )
        self.view.connect(
            sys.stdout,
            QtCore.SIGNAL("textWritten(QString)"),
            self.outputConsole,
        )

    def outputConsole(self, text):
        cursor = self.view.console_browser.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        if "\r" in text and "Progress:" in text:
            cursor.movePosition(cursor.StartOfLine, cursor.MoveAnchor)
            cursor.movePosition(cursor.EndOfLine, cursor.KeepAnchor)
            cursor.removeSelectedText()
            text = text.replace("\r", "")
        cursor.insertText(text)
        self.view.console_browser.setTextCursor(cursor)
        self.view.console_browser.ensureCursorVisible()

    def show_project_menu(self, pos):
        if self.model.user_role in (
            self.model.UserRole.ADMIN,
            self.model.UserRole.MANAGER,
        ):
            current_item = self.view.project_lw.currentItem()
            self.view.project_menu.clear()
            self.view.project_menu.addAction(self.view.add_project_action)
            if current_item:
                self.view.project_menu.addAction(self.view.edit_project_action)
                self.view.project_menu.addAction(self.view.delete_project_action)
                self.view.project_menu.addAction(self.view.assign_project_action)
            self.view.project_menu.exec_(self.view.project_lw.mapToGlobal(pos))

    def show_task_menu(self, pos):
        if self.model.user_role in (
            self.model.UserRole.ADMIN,
            self.model.UserRole.MANAGER,
        ):
            current_item = self.view.task_lw.currentItem()
            self.view.task_menu.clear()
            self.view.task_menu.addAction(self.view.add_task_action)
            if current_item:
                self.view.task_menu.addAction(self.view.add_subtask_action)
                self.view.task_menu.addAction(self.view.edit_task_action)
                self.view.task_menu.addAction(self.view.delete_task_action)
                self.view.task_menu.addAction(self.view.assign_task_action)
            self.view.task_menu.exec_(self.view.task_lw.mapToGlobal(pos))

    def show_launch_menu(self, pos):
        if self.model.user_role in (
            self.model.UserRole.ADMIN,
            self.model.UserRole.MANAGER,
        ):
            self.view.launcher_menu.clear()
            current_item = self.view.launcher_lw.itemAt(pos)
            if current_item:
                self.view.launcher_menu.addAction(self.view.send_command_action)
                self.view.launcher_menu.addAction(self.view.edit_launcher_action)
                self.view.launcher_menu.addAction(self.view.copy_launcher_action)
                self.view.launcher_menu.addAction(self.view.toggle_launcher_action)
                self.view.launcher_menu.addAction(self.view.delete_launcher_action)
            else:
                self.view.launcher_menu.addAction(self.view.add_launcher_action)
                self.view.launcher_menu.addAction(self.view.paste_launcher_action)
            self.view.launcher_menu.exec_(self.view.launcher_lw.mapToGlobal(pos))

    def send_command(self):
        item = self.view.launcher_lw.currentItem()
        widget = self.view.launcher_lw.itemWidget(item)
        self.view.args_edit.setText(widget.cmd)
        self.view.command_gbox.show()

    def add_launcher(self):
        self.launcher_manager.show_add_launcher_dialog()

    def edit_launcher(self):
        self.launcher_manager.show_edit_launcher_dialog()

    def copy_launcher(self):
        self.launcher_manager.show_copy_launcher_dialog()

    def paste_launcher(self):
        self.launcher_manager.show_paste_launcher_dialog()

    def toggle_launcher(self):
        self.launcher_manager.show_toggle_launcher_dialog()

    def delete_launcher(self):
        self.launcher_manager.show_delete_launcher_dialog()
