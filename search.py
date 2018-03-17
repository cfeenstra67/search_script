#!/usr/local/bin/python3

import argparse
from mmap import mmap, PROT_READ
import os
from pathlib import Path
import re
import sys
from time import time

def _denied(path): print('Permission denied: %s' % path.absolute())

def _namecheck(path, search):
	name = os.fsencode(path.name)
	matches = search.findall(name)
	if matches: yield 'name', path.absolute(), len(matches)

def _filecheck(path, search, verbose):
	try:
		with path.open('rb', os.O_RDONLY) as f, \
			 mmap(f.fileno(), 0, prot=PROT_READ) as m:

			matches = search.findall(m)
			if matches: yield 'file', path.absolute(), len(matches)
	except PermissionError:
		if verbose: _denied(path)
	except Exception as exc:
		if verbose: 
			print(
				'Error opening file: %s: %s: %s' % \
				(path.absolute(), exc.__class__.__name__, str(exc))
			)

def look(origin, search, name=True, content=True, verbose=False, recursive=False):
	if not isinstance(origin, Path):
		origin = Path(origin)

	if name: 
		yield from _namecheck(origin, search)

	if origin.is_dir():
		try:
			for path in origin.iterdir():
				isdir = path.is_dir()
				if (isdir and recursive) or path.is_file(): 
					yield from look(
						origin=path, 
						search=search, 
						name=name, 
						content=content, 
						verbose=verbose, 
						recursive=recursive
					)
				elif (isdir and name):
					yield from _namecheck(path, search)
		except PermissionError: 
			if verbose: _denied(origin)
	elif content:
		yield from _filecheck(origin, search, verbose)

def print_result(kind, path, num):
	print('In %s: %s %d occurence(s)' % (kind, path, num))

def print_finished(counts, elapsed):
	lines = []
	lines.append('\nSearch Completed.')
	for kind, count in counts.items():
		lines.append('In %s(s): %d results' % (kind, count))
	lines.append('Time elapsed: %f' % elapsed)
	print('\n'.join(lines))

def main():
	parser = argparse.ArgumentParser()
	
	parser.add_argument('term',
		help='search term (regular expressions supported). Double escape character required if used.')
	parser.add_argument('-s', '--search', 
		nargs='*', default=[os.getcwd()], help='specify files or directories to search.  Use -r option to search directories recursively.')
	parser.add_argument('-n', '--names', 
		action='store_true', help='search file/directory names.  If neither -n nor -f is specified, default behavior is to search both.')
	parser.add_argument('-f', '--files',
		action='store_true', help='search file contents. If neither -n nor -f is specified, default behavior is to search both.')
	parser.add_argument('-v', '--verbose',
		action='store_true', help='additional output')
	parser.add_argument('-r', '--recursive',
		action='store_true', help='Search directories recursively.  If this is option is not enabled, only the names of subdirectories will be searched.')
	parser.add_argument('-R', '--regex-options', nargs='+', default=[], 
		help='Additional regular expression options.')

	args = parser.parse_args()

	options = 0
	for op in args.regex_options:
		options |= getattr(re, op.upper())
	pattern = re.compile(args.term.encode(), options)
	counts = {'file':0, 'name':0}
	beg = time()

	for place in args.search:		
		g = lambda names, files: look(place, pattern, names, files, args.verbose, args.recursive)
		gen = g(args.names, args.files) if (args.names or args.files) else g(True, True)
		for result in gen:
			print_result(*result)
			counts[result[0]] += 1
	if args.verbose: print_finished(counts, time() - beg)


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt: 
		print('\n')
		sys.exit(0)