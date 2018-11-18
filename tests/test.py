import unittest
import os
import shutil
import tempfile

from search.core import crawl

class CrawlCase(unittest.TestCase):

	def setUp(self):
		self.tmpdir = tempfile.mkdtemp()
		self.setup_tmpdir()

	def setup_tmpdir(self):
		os.makedirs(os.path.join(self.tmpdir, 'a/b/c'))

	def tearDown(self):
		shutil.rmtree(self.tmpdir)

	def test_crawl(self):

		full = list(crawl(self.tmpdir))
		names = [os.path.split(path)[-1] for path in full][1:]

		self.assertEqual(names[:3], ['a', 'b', 'c'])

	def test_depth(self):

		full = list(crawl(self.tmpdir, max_depth=0))
		names = [os.path.split(path)[-1] for path in full][1:]

		self.assertEqual(names, ['a'])

		full = list(crawl(self.tmpdir, max_depth=1))
		names = [os.path.split(path)[-1] for path in full][1:]

		self.assertEqual(names, ['a', 'b'])

		full = list(crawl(self.tmpdir, max_depth=2))
		names = [os.path.split(path)[-1] for path in full][1:]

		self.assertEqual(names, ['a', 'b', 'c'])
