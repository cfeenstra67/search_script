from contextlib import contextmanager
from functools import partial
import logging
import mmap
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
		self.threads = []

		self.crawler = partial(
			crawl,
			recurse_func=self.config.should_search,
			yield_dirs=True,
			max_depth=max_depth
		)

		self.file_queue = queue.Queue()

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

	def server(self, que, func, timeout=.1):

		def serve():
			while self.running:
				try:
					tup = que.get(timeout=timeout)
				except queue.Empty:
					continue
				else:
					func(*tup)
					que.task_done()

		return serve

	def clear_queues(self):
		with self.file_queue.mutex:
			self.file_queue.queue.clear()

	def make_thread(self, target, daemon=True, start=True):
		t = threading.Thread(target=target, daemon=True)
		if start:
			t.start()
		return t

	def init_pool(self, join=True):
		if join:
			self.stop_pool()

		self.threads = []
		self.running = True

		self.clear_queues()

		fileserver = self.server(self.file_queue, self.process_path)

		for _ in range(self.pool_size):
			self.threads.append(self.make_thread(fileserver))

	def stop_pool(self):
		self.running = False
		for thread in self.threads:
			thread.join()

	@property
	@contextmanager
	def pool_context(self):
		self.init_pool()
		try:
			yield
		finally:
			self.stop_pool()

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

	def search(self, origins, term):
		self.reset_stats()

		with self.pool_context, self.search_context:
			for origin in origins:
				for path in self.crawler(origin):
					self.file_queue.put((path, term))

			self.file_queue.join()
