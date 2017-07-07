import fileinput
import unittest
import json

from jsoncompare import compare
from subprocess import call


class MechanicTest(unittest.TestCase):
	def test_spec(self):
		call(["python", "../generate-resources-v3.py", "../../cmdb/resources/master-v3.json", "~/cmdb", "--debug"])

		with open("debug.json", "r") as file:
			data = file.read()

		data = data.replace("'", "\"")
		data = data.replace("True", "true")
		data = data.replace("False", "false")
		data = data.replace("None", "null")

		with open("debug.json", "w") as file:
			file.write(data)

		result = compare("debug.json", "expected-spec.json")
		self.assertEqual(result, [])
		
