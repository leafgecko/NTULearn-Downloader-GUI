import ast
import os
import sys
from typing import Dict, List, Tuple
import traceback

from ntu_learn_downloader import (
    Storage,
    authenticate,
    get_courses,
    get_download_dir,
    get_file_download_link,
    get_recorded_lecture_download_link,
)
from ntu_learn_downloader.utils import (
    download,
    get_filename_from_url,
    sanitise_filename,
    create_dummy_file,
    dummy_file_exists,
    convert_size,
)
from PyQt5 import QtGui, QtWidgets, uic
from PyQt5.Qt import Qt
from PyQt5.QtCore import QSettings, QThreadPool
from PyQt5.QtGui import QStandardItem

from ntu_learn_downloader_gui.QtThreading import Worker
from ntu_learn_downloader_gui.logging import Logger
# from ntu_learn_downloader_gui.gui import ChooseDirDialog


class DownloadDialog(QtWidgets.QDialog):
    def __init__(self, appctxt, BbRouter, download_dir, modules: List[Tuple[str, str]], last_dialog: QtWidgets.QDialog):
        """Download Dialog for selecting files to download/ignore

        Args:
            appctxt (ApplicationContext): fbs application context
            BbRouter (str): authentication token
            download_dir (str): download directory
            modules (List[Tuple[str, str]]): list of course name and course id tuples
            last_dialog (QtWidgets.QDialog): last dialog to return on back button press
        """
        super(DownloadDialog, self).__init__()
        uic.loadUi(appctxt.get_resource("layouts/download.ui"), self)

        self.logger = Logger(appctxt)

        self.appctxt = appctxt
        self.BbRouter = BbRouter
        self.download_dir = download_dir
        self.modules = modules
        self.last_dialog = last_dialog
        dirLabel = self.findChild(QtWidgets.QLabel, "downloadDirLabel")
        dirLabel.setText("Downloading to: {}".format(download_dir))

        # load icons
        backIcon = QtGui.QIcon(appctxt.get_resource("images/back.png"))
        self.folderIcon = QtGui.QIcon(appctxt.get_resource("images/folder.png"))
        self.videoIcon = QtGui.QIcon(appctxt.get_resource("images/video.png"))
        self.fileIcon = QtGui.QIcon(appctxt.get_resource("images/file.png"))

        # load buttons
        self.backButton = self.findChild(QtWidgets.QToolButton, "backButton")
        self.backButton.setIcon(backIcon)
        self.ignoreButton = self.findChild(QtWidgets.QPushButton, "ignoreButton")
        self.downloadButton = self.findChild(QtWidgets.QPushButton, "downloadButton")
        self.selectAllButton = self.findChild(QtWidgets.QPushButton, "selectAllButton")
        self.deselectAllButton = self.findChild(
            QtWidgets.QPushButton, "deselectAllButton"
        )
        self.reloadButton = self.findChild(QtWidgets.QPushButton, "reloadButton")
        self.selectFilesButton = self.findChild(
            QtWidgets.QPushButton, "selectFilesButton"
        )
        self.selectVideosButton = self.findChild(
            QtWidgets.QPushButton, "selectVideosButton"
        )

        self.backButton.clicked.connect(self.handle_back)
        self.selectAllButton.clicked.connect(self.handle_select_all)
        self.deselectAllButton.clicked.connect(self.handle_unselect_all)
        self.ignoreButton.clicked.connect(self.handle_ignore)
        self.downloadButton.clicked.connect(self.handle_download)
        self.reloadButton.clicked.connect(self.handle_reload)
        self.selectFilesButton.clicked.connect(self.handle_select_files)
        self.selectVideosButton.clicked.connect(self.handle_select_videos)

        self.progressBar = self.findChild(QtWidgets.QProgressBar, "progressBar")
        self.progressBar.setValue(0)

        self.downloadProgressText = self.findChild(
            QtWidgets.QLabel, "downloadProgressText"
        )
        self.downloadProgressText.setText("Click download to start downloading files")

        # get download dir from NTU Learn and load tree
        self.threadPool = QThreadPool()
        self.tree = self.findChild(QtWidgets.QTreeWidget, "treeWidget")

        # NOTE do not show tree even though we have data as we want the user to
        # act on fresh download data
        self.storage = Storage(download_dir)
        self.data = self.storage.download_dir

        # add loading text
        node = QtWidgets.QTreeWidgetItem(self.tree)
        node.setText(0, "Click Reload to pull data from NTU Learn")

        self.show()

    def closeEvent(self, event):
        self.storage.save_download_dir(self.data)

    def handle_back(self):
        # self.main = ChooseDirDialog(self.appctxt, self.BbRouter)
        self.main = self.last_dialog(self.appctxt, self.BbRouter)
        self.main.show()
        self.close()

    def handle_select_files(self):
        self.__handle_select_type(obj_type="file")

    def handle_select_videos(self):
        self.__handle_select_type(obj_type="recorded_lecture")

    def handle_reload(self):
        """
        1. disable reload button until done fetching data
        2. clear tree and add Loading text node
        3. in a separate thread make ntu_learn_downloader API call
        4. when done update UI
        """
        self.reloadButton.setEnabled(False)
        self.__clear_tree()
        node = QtWidgets.QTreeWidgetItem(self.tree)
        node.setText(0, "Loading...")

        def get_data(progress_callback) -> List[Dict]:
            """Get download dir from NTU Learn, WARNING slow, should not be run in main thread
            Returns list of dicts
            """
            result = [
                get_download_dir(self.BbRouter, name, course_id)
                for name, course_id in self.modules
            ]
            return result

        def save_data(result):
            self.storage.merge_download_dir(result)
            self.data = result
            self.data_to_tree()

        def finished():
            self.reloadButton.setEnabled(True)

        worker = Worker(get_data)
        worker.signals.result.connect(save_data)
        worker.signals.finished.connect(finished)

        self.threadPool.start(worker)

    def handle_select_all(self):
        def traverse(node):
            node.setCheckState(0, Qt.Checked)
            for index in range(node.childCount()):
                traverse(node.child(index))

        root = self.tree.invisibleRootItem()
        traverse(root)

    def handle_unselect_all(self):
        def traverse(node):
            node.setCheckState(0, Qt.Unchecked)
            for index in range(node.childCount()):
                traverse(node.child(index))

        root = self.tree.invisibleRootItem()
        traverse(root)

    def handle_ignore(self):
        """Dummy files are in the format: .{name} 
        Do not have to get the actual filename
        """
        alert = QtWidgets.QMessageBox()
        alert.setWindowTitle("Ignore selected files")
        alert.setIcon(QtWidgets.QMessageBox.Warning)
        alert.setText(
            "You are about to ignore some files. This will generate hidden files in your download directory"
        )
        alert.setDetailedText(
            "This will generate hidden files in the download directory so that ignored "
            "files will not appear the menu in the future.\n"
            "To undo, you need to enable show hidden files in your file "
            "explorer and remove the files you want to download. E.g. if you want to download Tut_4, look for .Tut_4 and remove it"
        )
        alert.setStandardButtons(
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        retval = alert.exec_()
        if retval == QtWidgets.QMessageBox.Ok:
            path_and_nodes = self.get_paths_and_selected_nodes()
            for path, node in path_and_nodes:
                node_data = node.data(0, Qt.UserRole)
                create_dummy_file(path, sanitise_filename(node_data["name"]))
            self.downloadProgressText.setText(
                "Ignored {} files and recorded lectures".format(len(path_and_nodes))
            )
        if retval == QtWidgets.QMessageBox.Cancel:
            pass

    def handle_error(self, full_file_name: str, trace: str):
        """Create a MessageBox with a trace dump and log error to server
        """
        try:
            self.logger.log_error(trace)
        except Exception:
            pass

        alert = QtWidgets.QMessageBox()
        alert.setWindowTitle("Failed to get download link")
        alert.setText(
            "Failed to get download link for: {}. Please try again later. ".format(
                full_file_name
            )
            + "If the problem persists, please send the trace log below to us."
        )
        nonBoldFont = QtGui.QFont()
        nonBoldFont.setBold(False)
        alert.setDetailedText(trace)
        alert.setFont(nonBoldFont)
        alert.exec_()

    def handle_download(self):
        """
        1. Get list of files to download
        2. Map predownload links to download links
        3. Download files async in background
        4. update tree with downloaded items removed
        """
        self.setDownloadIgnoreButtonsEnabled(False)
        self.downloadProgressText.setText("Getting items to download...")
        paths_and_nodes = self.get_paths_and_selected_nodes()
        numFiles = len(paths_and_nodes)
        self.progressBar.setRange(0, numFiles)

        def download_from_nodes(progress_callback):
            """Return tuple (files downloaded, files skipped, download_links)
            """

            numDownloaded, numSkipped = 0, 0
            data_deltas = []

            for idx, (path, node) in enumerate(paths_and_nodes):
                node_data = node.data(0, Qt.UserRole)
                node_type = node_data["type"]

                save_flag = False
                # load the download link and file name from API if needed
                if node_data.get("download_link") is None:
                    save_flag = True
                    try:
                        if node_type == "file":
                            download_link = get_file_download_link(
                                self.BbRouter, node_data["predownload_link"]
                            )
                            filename = get_filename_from_url(download_link)
                        elif node_type == "recorded_lecture":
                            download_link = get_recorded_lecture_download_link(
                                self.BbRouter, node_data["predownload_link"]
                            )
                            filename = node_data["name"] + ".mp4"
                    except Exception:
                        trace = traceback.format_exc()
                        progress_callback.emit(
                            (idx + 1, node_data["name"], False, None, None, trace)
                        )
                        data_deltas.append(None)
                        continue
                else:
                    download_link = node_data.get("download_link")
                    filename = node_data.get("filename")

                full_file_path = os.path.join(path, sanitise_filename(filename))
                if os.path.exists(full_file_path):
                    numSkipped += 1
                    progress_callback.emit((idx + 1, filename, False, None, None, None))
                else:
                    try:
                        download(
                            self.BbRouter,
                            download_link,
                            full_file_path,
                            lambda bytes_downloaded, total_content_length: progress_callback.emit(
                                (
                                    idx + 1,
                                    filename,
                                    True,
                                    bytes_downloaded,
                                    total_content_length,
                                    None,
                                )
                            ),
                        )
                    except Exception:
                        numSkipped += 1
                        trace = traceback.format_exc()
                        progress_callback.emit(
                            (idx + 1, filename, False, None, None, trace)
                        )

                numDownloaded += 1
                data_deltas.append((download_link, filename) if save_flag else None)

            return (numDownloaded, numSkipped, data_deltas)

        def progress_fn(data):
            """
            Progress text format:
            [overall_progress] [prefix] [filename] [current_file_progress]
            """
            numDownloaded, filename, was_last_downloaded, bytes_downloaded, total_content_length, stack_trace = (
                data
            )


            overall_progress = "({}/{})".format(numDownloaded, numFiles)
            prefix = "Downloading" if was_last_downloaded else "Skipping"
            current_file_progress = ""
            if was_last_downloaded:
                current_file_progress = (
                    "({}/{})".format(
                        convert_size(bytes_downloaded),
                        convert_size(total_content_length),
                    )
                    if total_content_length
                    else "({})".format(convert_size(bytes_downloaded))
                )

            text = "{} {} {} {}".format(
                overall_progress, prefix, filename, current_file_progress
            )
            self.downloadProgressText.setText(text)
            self.progressBar.setValue(numDownloaded)

            if stack_trace:
                self.handle_error(filename, stack_trace)

        def display_result_and_update_node_data(result):
            self.setDownloadIgnoreButtonsEnabled(True)
            numDownloaded, numSkipped, data_deltas = result
            self.downloadProgressText.setText(
                "Completed. Downloaded {} files, skipped {} files".format(
                    numDownloaded, numSkipped
                )
            )

            for delta, (_path, node) in zip(data_deltas, paths_and_nodes):
                if delta is None:
                    continue
                download_link, filename = delta
                node_data = node.data(0, Qt.UserRole)
                node_data["download_link"] = download_link
                node_data["filename"] = filename
                node.setData(0, Qt.UserRole, node_data)

            try:
                self.logger.log_successful_download(numDownloaded)
            except Exception:
                pass

        worker = Worker(download_from_nodes)
        worker.signals.result.connect(display_result_and_update_node_data)
        worker.signals.finished.connect(self.reload_tree)
        worker.signals.progress.connect(progress_fn)

        self.threadPool.start(worker)

    def reload_tree(self):
        """update self.data based on new tree node data
        """
        self.tree_to_data()
        self.__clear_tree()
        self.data_to_tree()

    def tree_to_data(self):
        """traverse tree to convert it to data and update self.data
        """

        def traverse(node):
            node_data = node.data(0, Qt.UserRole)
            node_type = node_data["type"]

            if node_type == "folder":
                node_data["children"] = [
                    traverse(node.child(idx)) for idx in range(node.childCount())
                ]
            return node_data

        root = self.tree.invisibleRootItem()
        self.data = [traverse(root.child(idx)) for idx in range(root.childCount())]

    def data_to_tree(self):
        """traverse self.data and generate tree list widget. Files/videos that have already downloaded
        will not be displayed
        Raises:
            Exception: thrown on unknown data type
        """
        if self.data is None:
            print("Warning, there is not loaded data, was get_data() not called?")
            return
        self.__clear_tree()

        def traverse(data, parent, path):
            """recursively traverse NTU Learn data and render all file/video nodes, if the 
            file/video already exists, set the node as hidden
            """
            node = QtWidgets.QTreeWidgetItem(parent)
            # save relevant data fields into node.data
            node_data = {"name": data["name"], "type": data["type"]}

            data_type = data["type"]
            if data_type == "folder":
                node.setIcon(0, self.folderIcon)
                node.setFlags(node.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
                next_path = os.path.join(path, sanitise_filename(data["name"]), "")
                for child in data["children"]:
                    traverse(child, node, next_path)
            elif data_type == "file" or data_type == "recorded_lecture":
                # add file/video attributes
                node_data["predownload_link"] = data["predownload_link"]
                node_data["download_link"] = data.get("download_link")
                node_data["filename"] = data.get("filename")

                # ignore file if dummy file is present
                is_dummy_file_present = dummy_file_exists(
                    path, sanitise_filename(node_data["name"])
                )
                is_file_present = node_data["filename"] and os.path.exists(
                    os.path.join(path, sanitise_filename(node_data["filename"]))
                )

                if is_dummy_file_present or is_file_present:
                    node.setHidden(True)

                node.setIcon(
                    0, self.fileIcon if data_type == "file" else self.videoIcon
                )
                node.setFlags(node.flags() | Qt.ItemIsUserCheckable)
            else:
                raise Exception("unknown type", data_type)
            node.setText(0, data["name"])
            node.setCheckState(0, Qt.Unchecked)
            node.setData(0, Qt.UserRole, node_data)

        # iterate data (list)
        for item in self.data:
            traverse(item, self.tree, self.download_dir)

    def get_paths_and_selected_nodes(
        self, files=True, videos=False
    ) -> List[Tuple[str, QtWidgets.QTreeWidgetItem]]:
        """returns lists of QTreeWidgetItem (nodes) that correspond to files/videos to download/ignore

        Args:
            files (bool, optional): whether to download files. Defaults to True.
            videos (bool, optional): whether to download videos. Defaults to False.

        Returns:
           List[Tuple[str, QtWidgets.QTreeWidgetItem]]: list of path, tree nodes tuples
        
        Note:
            Not possible to project down to filename, download link as loading of the downloading 
            link is very slow (3s) for lecture videos
        """

        result = []

        def traverse(node, path):
            if node.checkState(0) == Qt.Unchecked or node.isHidden():
                return

            node_data = node.data(0, Qt.UserRole)
            node_type = node_data["type"]
            if node_type == "file" or node_type == "recorded_lecture":
                result.append((path, node))
            else:
                next_path = os.path.join(path, sanitise_filename(node_data["name"]))
                for index in range(node.childCount()):
                    traverse(node.child(index), next_path)

        root = self.tree.invisibleRootItem()
        for idx in range(root.childCount()):
            traverse(root.child(idx), self.download_dir)

        return result

    def setDownloadIgnoreButtonsEnabled(self, flag: bool):
        self.downloadButton.setEnabled(flag)
        self.ignoreButton.setEnabled(flag)

    def __clear_tree(self):
        self.tree.clear()

    def __handle_select_type(self, obj_type: str):
        assert obj_type in [
            "file",
            "recorded_lecture",
        ], "unexpected obj_type: {}".format(obj_type)

        def is_same_type(node, obj_type: str) -> bool:
            node_data = node.data(0, Qt.UserRole)
            node_type = isinstance(node_data, dict) and node_data["type"]
            node_name = isinstance(node_data, dict) and node_data["name"]
            if obj_type == "file":
                return (
                    node_type == obj_type
                    and isinstance(node_name, str)
                    and not node_name.endswith(".mp4")
                )
            else:
                return node_type == "recorded_lecture" or (
                    isinstance(node_name, str) and node_name.endswith(".mp4")
                )

        def traverse(node):
            if is_same_type(node, obj_type):
                node.setCheckState(0, Qt.Checked)
            else:
                for index in range(node.childCount()):
                    traverse(node.child(index))

        root = self.tree.invisibleRootItem()
        traverse(root)
