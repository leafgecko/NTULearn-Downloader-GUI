import json
import os
import sys
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

from ntu_learn_downloader_gui.gui import DownloadDialog

# from PyQt5.QtGui import QApplication
# from PyQt5.QtTest import QTest
# from PyQt5.QtCore import Qt


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
saved_download_dir_2 = json.load(
    open(os.path.join(FIXTURES_PATH, "CE3007_saved_subset_2.json"))
)
predownload_to_download_mapping = json.load(
    open(os.path.join(FIXTURES_PATH, "predownload_to_download_link.json"))
)


def mock_get_file_download_link(BbRouter, predownload_link):
    return predownload_to_download_mapping[predownload_link]


def mock_download(BbRouter, dl_link, full_file_path, callback=None):
    """create an empty file to mock a downloaded file, since we are not testing download progress
    UI elements for now
    """
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
        self.form = DownloadDialog(appctxt, BbRouter, DOWNLOAD_DIR, courses_fixture)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(DOWNLOAD_DIR) and os.path.isdir(DOWNLOAD_DIR):
            # print("removing test generated files")
            shutil.rmtree(DOWNLOAD_DIR)

    def assertDirectoryEqual(self, obj1, obj2):
        """ assert that os.walk return values are the same
        """

        def toSet(obj):
            """convert tuple items that are lists to tuples and then converts to a set
            """
            return set(
                [
                    tuple(tuple(x) if isinstance(x, list) else x for x in tup)
                    for tup in obj
                ]
            )

        self.assertSetEqual(toSet(obj1), toSet(obj2))

    def assertObjEquals(self, rhs, lhs, is_saved=False):
        """utility method to recursively compare serialized folders

        Args:
            rhs (Union[List, Dict]): Folder/File/Recorded Lecture
            lhs (Union[List, Dict]): Folder/File/Recorded Lecture
            is_saved (bool): True if validating saved download_dir, will check for mapping
        """

        if isinstance(lhs, list) and isinstance(rhs, list):
            self.assertEqual(len(lhs), len(rhs))
            for l_folder in lhs:
                r_folder = next(n for n in rhs if n["name"] == l_folder["name"])
                self.assertObjEquals(l_folder, r_folder, is_saved)
            return

        self.assertEqual(rhs["type"], lhs["type"])
        self.assertEqual(rhs["name"], lhs["name"])
        if lhs["type"] == "folder":
            if is_saved:
                self.assertDictEqual(lhs["mapping"], rhs["mapping"])
            self.assertEqual(len(lhs["children"]), len(rhs["children"]))
            for child in lhs["children"]:
                r_child = next(c for c in rhs["children"] if c["name"] == child["name"])
                self.assertObjEquals(child, r_child, is_saved)
        else:
            self.assertEqual(rhs["predownload_link"], lhs["predownload_link"])
            self.assertEqual(rhs["download_link"], lhs["download_link"])
            self.assertEqual(rhs["filename"], lhs["filename"])

    def number_of_visible_items(self):
        """return numner of visible downloadable items
        """

        def traverse(node):
            node_type = node.data(0, Qt.UserRole)["type"]
            if node_type in ["file", "recorded_lecture"]:
                return 0 if node.isHidden() else 1
            else:
                return sum(
                    traverse(node.child(idx)) for idx in range(node.childCount())
                )

        root = self.form.tree.invisibleRootItem()
        return sum(traverse(root.child(idx)) for idx in range(root.childCount()))


@unittest.mock.patch.dict('ntu_learn_downloader_gui.logging.__dict__', MOCK_CONSTANTS)
class TestNewDownloadDialog(TestDownloadDialogBase):
    @patch(
        "ntu_learn_downloader_gui.gui.get_download_dir",
        return_value=get_download_dir_fixture,
    )
    @patch(  # TODO add get_recorded_lecture_download_link
        "ntu_learn_downloader_gui.gui.get_file_download_link",
        side_effect=mock_get_file_download_link,
    )
    @patch("ntu_learn_downloader_gui.gui.download", side_effect=mock_download)
    def test_fresh_init_and_download_all_files(self, m_download, mock2, mock3):
        self.assertEqual(self.form.data, [])

        self.form.handle_reload()
        # QTest.mouseClick(self.form.reloadButton, Qt.LeftButton) # NOTE doesn't work for some reason
        appctxt.app.processEvents(QtCore.QEventLoop.AllEvents, 50)
        # needs to be in a list since self.data is List[Dict]
        self.assertEqual([get_download_dir_fixture], self.form.data)
        self.assertEqual(self.number_of_visible_items(), 1)

        # if press download without selecting any files, then nothing should be downloaded
        QTest.mouseClick(self.form.downloadButton, Qt.LeftButton)
        appctxt.app.processEvents(QtCore.QEventLoop.AllEvents, 50)
        self.assertEqual(m_download.call_count, 0)

        # select all files
        QTest.mouseClick(self.form.selectAllButton, Qt.LeftButton)
        appctxt.app.processEvents()

        # click download files
        QTest.mouseClick(self.form.downloadButton, Qt.LeftButton)
        appctxt.app.processEvents(QtCore.QEventLoop.AllEvents, 50)
        self.assertEqual(m_download.call_count, 1)

        # assert that files have been downloaded
        expected_dir = [
            (DOWNLOAD_DIR + "/.ntu_learn_downloader", (), ()),
            (
                DOWNLOAD_DIR,
                ["19S2-CE3007-DIGITAL SIGNAL PROCESSING", ".ntu_learn_downloader"],
                [],
            ),
            (DOWNLOAD_DIR + "/19S2-CE3007-DIGITAL SIGNAL PROCESSING", ["Content"], []),
            (
                DOWNLOAD_DIR + "/19S2-CE3007-DIGITAL SIGNAL PROCESSING/Content",
                ["Part 1 - Chng Eng Siong"],
                [],
            ),
            (
                DOWNLOAD_DIR
                + "/19S2-CE3007-DIGITAL SIGNAL PROCESSING/Content/Part 1 - Chng Eng Siong",
                ["Content (Lab Tut and Lectures)"],
                [],
            ),
            (
                DOWNLOAD_DIR
                + "/19S2-CE3007-DIGITAL SIGNAL PROCESSING/Content/Part 1 - Chng Eng Siong/Content (Lab Tut and Lectures)",
                [],
                ["Part1_ForStudentsOnly(1).zip"],
            ),
        ]
        curr_dir = list(os.walk(DOWNLOAD_DIR))
        self.assertDirectoryEqual(expected_dir, curr_dir)
        with open(os.path.join(FIXTURES_PATH, "CE3007_download_subset.json")) as f:
            expected_data = json.load(f)
        # form.data is of type List[Dict]
        self.assertEqual(len(self.form.data), 1)
        self.assertObjEquals(self.form.data[0], expected_data)
        self.assertEqual(self.number_of_visible_items(), 0)  # not more visible items


class TestExistingDownloadDialog(TestDownloadDialogBase):
    def setUp(self):
        remove_test_dir()
        # create existing download dir
        Path(STORAGE_DIR).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            os.path.join(FIXTURES_PATH, "CE3007_saved_subset.json"),
            os.path.join(STORAGE_DIR, "download_dir.json"),
        )

    @classmethod
    def tearDownClass(cls):
        remove_test_dir()

    @patch(
        "ntu_learn_downloader_gui.gui.get_download_dir",
        return_value=get_download_dir_fixture_2,
    )
    @patch(  # TODO add get_recorded_lecture_download_link
        "ntu_learn_downloader_gui.gui.get_file_download_link",
        side_effect=mock_get_file_download_link,
    )
    @patch("ntu_learn_downloader_gui.gui.download", side_effect=mock_download)
    def test_existing_init(self, m_download, m_get_file_dl_link, mock3):
        """simulate last refresh was subset and the new refresh returns subset_2
        """
        # start up
        self.form = DownloadDialog(appctxt, BbRouter, DOWNLOAD_DIR, courses_fixture)
        self.assertEqual(self.form.data, saved_download_dir)

        # clicking the reload button
        self.form.handle_reload()
        appctxt.app.processEvents(QtCore.QEventLoop.AllEvents, 50)
        # needs to be in a list since self.data is List[Dict]
        self.assertEqual([get_download_dir_fixture_2], self.form.data)
        self.assertEqual(self.number_of_visible_items(), 9)

        # select all files
        QTest.mouseClick(self.form.selectAllButton, Qt.LeftButton)
        appctxt.app.processEvents()

        # click download files
        QTest.mouseClick(self.form.downloadButton, Qt.LeftButton)
        appctxt.app.processEvents(QtCore.QEventLoop.AllEvents, 50)
        self.assertEqual(m_download.call_count, 9)
        self.assertEqual(m_get_file_dl_link.call_count, 8)
        self.assertEqual(self.number_of_visible_items(), 0)

        # assert that pressing refresh does not lead to duplicate nodes
        self.form.handle_reload()
        numTopLevelItems = self.form.tree.invisibleRootItem().childCount()
        self.assertEqual(numTopLevelItems, 1)

        self.form.close()

        # check that storage has been updated
        saved_data = json.load(open(os.path.join(STORAGE_DIR, "download_dir.json")))
        expected_data = json.load(
            open(os.path.join(FIXTURES_PATH, "CE3007_saved_subset_2.json"))
        )
        self.assertListEqual(saved_data, expected_data)

    @patch(
        "ntu_learn_downloader_gui.gui.get_download_dir",
        return_value=get_download_dir_fixture_2,
    )
    def test_existing_and_ignored_files_dont_appear_on_tree(self, mock1):
        # load previously downloaded files
        prev_downloaded_files = [
            (
                "19S2-CE3007-DIGITAL SIGNAL PROCESSING",
                "Content",
                "Part 1 - Chng Eng Siong",
                "Content (Lab Tut and Lectures)",
                "Part1_ForStudentsOnly(1).zip",
            )
        ]
        ignored_files = [
            (
                "19S2-CE3007-DIGITAL SIGNAL PROCESSING",
                "Lecture Notes for CE3007 (Part II) uploaded",
                "P2-Lecture Week10_ Filter Overview & FIR-Design.pptx",
            )
        ]
        for path_list in prev_downloaded_files:
            full_path = os.path.join(DOWNLOAD_DIR, *path_list)
            target_dir = os.path.dirname(full_path)
            if not os.path.isdir(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            Path(full_path).touch()

        for path_list in ignored_files:
            *path_toks, name = path_list
            target_dir = os.path.join(DOWNLOAD_DIR, *path_toks)
            if not os.path.isdir(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            Path(os.path.join(target_dir, "." + name)).touch()

        # start up
        self.form = DownloadDialog(appctxt, BbRouter, DOWNLOAD_DIR, courses_fixture)
        self.assertEqual(self.form.data, saved_download_dir)

        # clicking the reload button
        self.form.handle_reload()
        appctxt.app.processEvents(QtCore.QEventLoop.AllEvents, 50)
        # needs to be in a list since self.data is List[Dict]
        self.assertEqual([get_download_dir_fixture_2], self.form.data)
        # 9 - 1 (already downloaded) - 1 (ignored) = 8
        self.assertEqual(self.number_of_visible_items(), 8)
