import os
from unittest import TestCase
import subprocess


class TestV100(TestCase):
    def test_version(self):
        result = subprocess.check_output("mechanic --version")
        self.assertEqual("1.0.0", result.decode("utf-8").strip())

    def test_directory_structure(self):
        self.assertTrue(os.path.exists("gen/models"))
        self.assertTrue(os.path.exists("gen/schemas"))
        self.assertTrue(os.path.exists("gen/controllers"))
