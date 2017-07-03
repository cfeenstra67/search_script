This script can be used to easily find a string or regular expression, searching both file names and their contents.  See below for a description of how particular arguments can be used to customize behavior.

usage: search.py [-h] [-s [SEARCH [SEARCH ...]]] [-n] [-f] [-v] [-r] term

positional arguments:
  term                  search term (regular expressions supported). Double
                        escape character required if used.

optional arguments:
  -h, --help            show this help message and exit
  -s [SEARCH [SEARCH ...]], --search [SEARCH [SEARCH ...]]
                        specify files or directories to search. Use -r option
                        to search directories recursively.
  -n, --names           search file/directory names. If neither -n nor -f is
                        specified, default behavior is to search both.
  -f, --files           search file contents. If neither -n nor -f is
                        specified, default behavior is to search both.
  -v, --verbose         additional output
  -r, --recursive       Search directories recursively. If this is option is
                        not enabled, only the names of subdirectories will be
                        searched.