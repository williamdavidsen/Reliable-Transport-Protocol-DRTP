import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from filename_utils import get_unique_filename  # noqa: E402


class FilenameUtilsTests(unittest.TestCase):
    def test_returns_original_name_when_file_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                self.assertEqual(get_unique_filename("received.jpg"), "received.jpg")
            finally:
                os.chdir(old_cwd)

    def test_adds_number_when_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                Path("received.jpg").write_text("first")

                self.assertEqual(get_unique_filename("received.jpg"), "received1.jpg")
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
