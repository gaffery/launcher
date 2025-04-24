import os
import sys
import json
from PySide2 import QtCore, QtWidgets, QtNetwork

from . import view, model, cons


def enableHighDpi():
    if hasattr(QtCore.Qt, "AA_EnableHighDpiScaling"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class InstanceApplication(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super(InstanceApplication, self).__init__(*args, **kwargs)
        self.local_socket_name = "LauncherInstance"

        self._out_socket = QtNetwork.QLocalSocket()
        self._out_socket.connectToServer(self.local_socket_name)
        if self._out_socket.waitForConnected(1000):
            self._send_message_to_existing_instance()
            sys.exit(0)

        self.server = self._create_local_server()

    def _create_local_server(self):
        server = QtNetwork.QLocalServer(self)
        QtNetwork.QLocalServer.removeServer(self.local_socket_name)
        if not server.listen(self.local_socket_name):
            return None
        server.newConnection.connect(self._handle_new_connection)
        return server

    def _send_message_to_existing_instance(self):
        env_data = json.dumps(dict(os.environ)).encode('utf-8')
        self._out_socket.write(env_data)
        self._out_socket.waitForBytesWritten()

    def _handle_new_connection(self):
        socket = self.server.nextPendingConnection()
        if socket:
            socket.waitForReadyRead(1000)
            try:
                data = socket.readAll().data()
                if data:
                    new_env = json.loads(data.decode('utf-8'))
                    os.environ.update(new_env)
            except Exception:
                pass
            self._activate_window()

    def _activate_window(self):
        for widget in self.topLevelWidgets():
            if widget.objectName() == "MainWindow":
                widget.darkTitleBar()
                widget.centerActiveScreen()
                if widget.isMinimized():
                    widget.showNormal()
                if widget.isHidden():
                    widget.show()
                widget.raise_()
                widget.activateWindow()

    def cleanup(self):
        if self.server:
            self.server.close()
            QtNetwork.QLocalServer.removeServer(self.local_socket_name)
        if self._out_socket:
            self._out_socket.abort()
            self._out_socket.close()


def main():
    enableHighDpi()
    app = InstanceApplication(sys.argv)
    app.aboutToQuit.connect(app.cleanup)
    main_window = view.MainWindow()
    main_window.setObjectName("MainWindow")
    main_cons = cons.MainCons(main_window, model.MainModel())
    main_cons.initialize()
    main_window.show()
    main_window.raise_()
    main_window.activateWindow()
    app.setQuitOnLastWindowClosed(False)
    app.setActiveWindow(main_window)
    sys.exit(app.exec_())