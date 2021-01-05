from PyQt5 import QtWidgets
from fbs_runtime.application_context.PyQt5 import ApplicationContext
import sys
from ntu_learn_downloader_gui.gui.login_dialog import LoginDialog

if __name__ == "__main__":
    appctxt = ApplicationContext()
    window = LoginDialog(appctxt)
    exit_code = appctxt.app.exec_()
    sys.exit(exit_code)
