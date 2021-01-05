from PyQt5 import QtGui, QtWidgets, uic

from ntu_learn_downloader import authenticate
from ntu_learn_downloader_gui.gui.choose_dir_dialog import ChooseDirDialog


def get_app_icon(appctxt):
    return QtGui.QIcon(appctxt.get_resource("icon.png"))


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, appctxt):
        super(LoginDialog, self).__init__()
        # uic.loadUi(os.path.join(LAYOUTS_PATH, "login.ui"), self)
        uic.loadUi(appctxt.get_resource("layouts/login.ui"), self)

        self.appctxt = appctxt
        self.loginButton = self.findChild(QtWidgets.QPushButton, "loginButton")
        self.loginButton.clicked.connect(self.handle_login)
        self.setWindowIcon(get_app_icon(self.appctxt))
        self.setWindowTitle("NTU Learn Downloader")

        self.show()

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
