#!/usr/bin/python3

import argparse
from mmap import mmap, PROT_READ
import os
import re
import sys
from time import time

def _denied(path): print('Permission denied: %s' % path)

def _namecheck(path, search):
	name = os.path.split(path)[-1]
	matches = search.findall(name)
	if matches: yield 'name', path, len(matches)

def _filecheck(path, search, verbose):
	try:
		with open(path, 'rb', os.O_RDONLY) as f, \
			 mmap(f.fileno(), 0, prot=PROT_READ) as m:

			matches = search.findall(m)
			if matches: yield 'file', path, len(matches)
	except PermissionError:
		if verbose: _denied(path)
	except Exception as exc:
		if verbose: 
			print(
				'Error opening file: %s: %s: %s' % \
				(path, exc.__class__.__name__, str(exc))
			)

def look(origin, search, name=True, content=True, verbose=False, recursive=False):
	if name: yield from _namecheck(origin, search)
	if os.path.isdir(origin):
		try:
			for fname in os.listdir(origin):
				path = os.path.join(origin, fname)
				isdir = os.path.isdir(path)
				if (isdir and recursive) or os.path.isfile(path): 
					yield from look(os.path.join(origin, fname), search, name, content, verbose, recursive)
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
<<<<<<< HEAD
	pattern = re.compile(args.term.encode())
=======
	options = 0
	for op in args.regex_options:
		options |= getattr(re, op.upper())
	pattern = re.compile(args.term, options)
>>>>>>> 218c4b3d24222df3a30ca5246b30ca1453d20c13
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