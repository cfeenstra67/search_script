from contextlib import contextmanager
from functools import partial
from itertools import chain
import logging
import mmap
from multiprocessing.pool import ThreadPool
import os
from pathlib import Path
import queue
import threading
import time


def crawl(
	origin, 
	recurse_func=lambda x: True, 
	yield_dirs=True,
	max_depth=None,
	_depth=0
):
	if not isinstance(origin, Path):
		origin = Path(origin)

	if not origin.exists():
		return

	isfile = origin.is_file()

	if yield_dirs or isfile:
		yield origin

	if (
		not isfile 
		and recurse_func(str(origin)) 
		and (
			max_depth is None
			or _depth <= max_depth
		)

	):
		for path in origin.iterdir():
			yield from crawl(
				path, recurse_func, yield_dirs, 
				max_depth=max_depth, 
				_depth=_depth + 1
			)


class FileSearcher(object):

	def __init__(
		self, config, logger,
		max_depth, names, content,
		pool_size=16
	):
		self.config = config
		self.logger = logger
		self.max_depth = max_depth
		self.names = names
		self.content = content
		self.pool_size = pool_size

		self.crawler = partial(
			crawl,
			recurse_func=self.config.should_search,
			yield_dirs=True,
			max_depth=max_depth
		)

		self.reset_stats()

	def reset_stats(self):
		self.stats = {'name': 0, 'file': 0}
		self.start = time.time()

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

	def check_name(self, path, term):
		name = os.fsencode(path.name)
		matches = term.findall(name)
		return 'name', path, len(matches)

	def search_path(self, path, term):
		if not self.config.should_search(str(path)):
			self.logger.debug('Ignoring path due to configuration: %s' % path.absolute())
			return

		if self.names:
			yield self.check_name(origin, term)

		isfile = path.is_file()

		if path.is_file() and self.content:
			yield self.search_file(path, term)

	def process_path(self, path, term):
		for tup in self.search_path(path, term):
			self.process_result(*tup)

	@property
	@contextmanager
	def search_context(self):
		self.reset_stats()
		try:
			yield
		finally:
			self.print_finished()

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

	def search(self, origins, term, n_threads=4):

		mapper = map if n_threads is None else ThreadPool(n_threads).imap

		paths = map(self.crawler, origins)
		paths = chain.from_iterable(paths)

		proc_path = partial(self.process_path, term=term)

		with self.search_context:
			for _ in mapper(proc_path, paths):
				pass
