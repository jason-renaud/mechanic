from unittest import TestCase
from mechanic.mechanic.converter import Converter


class ConverterTest(TestCase):
    def setUp(self):
        self.converter = Converter("test_specs/petstore.json", "mech-petstore.json")
        # self.converter = Converter("/home/zackschrag/cmdb/resources/master.json", "mech-cmdb.json")

    def test_convert_invalid_version(self):
        converter = Converter("test_specs/invalid/invalid_version.json", "")
        self.assertRaises(SyntaxError, converter.convert)

    def test_convert_no_paths_obj(self):
        converter = Converter("test_specs/invalid/no_paths.json", "")
        self.assertRaises(SyntaxError, converter.convert)

    def test_convert_no_servers_obj(self):
        converter = Converter("test_specs/invalid/no_servers.json", "")
        self.assertRaises(SyntaxError, converter.convert)

    def test_convert_verify_yaml(self):
        self.converter = Converter("test_specs/petstore.yaml", "mech-petstore.json")
        self.converter.convert()
        self.verify_success()

    def test_convert_success(self):
        self.converter.convert()
        self.verify_success()

    def verify_success(self):
        # verify microservices
        self.assertEqual(len(self.converter.microservices.items()), 2)
        # TODO - verify each ms object

        self.assertTrue(self.converter.version.startswith("3"))
        self.assertIsNotNone(self.converter.oapi_obj)
        self.assertIsNotNone(self.converter.servers)
        self.assertIsNotNone(self.converter.paths)

        # verify controllers
        self.assertEqual(len(self.converter.controllers.items()), 4)