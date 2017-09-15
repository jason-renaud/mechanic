import os
from unittest import TestCase
from mechanic.mechanic.src.converter import Merger


def get_filename(path):
    dir = os.path.dirname(__file__)
    return os.path.join(dir, path)


class MergerTest(TestCase):
    def setUp(self):
        self.merger = Merger(get_filename("test_specs/split/petstore-split.json"), "mechanic.json")

    def test_merge(self):
        self.merger = Merger(get_filename("test_specs/split/petstore-split.json"), "mechanic.json")
        self.merger.merge()

    def test_merge_yaml(self):
        self.merger = Merger(get_filename("test_specs/split/petstore-split.json"), "mechanic.yaml")
        self.merger.merge()
