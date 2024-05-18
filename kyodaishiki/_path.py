#from kyodaishiki import __shell__
from . import _util
from . import __shell__
import sys
import docopt
import os
import re

class Docs:
	class Command:
		APPEND="""
		Usage:
			append file <commandConf>
		"""
	APPEND="""
	Usage:
		append file <pathFile>
		append <path>
	"""
	IMPORT="""
	Usage:
		import file <modulesFile>
		import (pkg|package) [(-a|--all)] <dname>
		import dir <dname>
		import <module_name>
	"""
	SET="""
	Usage:
		set <key> <value>
		set [<key>]
	"""
	HELP="""
		append file <pathFile>
		append <path>
		import file <modulesFile>
		import dir <dname>
		import <module_name>
	"""

class Command(_util.Command):
	IMPORT=["IMPORT"]
	COMMAND=["COMMAND"]
	SET=["SET"]

class AuHSShell(__shell__.BaseShell):
	PROMPT="#"
	def __init__(self,home_shell,*args):
		super().__init__(prompt=self.PROMPT)
		self.home_shell=home_shell
		self.homeDB=home_shell.home
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		elif query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["file"]:
				fname=args["<pathFile>"]
				with open(fname,"r") as f:
					paths=list(map(lambda line:line.rstrip(),f))
			else:
				paths=[args["<path>"]]
			for path in paths:
				path=_util.realpath(path)
				sys.path.append(path)
				output.write("Append path of {0}\n".format(path))
		elif query.command in Command.IMPORT:
			try:
				args=docopt.docopt(Docs.IMPORT,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["pkg"] or args["package"]:
				dname=args["<dname>"]
				dname=_util.realpath(dname)
				root,pkgname=os.path.split(dname)
				sys.path.append(root)
				exec("import "+pkgname)
				if args["-a"] or args["--all"]:
					for fname in os.listdir(dname):
						if re.match(".+\.py$",fname):
							module_name,ext=fname.rsplit(".",1)
							exec("from {0} import {1}".format(pkgname,module_name))
							self.home_shell.aliasCommands[module_name.upper()]=__shell__.Query([pkgname+"."+module_name])
				return
			elif args["file"]:
				fname=_util.realpath(args["<modulesFile>"])
				with open(fname,"r") as f:
					module_names=list(map(lambda line:line.rstrip(),f))
			elif args["dir"]:
				dname=_util.realpath(args["<dname>"])
				module_names=map(lambda fname:fname.replace(".py",""),filter(lambda fname:re.fullmatch(".*\.py$",fname),os.listdir(dname)))
			else:
				module_names=[args["<module_name>"]]
			for module_name in module_names:
				try:
					exec("import "+module_name)
					output.write("Imported "+module_name+"\n")
				except Exception as e:
					print(e,module_name)
					pass
		elif query.command in Command.SET:
			try:
				args=docopt.docopt(Docs.SET,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["<value>"]:
				key=args["<key>"]
				value=args["<value>"]
				os.environ[key]=value
			else:
				key__=args["<key>"].upper() if args["<key>"] else ""
				for key in os.environ:
					if re.search(key__,key):
						output.write("{0}:{1}\n".format(key,os.environ[key]))
		else:
			return super().execQuery(query,output)
