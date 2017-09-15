from unittest import TestCase
from mechanic.mechanic.converter import Merger


class MergerTest(TestCase):
    def setUp(self):
        self.merger = Merger("test_specs/split/petstore-split.json", "mechanic.json")

    def test_merge(self):
        self.merger = Merger("test_specs/split/petstore-split.json", "mechanic.json")
        self.merger.merge()

    def test_merge_yaml(self):
        self.merger = Merger("test_specs/split/petstore-split.json", "mechanic.yaml")
        self.merger.merge()
