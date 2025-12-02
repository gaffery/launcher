import os
import sys
import ctypes

from PySide2 import QtGui, QtCore, QtWidgets


class CenteredItemDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = QtCore.Qt.AlignCenter


class BaseLineEdit(QtWidgets.QLineEdit):
    def __init__(self, *args, **kwargs):
        super(BaseLineEdit, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        path = e.mimeData().text().replace("file:///", "")
        self.setText(path)


class BaseTreeWidget(QtWidgets.QTreeWidget):
    def __init__(self, *args, **kwargs):
        super(BaseTreeWidget, self).__init__(*args, **kwargs)
        self.header().setVisible(False)
        self.setColumnCount(1)
        self.hide()


class BaseTextEdit(QtWidgets.QTextEdit):
    def __init__(self, *args, **kwargs):
        super(BaseTextEdit, self).__init__(*args, **kwargs)
        self.setTabChangesFocus(True)
        self.setAcceptRichText(False)
        self.setAcceptDrops(True)
        self.default_font_size = 12
        self.zoom_level = self.default_font_size * 10

    def dropEvent(self, e):
        path = e.mimeData().text().replace("file:///", "")
        new_path = self.toPlainText() + path
        super(BaseTextEdit, self).dropEvent(e)
        self.setText(new_path)

    def updateFontSize(self):
        font = self.document().defaultFont()
        font.setPointSizeF(self.zoom_level * 0.1)
        self.document().setDefaultFont(font)

        self.setPlainText(self.toPlainText())

    def wheelEvent(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_level += 10
            else:
                self.zoom_level = max(10, self.zoom_level - 10)
            self.updateFontSize()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton and event.modifiers() & QtCore.Qt.ControlModifier:
            self.zoom_level = self.default_font_size * 10
            self.updateFontSize()
            event.accept()
        else:
            super().mousePressEvent(event)


class BaseTextBrowser(QtWidgets.QTextBrowser):
    def __init__(self, parent=None):
        super(BaseTextBrowser, self).__init__(parent)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.default_font_size = 12
        self.zoom_level = self.default_font_size * 10

    def updateFontSize(self):
        font = self.document().defaultFont()
        font.setPointSizeF(self.zoom_level * 0.1)
        self.document().setDefaultFont(font)

        self.setPlainText(self.toPlainText())

    def wheelEvent(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_level += 10
            else:
                self.zoom_level = max(10, self.zoom_level - 10)
            self.updateFontSize()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton and event.modifiers() & QtCore.Qt.ControlModifier:
            self.zoom_level = self.default_font_size * 10
            self.updateFontSize()
            event.accept()
        else:
            super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        clear_action = QtWidgets.QAction("Clear", self)
        clear_action.triggered.connect(self.clear_content)
        menu.addAction(clear_action)
        menu.exec_(event.globalPos())

    def clear_content(self):
        self.clear()


class BaseComboBox(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        super(BaseComboBox, self).__init__(*args, *kwargs)
        self.setItemDelegate(CenteredItemDelegate(self))
        self.setFixedWidth(110)
        self.setEditable(True)
        self.type = str()
        self.name = str()
        self.data = dict()
        self.context = str()
        self.comb_ledit = self.lineEdit()
        self.comb_ledit.setAlignment(QtCore.Qt.AlignCenter)
        self.comb_ledit.setReadOnly(True)
        self.comb_ledit.setFocusPolicy(QtCore.Qt.NoFocus)
        self.comb_ledit.selectionChanged.connect(lambda: self.comb_ledit.deselect())
        self.combClickable(self.comb_ledit).connect(self.showPopup)
        self.contextMenuEvent = lambda event: None
        self.wheelEvent = lambda event: None

    def combClickable(self, widget):
        class Filter(QtCore.QObject):
            clicked = QtCore.Signal()

            def eventFilter(self, obj, event):
                if obj == widget:
                    if event.type() != QtCore.QEvent.Type.MouseButtonRelease:
                        return False
                    if obj.rect().contains(event.pos()):
                        self.clicked.emit()
                        return True
                return False

        filter = Filter(widget)
        widget.installEventFilter(filter)
        return filter.clicked

    def showPopup(self):
        popup = self.view().window()
        pos = self.mapToGlobal(QtCore.QPoint(0, self.height()))
        screen = QtWidgets.QApplication.screenAt(self.mapToGlobal(QtCore.QPoint(0, 0)))
        if screen:
            screen_geometry = screen.geometry()
            popup_geometry = popup.geometry()
            popup_geometry.moveTopLeft(pos)
            if popup_geometry.right() > screen_geometry.right():
                popup_geometry.moveRight(screen_geometry.right())
            if popup_geometry.bottom() > screen_geometry.bottom():
                popup_geometry.moveBottom(pos.y() - self.height())
            popup.setGeometry(popup_geometry)
        super().showPopup()


class BaseListWidget(QtWidgets.QListWidget):
    def __init__(self, *args, **kwargs):
        super(BaseListWidget, self).__init__(*args, **kwargs)

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            event.accept()
        else:
            super(BaseListWidget, self).mouseDoubleClickEvent(event)


class BaseWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(BaseWindow, self).__init__(parent)
        self.hSpacer = QtWidgets.QSpacerItem(
            0,
            0,
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum,
        )
        self.vSpacer = QtWidgets.QSpacerItem(
            0,
            0,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding,
        )

        self.initStyle()

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.darkTitleBar()

    def darkTitleBar(self, hwnd=None):
        if sys.platform.startswith("win"):
            if not hwnd:
                hwnd = int(self.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            set_window_attribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(1)),
                ctypes.sizeof(ctypes.c_int(1)),
            )

    def initStyle(self):
        current_dir = os.path.dirname(__file__)
        style_file = os.path.join(current_dir, "resource", "dark.qss")
        with open(style_file, "r", encoding="utf-8") as f:
            style_sheet = f.read()
            self.setStyleSheet(style_sheet)
        window_icon = os.path.join(current_dir, "resource", "dark.ico")
        self.setWindowIcon(QtGui.QIcon(window_icon))


class BaseDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def setupLauncherUI(self, cons=None, launcher_data=None):
        if launcher_data:
            self.setWindowTitle(self.tr("Edit Launcher"))
        else:
            self.setWindowTitle(self.tr("New Launcher"))
        self.setMinimumWidth(400)
        layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()
        name_layout = QtWidgets.QHBoxLayout()
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setScaledContents(True)
        name_layout.addWidget(self.icon_label)

        self.software_edit = QtWidgets.QLineEdit()
        name_layout.addWidget(self.software_edit)
        form_layout.addRow(self.tr("Name:"), name_layout)
        self.delete_version_button = QtWidgets.QPushButton(self.tr("Remove"))

        version_layout = QtWidgets.QHBoxLayout()
        self.version_combo = BaseComboBox()
        version_layout.addWidget(self.version_combo)
        version_layout.addWidget(self.delete_version_button)
        form_layout.addRow(self.tr("Version List:"), version_layout)

        layout.addLayout(form_layout)

        version_group = BaseGroupBox(self.tr("Version Details"))
        version_layout = QtWidgets.QFormLayout()

        version_input_layout = QtWidgets.QHBoxLayout()
        self.version_edit = QtWidgets.QLineEdit()
        self.add_version_button = QtWidgets.QPushButton(self.tr("Add"))
        version_input_layout.addWidget(self.version_edit)
        version_input_layout.addWidget(self.add_version_button)
        version_layout.addRow(self.tr("Version:"), version_input_layout)

        icon_layout = QtWidgets.QHBoxLayout()
        self.icon_edit = QtWidgets.QLineEdit()
        self.browse_button = QtWidgets.QPushButton(self.tr("Browse"))
        icon_layout.addWidget(self.icon_edit)
        icon_layout.addWidget(self.browse_button)
        version_layout.addRow(self.tr("IconPath:"), icon_layout)

        cmd_layout = QtWidgets.QHBoxLayout()
        self.command_edit = QtWidgets.QLineEdit()
        self.run_button = QtWidgets.QPushButton(self.tr("Execute"))
        cmd_layout.addWidget(self.command_edit)
        cmd_layout.addWidget(self.run_button)
        version_layout.addRow(self.tr("Command:"), cmd_layout)

        version_group.setLayout(version_layout)
        layout.addWidget(version_group)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("OK"))
        button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))

        def on_accept():
            icon = self.icon_edit.text().strip()
            version = self.version_edit.text().strip()
            command = self.command_edit.text().strip()
            if not self.software_edit.text().strip():
                print("启动器名称为空")
                return
            if not version or not command:
                print("版本或命令为空")
                return
            for v in self.version_delete:
                if v in self.version_data:
                    del self.version_data[v]
            current_version = self.version_combo.currentText()
            if current_version:
                self.version_data.pop(current_version)
            if version not in self.version_data:
                self.version_data[version] = {"cmd": command, "icon": icon}
            else:
                self.version_data[version]["cmd"] = command
                self.version_data[version]["icon"] = icon
            if not self.version_data:
                print("版本数据为空")
                return
            self.accept()

        button_box.accepted.connect(on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.version_data = dict()
        self.version_delete = list()
        if launcher_data:
            for name, vdata in launcher_data.items():
                self.software_edit.setText(name)
                self.version_data = vdata.get("vdata", {})
        for version in reversed(self.version_data.keys()):
            self.version_combo.addItem(version)
            if self.version_combo.count() == 1:
                self.version_edit.setText(version)
                data = self.version_data.get(version)
                self.icon_edit.setText(data.get("icon", ""))
                self.command_edit.setText(data.get("cmd", ""))

        def choose_icon():
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                self.tr("Choose Icon"),
                "",
                self.tr("Images (*.png *.jpg *.jpeg *.ico)"),
            )
            if file_path:
                self.icon_edit.setText(file_path)

        def execute():
            command = self.command_edit.text()
            if cons:
                cons.process_start(command)

        self.run_button.clicked.connect(execute)
        self.browse_button.clicked.connect(choose_icon)
        self.add_version_button.clicked.connect(self._add_version)
        self.delete_version_button.clicked.connect(self._delete_version)
        self.version_combo.currentIndexChanged.connect(self._on_version_changed)

    def _add_version(self):
        version = self.version_edit.text()
        command = self.command_edit.text()
        if not version or not command:
            print("版本或命令为空")
            return
        if version in self.version_delete:
            self.version_delete.remove(version)
        self.version_data[version] = {"cmd": command, "icon": self.icon_edit.text()}
        current_index = self.version_combo.findText(version)
        if current_index == -1:
            self.version_combo.addItem(version)
            self.version_combo.setCurrentText(version)

    def _delete_version(self):
        index = self.version_combo.currentIndex()
        version = self.version_combo.currentText()
        if version and version in self.version_data:
            self.version_delete.append(version)
            self.version_combo.removeItem(index)
            self._on_version_changed(index - 1)

    def _on_version_changed(self, index):
        if index >= 0:
            version = self.version_combo.itemText(index)
            if version in self.version_data:
                data = self.version_data[version]
                if isinstance(data, dict):
                    self.version_edit.setText(version)
                    self.command_edit.setText(data.get("cmd", ""))
                    self.icon_edit.setText(data.get("icon", ""))

    def setupUserManagementUI(self):
        self.setWindowTitle(self.tr("User Management"))
        self.setMinimumWidth(400)
        layout = QtWidgets.QVBoxLayout(self)
        self.user_list = QtWidgets.QListWidget()
        layout.addWidget(self.user_list)
        button_layout = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton(self.tr("Add User"))
        self.delete_button = QtWidgets.QPushButton(self.tr("Delete User"))
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.delete_button)
        layout.addLayout(button_layout)
        self.close_button = QtWidgets.QPushButton(self.tr("Close"))
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)

    def setupAddUserUI(self):
        self.setWindowTitle(self.tr("Add User"))
        layout = QtWidgets.QFormLayout(self)
        self.username_edit = QtWidgets.QLineEdit()
        layout.addRow(self.tr("Username:"), self.username_edit)
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addRow(self.tr("Password:"), self.password_edit)
        self.email_edit = QtWidgets.QLineEdit()
        self.email_edit.setPlaceholderText(self.tr("Leave blank to use username@wish.com"))
        layout.addRow(self.tr("Email:"), self.email_edit)
        self.role_combo = BaseComboBox()
        self.role_combo.addItems([self.tr("Member"), self.tr("Manager"), self.tr("Admin")])
        layout.addRow(self.tr("Role:"), self.role_combo)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("OK"))
        button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def setupAssignUI(self, users):
        self.setWindowTitle(self.tr("Assign Members"))
        layout = QtWidgets.QVBoxLayout(self)
        self.member_list = QtWidgets.QListWidget()
        self.member_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for user in users:
            item = QtWidgets.QListWidgetItem(user["text"])
            item.setData(QtCore.Qt.UserRole, user)
            self.member_list.addItem(item)
            if user.get("is_member"):
                item.setSelected(True)

        layout.addWidget(self.member_list)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("OK"))
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def setupUserEditUI(self, user_info):
        self.setWindowTitle(self.tr("Edit User"))
        layout = QtWidgets.QFormLayout(self)
        role = user_info.get("role")
        email = user_info.get("email")
        username = user_info.get("username")
        self.username_edit = QtWidgets.QLineEdit(username)
        self.username_edit.setPlaceholderText(self.tr("Enter new username"))
        layout.addRow(self.tr("Username:"), self.username_edit)

        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_edit.setPlaceholderText(self.tr("Leave blank if no change"))
        layout.addRow(self.tr("Password:"), self.password_edit)

        self.email_edit = QtWidgets.QLineEdit(email or "")
        self.email_edit.setPlaceholderText(self.tr("Enter new email"))
        layout.addRow(self.tr("Email:"), self.email_edit)

        self.role_combo = BaseComboBox()
        self.role_combo.addItems([self.tr("Member"), self.tr("Manager"), self.tr("Admin")])

        role_index = {"member": 0, "manager": 1, "admin": 2}.get(role.lower(), 0)
        self.role_combo.setCurrentIndex(role_index)
        layout.addRow(self.tr("Role:"), self.role_combo)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("OK"))
        button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def setupLoginUI(self):
        self.setWindowTitle(self.tr("Login"))
        self.setFixedSize(400, 0)
        mainLayout = QtWidgets.QHBoxLayout(self)
        left_layout = QtWidgets.QVBoxLayout()
        mainLayout.addLayout(left_layout)
        user_layout = QtWidgets.QHBoxLayout()
        self.user_label = QtWidgets.QLabel(self.tr("Username:"))
        self.user_label.setMinimumWidth(50)
        self.user_ledit = QtWidgets.QLineEdit()
        user_layout.addWidget(self.user_label)
        user_layout.addWidget(self.user_ledit)
        left_layout.addLayout(user_layout)
        key_layout = QtWidgets.QHBoxLayout()
        self.key_label = QtWidgets.QLabel(self.tr("Password:"))
        self.key_label.setMinimumWidth(50)
        self.key_ledit = QtWidgets.QLineEdit()
        self.key_ledit.setEchoMode(QtWidgets.QLineEdit.Password)
        key_layout.addWidget(self.key_label)
        key_layout.addWidget(self.key_ledit)
        left_layout.addLayout(key_layout)
        button_layout = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(button_layout)
        self.set_bt = QtWidgets.QPushButton(self.tr("Login"))
        self.set_bt.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        button_layout.addWidget(self.set_bt)
        self.loading = False

    def connects_login(self, login_func):
        self.set_bt.clicked.connect(lambda: self.handle_login(lambda: login_func(self)))
        self.key_ledit.returnPressed.connect(lambda: self.handle_login(lambda: login_func(self)))

    def handle_login(self, login_func):
        if self.loading:
            return
        self.loading = True
        self.user_ledit.setEnabled(False)
        self.key_ledit.setEnabled(False)
        self.set_bt.setEnabled(False)
        self.set_bt.setDown(True)
        login_func()

    def reset_login_state(self):
        self.loading = False
        self.user_ledit.setEnabled(True)
        self.key_ledit.setEnabled(True)
        self.set_bt.setEnabled(True)
        self.set_bt.setDown(False)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent:
            parent_center = self.parent.geometry().center()
            self.move(
                parent_center.x() - self.width() // 2,
                parent_center.y() - self.height() // 2,
            )


class BaseInputDialog(QtWidgets.QInputDialog):
    def __init__(self, parent=None):
        super(BaseInputDialog, self).__init__(parent)

    def setupProjectInput(self):
        self.setWindowTitle(self.tr("New Project"))
        self.setLabelText(self.tr("Please enter the project name:"))
        self.setCancelButtonText(self.tr("Cancel"))
        self.setOkButtonText(self.tr("OK"))

    def setupEditProject(self):
        self.setWindowTitle(self.tr("Edit Project"))
        self.setLabelText(self.tr("Please enter the project name:"))
        self.setCancelButtonText(self.tr("Cancel"))
        self.setOkButtonText(self.tr("OK"))

    def setupTaskInput(self):
        self.setWindowTitle(self.tr("New Task"))
        self.setLabelText(self.tr("Please enter the task name:"))
        self.setCancelButtonText(self.tr("Cancel"))
        self.setOkButtonText(self.tr("OK"))

    def setupEditTask(self):
        self.setWindowTitle(self.tr("Edit Task"))
        self.setLabelText(self.tr("Please enter the task name:"))
        self.setCancelButtonText(self.tr("Cancel"))
        self.setOkButtonText(self.tr("OK"))


class BaseMessageBox(QtWidgets.QMessageBox):
    def __init__(self, parent=None):
        super(BaseMessageBox, self).__init__(parent)
        self.parent = parent
        self.texts = {
            "delete": {
                "user": {
                    "title": "Delete User",
                    "message": "Are you sure to delete user: ",
                },
                "project": {
                    "title": "Delete Project",
                    "message": "Are you sure to delete project: ",
                },
                "task": {
                    "title": "Delete Task",
                    "message": "Are you sure to delete task: ",
                },
                "launcher": {
                    "title": "Delete Launcher",
                    "message": "Are you sure to delete launcher: ",
                },
            }
        }

    def loginMessages(self, error):
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)
        self.setButtonText(QtWidgets.QMessageBox.Ok, self.tr("OK"))
        self.setWindowTitle(self.tr("Login failed"))
        message = self.tr("Login failed, please check your network...")
        if error:
            message = self.tr("Account or password is incorrect, please try again...")
        self.setText(message)

    def deleteProjectMessage(self, name):
        self.setText(self.tr("Are you sure to delete project: ") + name)
        self.setWindowTitle(self.tr("Delete Project"))
        self.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        self.setButtonText(QtWidgets.QMessageBox.Yes, self.tr("OK"))
        self.setButtonText(QtWidgets.QMessageBox.No, self.tr("Cancel"))
        self.setDefaultButton(QtWidgets.QMessageBox.No)

    def deleteTaskMessage(self, name):
        self.setText(self.tr("Are you sure to delete task: ") + name)
        self.setWindowTitle(self.tr("Delete Task"))
        self.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        self.setButtonText(QtWidgets.QMessageBox.Yes, self.tr("OK"))
        self.setButtonText(QtWidgets.QMessageBox.No, self.tr("Cancel"))
        self.setDefaultButton(QtWidgets.QMessageBox.No)

    def deleteUserMessage(self, name):
        self.setText(self.tr("Are you sure to delete user: ") + name)
        self.setWindowTitle(self.tr("Delete User"))
        self.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        self.setButtonText(QtWidgets.QMessageBox.Yes, self.tr("OK"))
        self.setButtonText(QtWidgets.QMessageBox.No, self.tr("Cancel"))
        self.setDefaultButton(QtWidgets.QMessageBox.No)

    def deleteLauncherMessage(self, name):
        self.setText(self.tr("Are you sure to delete launcher: ") + name)
        self.setWindowTitle(self.tr("Delete Launcher"))
        self.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        self.setButtonText(QtWidgets.QMessageBox.Yes, self.tr("OK"))
        self.setButtonText(QtWidgets.QMessageBox.No, self.tr("Cancel"))
        self.setDefaultButton(QtWidgets.QMessageBox.No)


class BaseGroupBox(QtWidgets.QGroupBox):
    def resizeEvent(self, event):
        super(BaseGroupBox, self).resizeEvent(event)
        internal_layout = self.layout()

        if internal_layout:
            internal_layout.activate()

            for i in range(internal_layout.count()):
                item = internal_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.updateGeometry()


class LauncherWindow(BaseWindow):
    def __init__(self, parent=None):
        super(LauncherWindow, self).__init__(parent)
        self.parent = parent
        self.addMainUI()

    def addMainUI(self):
        layout = QtWidgets.QHBoxLayout()
        self.icon_label = QtWidgets.QLabel()
        self.name_label = QtWidgets.QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setScaledContents(True)
        self.version_comb = BaseComboBox()
        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        layout.addItem(self.hSpacer)
        layout.addWidget(self.version_comb)
        self.setLayout(layout)


class MainWindow(BaseWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.resize(1200, 800)
        mainLayout = QtWidgets.QVBoxLayout()
        self.addHeadUI(mainLayout)
        self.addMainUI(mainLayout)
        self.addInfoUI(mainLayout)
        self.setLayout(mainLayout)
        self.centerActiveScreen()
        self.createTrayIcon()
        self.translateUI()

    def createUI(self, name, parent=None):
        dialog = globals()[name](parent=parent)
        self.darkTitleBar(hwnd=int(dialog.winId()))
        return dialog

    def createTrayIcon(self):
        self.trayIcon = QtWidgets.QSystemTrayIcon(self)
        menu = QtWidgets.QMenu(self)
        self.tray_quit = QtWidgets.QAction(self)
        self.tray_restart = QtWidgets.QAction(self)
        menu.addAction(self.tray_restart)
        menu.addAction(self.tray_quit)
        self.trayIcon.setContextMenu(menu)
        current_dir = os.path.dirname(__file__)
        window_icon = os.path.join(current_dir, "resource", "dark.ico")
        self.trayIcon.setIcon(QtGui.QIcon(window_icon))
        self.trayIcon.setVisible(False)
        self.trayIcon.setVisible(True)
        self.trayIcon.show()

    def addHeadUI(self, parent):
        layout = QtWidgets.QHBoxLayout()
        parent.addLayout(layout)
        self.mode_comb = BaseComboBox()
        self.filter_line = BaseLineEdit()
        self.user_comb = BaseComboBox()

        layout.addWidget(self.mode_comb)
        layout.addItem(self.hSpacer)
        layout.addWidget(self.filter_line)
        layout.addItem(self.hSpacer)
        layout.addWidget(self.user_comb)

    def addInfoUI(self, parent):
        layout = QtWidgets.QHBoxLayout()
        parent.addLayout(layout)
        self.lang_comb = BaseComboBox()
        self.command_label = QtWidgets.QLabel()
        self.command_label.setMinimumWidth(10)
        self.command_label.setAlignment(QtCore.Qt.AlignCenter)
        self.command_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.command_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.option_comb = BaseComboBox()
        layout.addWidget(self.lang_comb)
        layout.addWidget(self.command_label)
        layout.addWidget(self.option_comb)

    def addMainUI(self, parent):
        layout = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        parent.addWidget(layout)
        self.project_gbox = BaseGroupBox()
        project_layout = QtWidgets.QVBoxLayout()
        self.project_gbox.setLayout(project_layout)
        self.project_lw = BaseListWidget()
        project_layout.addWidget(self.project_lw)
        self.task_lw = BaseTreeWidget()
        project_layout.addWidget(self.task_lw)
        layout.addWidget(self.project_gbox)

        self.launcher_gbox = BaseGroupBox()
        launcher_layout = QtWidgets.QVBoxLayout()
        self.launcher_gbox.setLayout(launcher_layout)
        self.launcher_lw = BaseListWidget()
        launcher_layout.addWidget(self.launcher_lw)
        layout.addWidget(self.launcher_gbox)

        config_layout = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.addConfigUI(config_layout)
        layout.addWidget(config_layout)

        self.project_lw.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.project_menu = QtWidgets.QMenu(self)
        self.add_project_action = QtWidgets.QAction(self)
        self.edit_project_action = QtWidgets.QAction(self)
        self.delete_project_action = QtWidgets.QAction(self)
        self.assign_project_action = QtWidgets.QAction(self)
        self.project_menu.addAction(self.add_project_action)
        self.project_menu.addAction(self.edit_project_action)
        self.project_menu.addAction(self.assign_project_action)
        self.project_menu.addAction(self.delete_project_action)

        self.task_lw.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.task_menu = QtWidgets.QMenu(self)
        self.add_task_action = QtWidgets.QAction(self)
        self.edit_task_action = QtWidgets.QAction(self)
        self.delete_task_action = QtWidgets.QAction(self)
        self.add_subtask_action = QtWidgets.QAction(self)
        self.assign_task_action = QtWidgets.QAction(self)
        self.task_menu.addAction(self.add_task_action)
        self.task_menu.addAction(self.edit_task_action)
        self.task_menu.addAction(self.add_subtask_action)
        self.task_menu.addAction(self.assign_task_action)
        self.task_menu.addAction(self.delete_task_action)

        self.launcher_lw.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.launcher_menu = QtWidgets.QMenu(self)
        self.send_command_action = QtWidgets.QAction(self)
        self.add_launcher_action = QtWidgets.QAction(self)
        self.edit_launcher_action = QtWidgets.QAction(self)
        self.copy_launcher_action = QtWidgets.QAction(self)
        self.paste_launcher_action = QtWidgets.QAction(self)
        self.toggle_launcher_action = QtWidgets.QAction(self)
        self.delete_launcher_action = QtWidgets.QAction(self)

        self.launcher_menu.addAction(self.send_command_action)
        self.launcher_menu.addAction(self.add_launcher_action)
        self.launcher_menu.addAction(self.edit_launcher_action)
        self.launcher_menu.addAction(self.copy_launcher_action)
        self.launcher_menu.addAction(self.paste_launcher_action)
        self.launcher_menu.addAction(self.toggle_launcher_action)
        self.launcher_menu.addAction(self.delete_launcher_action)

    def addConfigUI(self, parent):
        self.command_gbox = BaseGroupBox()
        setting_layout = QtWidgets.QVBoxLayout()
        self.cmd_layout = QtWidgets.QVBoxLayout()
        self.command_gbox.setLayout(setting_layout)
        self.config_comb = BaseComboBox()
        self.args_label = QtWidgets.QLabel()
        start_layout = QtWidgets.QHBoxLayout()
        start_layout.addWidget(self.args_label)
        start_layout.addWidget(self.config_comb)

        self.args_edit = BaseTextEdit()
        self.args_edit.setMinimumHeight(50)
        self.cmd_layout.addWidget(self.args_edit)
        self.launch_bt = QtWidgets.QPushButton()
        self.launch_bt.setMinimumHeight(50)
        setting_layout.addLayout(start_layout)
        setting_layout.addLayout(self.cmd_layout)
        setting_layout.addWidget(self.launch_bt)
        parent.addWidget(self.command_gbox)

        self.console_gbox = BaseGroupBox()
        console_layout = QtWidgets.QVBoxLayout()
        self.console_gbox.setLayout(console_layout)
        self.console_gbox.resize(self.size())
        self.console_browser = BaseTextBrowser()
        console_layout.addWidget(self.console_browser)
        parent.addWidget(self.console_gbox)

    def setCombItems(self, comb_obj, *args):
        if comb_obj.count() == 0:
            comb_obj.addItems([self.tr(i) for i in args])
        else:
            for i in range(len(args)):
                comb_obj.setItemText(i, self.tr(args[i]))

    def activated(self):
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    def centerActiveScreen(self):
        mouse_position = QtGui.QCursor.pos()
        screen = QtWidgets.QApplication.screenAt(mouse_position)
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        window_geometry = self.geometry()
        x = screen_geometry.x() + (screen_geometry.width() - window_geometry.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)

    def translateTitle(self):
        status = getattr(self, "online", False)
        status_str = self.tr("Online") if status else self.tr("Offline")
        if os.environ[os.environ.get("LAUNCHER_OFFLINE_NAME")] == "1":
            status_str = self.tr("Local")
        title_string = (" ").join(
            [
                self.tr("Launcher"),
                os.environ.get("LAUNCHER_TAGS", ""),
                status_str,
            ]
        )
        self.setWindowTitle(title_string)

    def translateUI(self):
        self.translateTitle()
        self.tray_quit.setText(self.tr("Quit"))
        self.tray_restart.setText(self.tr("Restart"))
        self.trayIcon.setToolTip(self.tr("Launcher"))
        self.setCombItems(self.mode_comb, "Layout", "Projects", "Launchers")
        self.setCombItems(self.user_comb, "Account", "LogIn", "LogOut", "Manage")
        self.user_comb.view().setRowHidden(3, True)
        self.setCombItems(self.lang_comb, "Languages", "English", "Chinese")
        self.setCombItems(self.option_comb, "Options", "Restart", "Quit")
        self.setCombItems(self.config_comb, "Default", "Local", "Test")
        self.project_gbox.setTitle(self.tr("Projects"))
        self.launcher_gbox.setTitle(self.tr("Launchers"))
        self.command_gbox.setTitle(self.tr("Inputs"))
        self.console_gbox.setTitle(self.tr("Outputs"))
        self.args_label.setText(self.tr("Environment"))
        self.launch_bt.setText(self.tr("Launch"))
        self.upgrade_comb = self.tr("Upgrade")
        self.loading_info = self.tr("Loading")
        self.upgrade_info = self.tr("Launcher found new version, please click Options-Upgrade version!")

        self.add_project_action.setText(self.tr("New Project"))
        self.edit_project_action.setText(self.tr("Edit Project"))
        self.delete_project_action.setText(self.tr("Delete Project"))
        self.assign_project_action.setText(self.tr("Assign Member"))

        self.add_task_action.setText(self.tr("New Task"))
        self.edit_task_action.setText(self.tr("Edit Task"))
        self.add_subtask_action.setText(self.tr("New SubTask"))
        self.delete_task_action.setText(self.tr("Delete Task"))
        self.assign_task_action.setText(self.tr("Assign Member"))

        self.send_command_action.setText(self.tr("Send Command"))
        self.add_launcher_action.setText(self.tr("New Launcher"))
        self.edit_launcher_action.setText(self.tr("Edit Launcher"))
        self.copy_launcher_action.setText(self.tr("Copy Launcher"))
        self.paste_launcher_action.setText(self.tr("Paste Launcher"))
        self.toggle_launcher_action.setText(self.tr("Toggle Launcher"))
        self.delete_launcher_action.setText(self.tr("Delete Launcher"))
