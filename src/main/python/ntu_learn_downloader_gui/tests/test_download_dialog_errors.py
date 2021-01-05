"""
Testing unhappy paths
"""
import json
import os
import sys
import time
import unittest
from unittest.mock import patch
import shutil
from pathlib import Path

import ntu_learn_downloader
from ntu_learn_downloader_gui.tests.mock_server import MOCK_CONSTANTS

from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt

from ntu_learn_downloader_gui.gui.download_dialog import DownloadDialog
from ntu_learn_downloader_gui.gui.choose_dir_dialog import ChooseDirDialog


FIXTURES_PATH = os.path.join(os.path.dirname(__file__), "fixtures")
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "temp")
STORAGE_DIR = os.path.join(DOWNLOAD_DIR, ".ntu_learn_downloader", "")

courses_fixture = [("19S2-CE3007-DIGITAL SIGNAL PROCESSING", "PLACEHOLDER")]
get_download_dir_fixture = json.load(
    open(os.path.join(FIXTURES_PATH, "CE3007_predownload_subset.json"))
)
saved_download_dir = json.load(
    open(os.path.join(FIXTURES_PATH, "CE3007_saved_subset.json"))
)
get_download_dir_fixture_2 = json.load(
    open(os.path.join(FIXTURES_PATH, "CE3007_predownload_subset_2.json"))
)
predownload_to_download_mapping = json.load(
    open(os.path.join(FIXTURES_PATH, "predownload_to_download_link.json"))
)


def mock_get_file_download_link_with_errors(error_links_w_fails={}):
    error_counter = error_links_w_fails.copy()
    def get_file_download_link(BbRouter, predownload_link):
        if predownload_link in error_counter:
            if error_counter[predownload_link] > 0:
                error_counter[predownload_link] -= 1
                raise ValueError("Failed to get download link")
        return predownload_to_download_mapping[predownload_link]
    return get_file_download_link


def mock_download(BbRouter, dl_link, full_file_path, callback=None):
    """create an empty file to mock a downloaded file, since we are not testing download progress
    UI elements for now
    """
    print("mock_download", dl_link, full_file_path)
    dir_path = os.path.dirname(full_file_path)
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    Path(full_file_path).touch()


# app = QtWidgets.QApplication(sys.argv)
appctxt = ApplicationContext()
BbRouter = "PLACEHOLDER"


def remove_test_dir():
    if os.path.exists(DOWNLOAD_DIR) and os.path.isdir(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)


@unittest.mock.patch.dict('ntu_learn_downloader_gui.logging.__dict__', MOCK_CONSTANTS)
class TestDownloadDialogBase(unittest.TestCase):
    def setUp(self):
        remove_test_dir()
        self.form = DownloadDialog(appctxt, BbRouter, DOWNLOAD_DIR, courses_fixture, ChooseDirDialog)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(DOWNLOAD_DIR) and os.path.isdir(DOWNLOAD_DIR):
            # print("removing test generated files")
            shutil.rmtree(DOWNLOAD_DIR)

    def get_visible_items(self):
        """return numner of visible downloadable items
        """

        items = []
        def traverse(node):
            node_type = node.data(0, Qt.UserRole)["type"]
            node_name = node.data(0, Qt.UserRole)["name"]
            if node_type in ["file", "recorded_lecture"] and not node.isHidden():
                items.append(node_name)
            else:
                for idx in range(node.childCount()):
                    traverse(node.child(idx)) 

        root = self.form.tree.invisibleRootItem()
        for idx in range(root.childCount()):
            traverse(root.child(idx))
 
        return items


@unittest.mock.patch.dict('ntu_learn_downloader_gui.logging.__dict__', MOCK_CONSTANTS)
class TestNewDownloadDialog(TestDownloadDialogBase):
    @patch("ntu_learn_downloader_gui.gui.download_dialog.DownloadDialog.handle_error")
    @patch(
        "ntu_learn_downloader_gui.gui.download_dialog.get_download_dir",
        return_value=get_download_dir_fixture_2,
    )
    @patch(  
        "ntu_learn_downloader_gui.gui.download_dialog.get_file_download_link",
        side_effect=mock_get_file_download_link_with_errors(error_links_w_fails={'https://ntulearn.ntu.edu.sg/bbcswebdav/pid-2015986-dt-content-rid-10582032_1/xid-10582032_1': 1}),
    )
    @patch("ntu_learn_downloader_gui.gui.download_dialog.download", side_effect=mock_download)
    def test_get_download_link_failure_doesnt_hang_download(self, m_download, m_get_file_dl_link, mock3, mock_handle_error):
        self.assertEqual(self.form.data, [])

        self.form.handle_reload()
        # QTest.mouseClick(self.form.reloadButton, Qt.LeftButton) # NOTE doesn't work for some reason
        appctxt.app.processEvents(QtCore.QEventLoop.AllEvents, 500)
        # needs to be in a list since self.data is List[Dict]
        self.assertEqual([get_download_dir_fixture_2], self.form.data)
        self.assertEqual(len(self.get_visible_items()), 9)

        # select all files
        QTest.mouseClick(self.form.selectAllButton, Qt.LeftButton)
        appctxt.app.processEvents()

        # click download files
        QTest.mouseClick(self.form.downloadButton, Qt.LeftButton)
        appctxt.app.processEvents(QtCore.QEventLoop.AllEvents, 500)

        # 9 - 1 = 8 since 1 download failed
        self.assertEqual(m_download.call_count, 8)
        self.assertEqual(m_get_file_dl_link.call_count, 9)
        # 1 solo file that failed to download
        self.assertListEqual(['P2-Lecture Week9_UpDownSampling.pptx'], self.get_visible_items())

        mock_handle_error.assert_called_once()

        # try to download file again...
        # select all files
        QTest.mouseClick(self.form.selectAllButton, Qt.LeftButton)
        appctxt.app.processEvents()

        # click download files
        QTest.mouseClick(self.form.downloadButton, Qt.LeftButton)
        appctxt.app.processEvents(QtCore.QEventLoop.AllEvents, 500)

        mock_handle_error.assert_called_once()
        self.assertEqual(m_get_file_dl_link.call_count, 10)
        self.assertEqual(len(self.get_visible_items()), 0)
        self.assertEqual(m_download.call_count, 9) 

