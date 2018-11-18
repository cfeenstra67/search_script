from collections import OrderedDict
from contextlib import closing
from copy import deepcopy
from functools import partial
import glob
import inspect
from itertools import chain
import json
import os
import re

CONFIG_PATHS = (
	'~/.search.conf*',
	'/etc/search.conf*'
)

CONFIG_LOADERS = OrderedDict([
	(('json',), json.loads)
])

DEFAULT_CONFIG = {}

try:
	import yaml
	CONFIG_LOADERS['yml', 'yaml'] = yaml.load
except ImportError:
	pass

def shellify(path, abs=True):
	path = os.path.expanduser(path)
	if abs:
		path = os.path.abspath(path)
	path = glob.glob(path)
	return path

def uniq(iterable):
	helper = set()
	return (i for i in iterable if i not in helper and (helper.add(i) or True))

def guess_loader(path, loaders):
	_, name = os.path.split(path)
	ext = name.rsplit('.', 1)[-1]
	loaders = tuple(lo for keys, lo in CONFIG_LOADERS.items() if ext in keys)
	return loaders

def load_config_at_path(path, loaders=CONFIG_LOADERS, default=DEFAULT_CONFIG):

	if not (
		os.path.exists(path)
		and os.path.isfile(path)
	):
		return

	try:
		with open(path, encoding='utf-8') as f:
			content = f.read()
	except (PermissionError, EOFError):
		return

	try_loaders = guess_loader(path, loaders) + tuple(loaders.values())

	for loader in uniq(try_loaders):
		try:
			return loader(content)
		except:
			pass

	return default

def load_config_dict(paths=CONFIG_PATHS):
	paths = map(shellify, paths)
	paths = chain.from_iterable(paths)

	for path in paths:
		conf = load_config_at_path(path)
		if conf is not None:
			return conf, path

	return {}, None

## PATTERN MATCHERS

def regex_matches(*args, options=0):
	pattern, value = args

	if isinstance(options, str):
		options = list(options)

	elif isinstance(options, list):
		ops = 0
		for op in options:
			if isinstance(op, int):
				ops |= op
			else:
				ops |= getattr(re, op.upper())
		self.options = ops

	return bool(re.search(pattern, value, options))

def glob_matches(*args):
	pattern, value = args
	return glob.fnmatch.fnmatch(value, pattern)


class Configuration(object):

	pattern_types = {
		'regex': regex_matches,
		'glob': glob_matches
	}

	def __init__(self, src, path):
		self.src = src
		self.path = path
		self.ignore_names = []

	def check_func_kwargs(self, func, keys):
		sig = inspect.signature(func)
		params = sig.parameters

		for k, v in params.items():
			# VAR_KEYWORD
			if v.kind == 4:
				return True, None, ()

		for k in keys:
			if k not in params:
				return False, 'Invalid parameter %r' % k, (k,)

		return True, None, ()

	def get_ignore_funcs(self, vals):
		if not isinstance(vals, list):
			vals = [vals]

		out = []

		for ind, val in enumerate(vals):
			if not isinstance(val, dict):
				val = {'glob': val}

			pattern_types = [i for i in val if i in self.pattern_types]

			if len(pattern_types) == 0:
				return False, 'No valid pattern type found', (ind,)
			if len(pattern_types) > 1:
				return False, 'Multiple pattern types found: %r' % pattern_types, (ind,)

			typ, = pattern_types
			pattern = val.pop(typ)

			func = self.pattern_types[typ]
			valid, reason, path = self.check_func_kwargs(func, val.keys())

			if not valid:
				return False, reason, (ind,) + path

			wrapped = partial(func, pattern, **val)
			out.append(wrapped)

		return True, out, ()

	def load(self):
		src = deepcopy(self.src)
		
		to_ignore = src.pop('ignore', None)
		if to_ignore is not None:
			valid, ignore, path = self.get_ignore_funcs(to_ignore)

			if not valid:
				return valid, ignore, ('ignore',) + path

			self.ignore_names = ignore

		if len(src) > 0:
			return False, 'Unrecognized keys: %r' % list(src), ()

		return True, None, ()

	def should_search(self, path):
		_, name = os.path.split(path)
		return not any(match(name) for match in self.ignore_names)


def load_config(paths=CONFIG_PATHS):
	config_path = os.getenv('SEARCH_CONFIG')
	if config_path is not None:
		paths = (config_path,) + paths

	config_dict, path = load_config_dict(paths)

	config = Configuration(config_dict, path)

	valid, msg, path = config.load()

	if not valid:
		path_str = '>'.join(map(str, path))
		return False, 'Configuration error at path: %s: %s' % (path_str, msg)

	return True, config
