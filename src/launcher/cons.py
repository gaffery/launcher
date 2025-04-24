import os
import sys

import wish
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
    def __init__(self, parent=None):
        super(FocusTracker, self).__init__(parent)
        self.last_focused_textedit = None
        QtWidgets.QApplication.instance().installEventFilter(self)

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
        self.view = view
        self.model = model

    def initialize(self):
        self.initVariables()
        self.initAttributes()
        self.customShortcut()
        self.connectActions()
        self.redirectConsole()

    def initVariables(self):
        self.sync_mode = "1"
        self.keypath_name = "LAUNCHER_KEYPATH"
        self.language_name = "LAUNCHER_LANGUAGE"
        self.launcher_command = os.environ.get("LAUNCHER_COMMAND")
        self.launcher_inherit = os.environ.get("LAUNCHER_INHERIT")
        self.sys_shell_name = os.environ.get("LAUNCHER_SYS_SHELL_NAME")
        self.launcher_pkgroot_name = os.environ.get("LAUNCHER_PKGROOT_NAME")
        self.launcher_pkgmode_name = os.environ.get("LAUNCHER_PKGMODE_NAME")
        self.launcher_task_id_name = os.environ.get("LAUNCHER_TASK_ID_NAME")
        self.launcher_project_id_name = os.environ.get("LAUNCHER_PROJECT_ID_NAME")

    def initAttributes(self):
        self.translator = QtCore.QTranslator()
        self.timer_manager = TimerManager(self)
        self.project_manager = ProjectManager(self)
        self.launcher_manager = LauncherManager(self)
        self.user_manager = UserManager(self)
        self.task_manager = TaskManager(self)

        self.focusTracker = FocusTracker(QtWidgets.QApplication.instance())
        self.configParser = configparser.ConfigParser(interpolation=None)
        self.config_path = os.path.join(os.path.expanduser("~"), ".launcher")
        self.view.launcher_lw.setObjectName("launcher_box")
        self.view.filter_line.setObjectName("search_box")
        self.view.args_edit.setObjectName("command_box")
        self.view.launch_bt.setObjectName("button_box")
        self.initConfigs()

    def initConfigs(self):
        self.switch_lang(None, init=True)
        if not os.path.exists(self.config_path):
            return
        config_file = os.path.join(self.config_path, "launcher.ini")
        if not os.path.exists(config_file):
            return
        self.configParser.read(config_file)
        index = int(self.configParser.get("MainUI", "layout", fallback="0"))
        self.switch_mode(index)
        index = int(self.configParser.get("MainUI", "languages", fallback="0"))
        self.switch_lang(index)
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
        self.view.project_gbox.mouseDoubleClickEvent = lambda _: self.switch_proj()
        self.view.config_comb.currentTextChanged.connect(self.switch_config)
        self.view.task_lw.currentItemChanged.connect(self.switch_launch)
        self.view.filter_line.textChanged.connect(self.filter_launch)
        self.view.tray_restart.triggered.connect(self.tryIconRestart)
        self.view.trayIcon.activated.connect(self.tryIconActivated)
        self.view.tray_quit.triggered.connect(self.tryIconQuit)

        self.view.project_lw.customContextMenuRequested.connect(self.show_project_menu)
        self.view.add_project_action.triggered.connect(self.add_project)
        self.view.delete_project_action.triggered.connect(self.delete_project)
        self.view.assign_project_action.triggered.connect(self.assign_project)

        self.view.task_lw.customContextMenuRequested.connect(self.show_task_menu)
        self.view.add_task_action.triggered.connect(self.add_task)
        self.view.add_subtask_action.triggered.connect(self.add_subtask)
        self.view.delete_task_action.triggered.connect(self.delete_task)
        self.view.assign_task_action.triggered.connect(self.assign_task)

        self.view.launcher_lw.customContextMenuRequested.connect(self.show_launch_menu)
        self.view.send_command_action.triggered.connect(self.send_command)
        self.view.add_launcher_action.triggered.connect(self.add_launcher)
        self.view.edit_launcher_action.triggered.connect(self.edit_launcher)
        self.view.toggle_launcher_action.triggered.connect(self.toggle_launcher)
        self.view.delete_launcher_action.triggered.connect(self.delete_launcher)

    def refresh_info(self):
        span_text = '<span style="color:red;">%s</span>' % self.view.upgrade_info
        self.view.option_comb.setItemText(1, self.view.upgrade_comb)
        self.view.command_label.setText(span_text)
        self.sync_mode = "0"

    def refresh_view(self):
        if not self.model.is_authenticated:
            return
        if self.view.task_lw.isVisible():
            self.task_manager.refresh_tasks(self.view.project_gbox.property("project_id"))
        if self.view.project_lw.isVisible():
            self.project_manager.refresh_projects()

    def switch_config(self, text, init=None):
        if init:
            index = int(init)
            self.view.config_comb.setCurrentIndex(index)
        else:
            index = self.view.config_comb.currentIndex()
            self.update_config("MainUI", "environment", str(index))
        os.environ[self.launcher_pkgmode_name] = str(index)

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
            dialog.darkTitleBar()
            dialog.exec_()
        elif index == 2:
            self.logout()
        elif index == 3:
            if self.model.user_role == self.model.UserRole.ADMIN:
                self.user_manager.show_user_management()
        self.update_config("MainUI", "account", str(index))
        self.view.user_comb.setCurrentIndex(0)

    def switch_mode(self, index):
        if index == 0:
            return
        if index == -1:
            self.modify_mode(0, 0, 1, 1)
        if index == 1:
            self.modify_mode(1, 1, 0, 1)
        if index == 2:
            self.modify_mode(0, 1, 1, 1)
        self.update_config("MainUI", "layout", str(index))
        self.view.mode_comb.setCurrentIndex(0)

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
        app = QtWidgets.QApplication.instance()
        res_dir = os.path.join(os.path.dirname(__file__), "resource")
        locale = QtCore.QLocale.system().name()
        if index == 1:
            locale = "en_US"
        if index == 2:
            locale = "zh_CN"
        os.environ[self.language_name] = locale
        qm_path = os.path.join(res_dir, "{}.qm".format(locale))
        self.translator.load(qm_path)
        app.installTranslator(self.translator)
        app.processEvents()
        self.view.translateUI()
        if self.model.is_authenticated:
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
        src_info = str()
        focus_widget = QtWidgets.QApplication.focusWidget()
        if focus_widget:
            if focus_widget.objectName() == "launcher_box":
                item = self.view.launcher_lw.currentItem()
                if item:
                    widget = self.view.launcher_lw.itemWidget(item)
                    if widget:
                        src_info = widget.cmd
        label_width = self.view.command_label.width()
        metrics = QtGui.QFontMetrics(self.view.command_label.font())
        text_width = metrics.horizontalAdvance(src_info)
        if text_width > label_width:
            src_info = metrics.elidedText(src_info, QtCore.Qt.ElideMiddle, label_width)
        self.view.command_label.setText(src_info)
        self.view.command_label.show()

    def launch_cmd(self, item=None):
        cmd = str()
        self.view.console_browser.clear()
        item = self.view.launcher_lw.currentItem()
        focus_widget = QtWidgets.QApplication.focusWidget()
        if focus_widget.objectName() == "launcher_box":
            if item:
                widget = self.view.launcher_lw.itemWidget(item)
                if not widget.styleSheet():
                    cmd = widget.cmd
        if focus_widget.objectName() in ("command_box", "splitCommand_box"):
            if (self.focusTracker.last_focused_textedit and self.focusTracker.last_focused_textedit.toPlainText()):
                cmd = self.focusTracker.last_focused_textedit.toPlainText()
            elif self.view.args_edit.toPlainText():
                cmd = self.view.args_edit.toPlainText()
            if cmd:
                self.update_config("MainUI", "command", cmd)
        if focus_widget.objectName() == "button_box":
            if (self.focusTracker.last_focused_textedit and self.focusTracker.last_focused_textedit.toPlainText()):
                cmd = self.focusTracker.last_focused_textedit.toPlainText()
            elif self.view.args_edit.toPlainText():
                cmd = self.view.args_edit.toPlainText()
            if cmd:
                self.update_config("MainUI", "command", cmd)
            elif item:
                widget = self.view.launcher_lw.itemWidget(item)
                if not widget.styleSheet():
                    cmd = widget.cmd
        if cmd:
            self.process_start(cmd)
        self.view.launch_bt.clearFocus()

    def logout(self):
        self.view.user_comb.view().setRowHidden(3, True)
        self.model.auth_service.logout()
        self.update_config("Login", "username", "")
        self.update_config("Login", "password", "")
        self.view.user_comb.setItemText(0, self.view.tr("Account"))
        self.view.project_gbox.setTitle(self.view.tr("Projects"))
        self.view.project_lw.setProperty("projects", None)
        self.view.launcher_lw.clear()
        self.view.project_lw.clear()
        self.view.task_lw.clear()
        self.switch_mode(-1)

    def switch_login(self, init=None):
        if init:
            username = self.configParser.get("Login", "username", fallback="")
            password = self.configParser.get("Login", "password", fallback="")
            if not any((username, password)):
                return
            self.user_manager.perform_login(username, password)
            return

        dialog = self.view.createUI("BaseDialog", parent=self.view)
        dialog.setupLoginUI()
        dialog.connects_login(lambda: self.handle_login(dialog))
        dialog.exec_()

    def handle_login(self, dialog):
        username = dialog.user_ledit.text().strip()
        password = dialog.key_ledit.text().strip()

        if not username or not password:
            dialog.reset_login_state()
            return

        self.user_manager.perform_login(username, password, dialog)

    def switch_proj(self):
        self.project_manager.show_switch_project_dialog()

    def switch_task(self):
        self.task_manager.show_switch_task_dialog()

    def add_task(self):
        self.task_manager.show_add_task_dialog()

    def add_subtask(self):
        self.task_manager.show_add_subtask_dialog()

    def delete_task(self):
        self.task_manager.show_delete_task_dialog()

    def assign_task(self):
        self.task_manager.show_assign_task_dialog()

    def switch_launch(self):
        if not self.model.is_authenticated:
            self.switch_mode(-1)
        self.launcher_manager.show_switch_launcher_dialog()

    def filter_launch(self, text):
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
            self.view.darkTitleBar()
            if self.view.isMinimized():
                self.view.showNormal()
            else:
                self.view.show()
            self.view.raise_()
            self.view.activateWindow()

    def tryIconQuit(self):
        self.view.trayIcon.setVisible(False)
        self.timer_manager.stop()
        os._exit(1)

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
        process = self.process_reset(process)
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
            os.environ[self.launcher_pkgmode_name] = self.sync_mode
            process.startDetached(shell, [flag, cmd])
        else:
            process.start(shell, [flag, cmd])
        locale = QtCore.QLocale.system().name()
        if locale == "zh_CN":
            encoding = "gbk"
        else:
            encoding = "utf-8"
        process.readyReadStandardOutput.connect(
            lambda: self.outputConsole(process.readAllStandardOutput().data().decode(encoding, "ignore"))
        )

    def process_reset(self, process):
        inherit_list = list()
        if self.launcher_inherit:
            inherit_list = self.launcher_inherit.split(os.pathsep)
            inherit_list = wish.Require().process_pkgs(inherit_list, syncer=False)
        env = QtCore.QProcessEnvironment.systemEnvironment()
        if not env.contains(self.launcher_pkgroot_name):
            return process
        root_list = env.value(self.launcher_pkgroot_name).split(os.pathsep)
        for root in root_list:
            name = root.split(os.sep)[-2]
            if name not in inherit_list:
                for key in env.keys():
                    remove_flag = False
                    value_list = env.value(key).split(os.pathsep)
                    for value in list(value_list):
                        if value.startswith(root):
                            value_list.remove(value)
                            remove_flag = True
                    if remove_flag:
                        env.insert(key, os.pathsep.join(value_list))
        process.setProcessEnvironment(env)
        return process

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

    def customShortcut(self):
        command = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+E"), self.view)
        command.activated.connect(self.splitCommand)
        closed = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+D"), self.view)
        closed.activated.connect(self.splitClosed)
        enter = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self.view)
        enter.activated.connect(self.launch_cmd)
        switch_up = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Up"), self.view)
        switch_up.activated.connect(lambda: self.switchVersion("up"))
        switch_down = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Down"), self.view)
        switch_down.activated.connect(lambda: self.switchVersion("down"))
        backspace = QtWidgets.QShortcut(QtGui.QKeySequence("Backspace"), self.view)
        backspace.activated.connect(lambda: self.switch_proj())

    def switchVersion(self, direction):
        focus_widget = QtWidgets.QApplication.focusWidget()
        if focus_widget.objectName() == "launcher_box":
            item = self.view.launcher_lw.currentItem()
            if item:
                launcher_item = self.view.launcher_lw.itemWidget(item)
                current_index = launcher_item.version_comb.currentIndex()
                total_versions = launcher_item.version_comb.count()
                if direction == "up":
                    if current_index > 0:
                        launcher_item.version_comb.setCurrentIndex(current_index - 1)
                    else:
                        launcher_item.version_comb.setCurrentIndex(total_versions - 1)
                    launcher_item.version_comb.activated.emit(launcher_item.version_comb.currentIndex())

                elif direction == "down":
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
        if "\r" in text:
            cursor.movePosition(cursor.StartOfLine, cursor.MoveAnchor)
            cursor.movePosition(cursor.EndOfLine, cursor.KeepAnchor)
            cursor.removeSelectedText()
            text = text.replace("\r", "")
        else:
            cursor.movePosition(QtGui.QTextCursor.End)
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
                self.view.project_menu.addAction(self.view.delete_project_action)
                self.view.project_menu.addAction(self.view.assign_project_action)
            self.view.project_menu.exec_(self.view.project_lw.mapToGlobal(pos))

    def add_project(self):
        self.project_manager.show_add_project_dialog()

    def delete_project(self):
        self.project_manager.show_delete_project_dialog()

    def assign_project(self):
        self.project_manager.show_assign_project_dialog()

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
                self.view.launcher_menu.addAction(self.view.add_launcher_action)
                self.view.launcher_menu.addAction(self.view.edit_launcher_action)
                self.view.launcher_menu.addAction(self.view.toggle_launcher_action)
                self.view.launcher_menu.addAction(self.view.delete_launcher_action)
            else:
                self.view.launcher_menu.addAction(self.view.add_launcher_action)
            self.view.launcher_menu.exec_(self.view.launcher_lw.mapToGlobal(pos))

    def add_launcher(self):
        self.launcher_manager.show_add_launcher_dialog()

    def edit_launcher(self):
        self.launcher_manager.show_edit_launcher_dialog()

    def toggle_launcher(self):
        self.launcher_manager.show_toggle_launcher_dialog()

    def send_command(self):
        item = self.view.launcher_lw.currentItem()
        widget = self.view.launcher_lw.itemWidget(item)
        self.view.args_edit.setText(widget.cmd)

    def delete_launcher(self):
        self.launcher_manager.show_delete_launcher_dialog()
