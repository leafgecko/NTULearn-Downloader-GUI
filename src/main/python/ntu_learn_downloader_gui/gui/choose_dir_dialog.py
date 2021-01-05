import ast
from typing import Dict, List, Tuple

from PyQt5 import QtWidgets, uic
from PyQt5.Qt import Qt
from PyQt5.QtCore import QSettings, QThreadPool
from PyQt5.QtGui import QStandardItem, QStandardItemModel

from ntu_learn_downloader import get_courses

from ntu_learn_downloader_gui.QtThreading import Worker
from ntu_learn_downloader_gui.logging import Logger
from ntu_learn_downloader_gui.gui.download_dialog import DownloadDialog


class ChooseDirDialog(QtWidgets.QMainWindow):
    def __init__(self, appctxt, BbRouter):
        super(ChooseDirDialog, self).__init__()
        uic.loadUi(appctxt.get_resource("layouts/chooseDir.ui"), self)

        self.appctxt = appctxt
        self.BbRouter = BbRouter
        self.settings = QSettings("NTULearnDownloader", "GUI")

        self.defaultDirCheckBox = self.findChild(
            QtWidgets.QCheckBox, "defaultDirCheckBox"
        )
        self.defaultModulesCheckBox = self.findChild(
            QtWidgets.QCheckBox, "defaultModulesCheckBox"
        )
        self.downloadDirLine = self.findChild(QtWidgets.QLineEdit, "downloadDir")
        self.chooseDirButton = self.findChild(QtWidgets.QPushButton, "chooseDirButton")
        self.chooseDirButton.clicked.connect(self.choose_dir_handler)

        self.nextButton = self.findChild(QtWidgets.QPushButton, "nextButton")
        self.nextButton.clicked.connect(self.next_handler)
        # disable until download dir and modules are set
        self.nextButton.setEnabled(False)

        # load default download directory from settings if possible
        if self.settings.value("default_download_dir"):
            self.downloadDirLine.setText(self.settings.value("default_download_dir"))
            self.defaultDirCheckBox.setChecked(True)
        else:
            self.defaultDirCheckBox.setChecked(False)

        # load modules list in the background
        self.listModel = QStandardItemModel()
        self.listView = self.findChild(QtWidgets.QListView, "listView")
        self.threadPool = QThreadPool()

        worker = Worker(lambda progress_callback: sorted(get_courses(self.BbRouter)))
        worker.signals.result.connect(self.display_modules_list)
        self.threadPool.start(worker)

        self.show()

    def display_modules_list(self, modules: List[Tuple[str, str]]):
        default_modules_str = self.settings.value("default_modules")
        if default_modules_str:
            default_modules = ast.literal_eval(default_modules_str)
        else:
            default_modules = None

        for name, module_id in modules:
            item = QStandardItem(name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
            item.setData({"name": name, "module_id": module_id}, Qt.UserRole)
            # if saved selected modules, only check those, else check all
            item.setCheckable(True)
            if default_modules:
                item.setCheckState(
                    Qt.Checked if module_id in default_modules else Qt.Unchecked
                )
            else:
                item.setCheckState(Qt.Checked)
            self.listModel.appendRow(item)
        self.listView.setModel(self.listModel)

        # enable next butten if download dir is set
        if self.downloadDirLine.text():
            self.nextButton.setEnabled(True)

    def choose_dir_handler(self):
        download_dir = str(
            QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        )

        if self.defaultDirCheckBox.isChecked():
            self.settings.setValue("default_download_dir", download_dir)

        self.downloadDirLine.setText(download_dir)
        # enable next button if listModel is already loaded
        if self.listModel.rowCount():
            self.nextButton.setEnabled(True)

    def next_handler(self):
        selected_modules = []
        for idx in range(self.listModel.rowCount()):
            item = self.listModel.item(idx)
            if item.checkState() == Qt.Checked:
                data = item.data(Qt.UserRole)
                selected_modules.append((data["name"], data["module_id"]))

        if self.defaultModulesCheckBox.isChecked():
            self.settings.setValue(
                "default_modules", str([mod_id for _name, mod_id in selected_modules])
            )

        self.main = DownloadDialog(
            self.appctxt, self.BbRouter, self.downloadDirLine.text(), selected_modules, self.__class__
        )
        self.main.show()
        self.close()
