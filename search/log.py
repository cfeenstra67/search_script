import logging

def add_level(name, num):
	logging.addLevelName(num, name)

	def func(self, message, *args, **kws):
		if self.isEnabledFor(num):
			self._log(num, message, args, **kws)

	lower_name = name.lower()
	func.__name__ = lower_name

	setattr(logging.Logger, lower_name, func)
	setattr(logging, name.upper(), num)

NEW_LEVELS = {
	'info2': 11,
	'info1': 12
}

def setup_levels():
	for k, v in NEW_LEVELS.items():
		add_level(k, v)
