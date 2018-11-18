
def main(name='search'):

	from .run import main as _main, make_logger
	from .log import setup_levels
	import sys

	setup_levels()
	logger = make_logger(name)

	try:
		ret = _main(sys.argv[1:], name=name, logger=logger)
	except (KeyboardInterrupt, SystemExit):
		logger.info2('Interrupted.')
		ret = 1
	except:
		ret = 1
		raise

	sys.exit(ret)

if __name__ == '__main__':
	main()
