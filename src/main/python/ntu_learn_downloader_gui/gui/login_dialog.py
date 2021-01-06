from PyQt5.Qt import Qt
from PyQt5 import QtGui, QtWidgets, uic, QtCore
from PyQt5.QtCore import QThreadPool
from PyQt5.QtGui import QCursor

from ntu_learn_downloader import authenticate
from ntu_learn_downloader_gui.gui.choose_dir_dialog import ChooseDirDialog
from ntu_learn_downloader_gui.QtThreading import Worker
from ntu_learn_downloader_gui.networking import get_latest_version
from ntu_learn_downloader_gui.structs import VersionResult

from typing import Optional

def get_app_icon(appctxt):
    return QtGui.QIcon(appctxt.get_resource("icon.png"))


def formatted_text(text: str) -> str:
    return f"<font color='blue'><u>{text}</u></font>"

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, appctxt):
        super(LoginDialog, self).__init__()
        uic.loadUi(appctxt.get_resource("layouts/login.ui"), self)

        self.appctxt = appctxt

        self.loginButton = self.findChild(QtWidgets.QPushButton, "loginButton")
        self.loginButton.clicked.connect(self.handle_login)
        self.setWindowIcon(get_app_icon(self.appctxt))
        self.setWindowTitle("NTU Learn Downloader")

        self.latest_version: Optional[VersionResult] = None
        self.updateLabel = self.findChild(QtWidgets.QLabel, 'updateLabel')
        self.updateLabel.setText("Fetching latest version")

        # get latest version in the background 
        self.threadPool = QThreadPool()
        self.version = self.appctxt.build_settings['version']
        test_mode = self.appctxt.build_settings.get('test_mode', False)
        worker = Worker(lambda progress_callback: get_latest_version(self.version, test_mode))
        worker.signals.result.connect(self.display_latest_version)
        self.threadPool.start(worker)

        self.show()

    def display_latest_version(self, latest_version: Optional[VersionResult]):
        if latest_version is None:
            self.updateLabel.setText("Unable to fetch lateset version")
            return
        self.latest_version = latest_version
        if tuple([int(x) for x in self.version.split('.')]) == latest_version.version:
            self.updateLabel.setText("")
        else:
            self.updateLabel.setText(formatted_text("Update available"))
            self.updateLabel.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
            self.updateLabel.mousePressEvent = self.handle_click_update_available


    def handle_login(self):
        username = self.Username.text()
        password = self.Password.text()

        try:
            BbRouter = authenticate(username, password)
            self.main = ChooseDirDialog(self.appctxt, BbRouter)
            self.main.show()
            self.close()
        except Exception:
            alert = QtWidgets.QMessageBox()
            alert.setText("Authentication failed")
            alert.exec_()

    def handle_click_update_available(self, event):
        if self.latest_version is None:
            return
        body = "<p>" + '</p><p>'.join(self.latest_version.content.split('\n')) + "</p>"
        text = f"""
        <center>
        <h1>{self.latest_version.title}</h1>
        </center>
        {body}
        <p><a href={self.latest_version.link}>Download here</a></p>
        """
        alert = QtWidgets.QMessageBox()
        alert.setText(text)
        alert.exec_()