from . import __db__
from . import _util
from . import __server__
from . import __data__
from . import __dns__
from . import __index__
from . import __shell__
from ._util import *
import sys
import docopt
import random
import subprocess as sp
from functools import *
import re
import shutil
import os
import threading
import datetime

HOME=realpath("%USERPROFILE%\\kyodaishiki2")
DEFAULT_LOADER_DIR=os.path.join(HOME,"default_loader_home")
DEFAULT_HOME="MAIN"
DEFAULT_DB="MAIN"

sys.path.append(_util.realpath("%USERPROFILE%\\code/kyodaishiki2"))


__doc__="""
Usage:
	kyodaishiki (-q <query>) [(-d <dname>)] [(--home <homeid>)] [(--db <dbid>)]
	kyodaishiki home <dname>
	kyodaishiki db <dname>
	kyodaishiki [(-d <dname>)]

"""

def main():
	try:
		args=docopt.docopt(__doc__)
	except SystemExit:
		#print(sys.argv)
		exit()

	dname=args["<dname>"] or DEFAULT_LOADER_DIR
	dname=_util.realpath(dname)
	if args["home"]:
		home=__db__.HomeTagDB(dname)
		shell=__shell__.HomeShell(home)
		shell.start()
	elif args["db"]:
		db=__db__.TagDB(dname)
		shell=__shell__.DBShell(db)
		shell.start()
	else:
		if os.environ.get(__shell__.EnvKey.LOADER_HOME):
			dname=_util.realpath(os.environ[__shell__.EnvKey.LOADER_HOME])

		if not os.path.exists(dname):
			os.makedirs(dname)

		loader=__shell__.HomeLoader(dname)

		if args["-q"]:
			homeid=args["<homeid>"] if args["--home"] else DEFAULT_HOME
			dbid=args["<dbid>"] if args["--db"] else DEFAULT_DB
			query=__shell__.Query(args["<query>"].split(" "))
			home_shell=loader.get(homeid)
			loader.close()
			if not home_shell:
				print(homeid,"don't be found.")
				exit()
			db=home_shell.home.select(dbid)
			if not db:
				print(dbid,"don't be found.")
				exit()
			home_shell.close()
			__shell__.DBShell(db).execQuery(query,sys.stdout)
		else:
			loader.start()

if __name__ == "__main__":
	main()
