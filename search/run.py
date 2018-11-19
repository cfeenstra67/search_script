#!/usr/local/bin/python3

import argparse
import logging
import os
import re
import sys

from .config import load_config
from .core import FileSearcher
from .log import setup_levels


def make_logger(name):
	logger = logging.getLogger(name)
	handler = logging.StreamHandler(sys.stdout)
	handler.setFormatter(logging.Formatter('%(message)s'))
	logger.addHandler(handler)
	logger.setLevel(logging.INFO1)
	return logger

def make_regex(pattern_str, ops):
	options = 0
	for op in ops:
		options |= getattr(re, op.upper())
	pattern = re.compile(pattern_str, options)
	return pattern

def main(argv=None, logger=None, name='search'):
	setup_levels()

	if logger is None:
		logger = make_logger(name)

	if argv is None:
		argv = sys.argv[1:]

	parser = argparse.ArgumentParser(name)
	
	parser.add_argument('term',
		help='search term (regular expressions supported). Double escape character required if used.')
	parser.add_argument('-s', '--search', nargs='+', default=[os.getcwd()],
		help='specify files or directories to search.  Use -r option to search directories recursively.')
	parser.add_argument('-n', '--names', action='store_true', 
		help='search file/directory names.  If neither -n nor -f is specified, default behavior is to search both.')
	parser.add_argument('-f', '--files', action='store_true', 
		help='search file contents. If neither -n nor -f is specified, default behavior is to search both.')
	parser.add_argument('-v', '--verbose', action='store_true', 
		help='additional output')
	parser.add_argument('--debug', action='store_true', 
		help='debug-level output')
	parser.add_argument('-r', '--recurse', nargs='?', type=int, default=0,
		help='Search directories recursively.  If this is option is not enabled, only the names of '
			 'subdirectories will be searched. Add a number after this arg to determine max depth')
	parser.add_argument('-R', '--regex-options', nargs='+', default=[], 
		help='Additional regular expression options.')
	parser.add_argument('-t', '--threads', default=4, type=int,
		help='Number of threads to use')

	args = parser.parse_args(argv)

	if args.verbose:
		logger.setLevel(logging.INFO2)

	if args.debug:
		logger.setLevel(logging.DEBUG)

	pattern = make_regex(args.term.encode(), args.regex_options)

	valid, conf = load_config()

	if not valid:
		logger.info1(conf)
		return 1
	else:
		logger.debug('Using configuration from: %s' % conf.path)

	names, content = args.names, args.files
	if not (names or content):
		names, content = True, True

	searcher = FileSearcher(conf, logger, args.recurse, names, content)

	searcher.search(args.search, pattern, n_threads=args.threads)

	return 0
