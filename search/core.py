import logging
import mmap
import os
from pathlib import Path
import time


class FileSearcher(object):

	def __init__(
		self, config, logger,
		max_depth, names, content
	):
		self.config = config
		self.logger = logger
		self.max_depth = max_depth
		self.names = names
		self.content = content
		self.stats = {'name': 0, 'file': 0}
		self.start = 0

	def access_denied(self, path):
		self.logger.info2('Permission denied: %s' % path.absolute())

	def search_file(self, path, term):
		size = os.path.getsize(str(path.absolute()))
		if size == 0:
			return 'file', path, 0

		try:

			with path.open('rb', os.O_RDONLY) as f, \
				 mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ) as m:

				matches = term.findall(m)
				return 'file', path, len(matches)

		except PermissionError:
			self.access_denied(path)
		except Exception as exc:
			self.logger.info2(
				'Error opening file: %s: %s: %s',
				path.absolute(), exc.__class__.__name__, str(exc)
			)

	def search_dir(self, path, term, depth):
		try:
			for path in path.iterdir():
				yield from self._search(path, term, depth + 1)
		except PermissionError:
			self.access_denied(path)		

	def check_name(self, path, term):
		name = os.fsencode(path.name)
		matches = term.findall(name)
		return 'name', path, len(matches)

	def _search(self, origin, term, depth=0):

		if not isinstance(origin, Path):
			origin = Path(origin).absolute()

		if not self.config.should_search(str(origin)):
			self.logger.debug('Ignoring path due to configuration: %s' % origin.absolute())
			return

		if self.names:
			yield self.check_name(origin, term)

		isfile, isdir = origin.is_file(), origin.is_dir()

		if self.max_depth is not None:
			if depth > self.max_depth and isdir:
				return
			elif depth > (self.max_depth + 1) and isfile:
				return

		if isfile and self.content:
			res = self.search_file(origin, term)
			if res is not None:
				yield res

		if isdir:
			yield from self.search_dir(origin, term, depth)

	def process_result(self, kind, path, num):
		lvl = logging.DEBUG if num == 0 else logging.INFO1
		self.logger.log(lvl, 'In %s: %s %d occurence(s)', kind, path.absolute(), num)
		self.stats.setdefault(kind, 0)
		self.stats[kind] += num > 0

	def print_finished(self):
		lines = []
		lines.append('\nSearch Completed.')

		for kind, count in self.stats.items():
			lines.append('In %s(s): %d results' % (kind, count))

		lines.append('Time elapsed: %f' % (time.time() - self.start))

		self.logger.info2('\n'.join(lines))

	def search(self, origins, term):
		self.stats = {}
		self.start = time.time()
		self.logger.info1('')
		for origin in origins:
			for kind, path, num in self._search(origin, term):
				self.process_result(kind, path, num)
		self.print_finished()
