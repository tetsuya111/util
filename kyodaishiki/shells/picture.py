from . import __binalli__
from kyodaishiki import __shell__
from . import util
from kyodaishiki import __utils__
from kyodaishiki import __data__
import docopt
import base64
import os
import re

TAG="IS_PICTURE"

class Docs:
	APPEND="""
	Usage:
		append url <dbid> <url> 
		append dir <dbid> <dname>
		append <dbid> <fname>
	"""
	DUMP="""
	Usage:
		dump <dbid> [(-d <dname>)]
	"""
	HELP="""
		append url <dbid> <url> 
		append dir <dbid> <dname>
		append <dbid> <fname>
		dump <dbid> [(-d <dname>)]
	"""

class Command(__utils__.Command):
	DUMP=("D","DUMP")

class Shell(__shell__.BaseShell):
	PROMPT=":>>"
	def __init__(self,homeDB):
		self.homeDB=homeDB
		super().__init__(prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		if query.command in Command.APPEND:
			query=__shell__.Query((*query,"-t",TAG))
			return __binalli__.Shell(self.homeDB).execQuery(query,output)
		elif query.command in Command.DUMP:
			return __binalli__.Shell(self.homeDB).execQuery(__shell__.Query(("DUMP","-t",TAG,*query.args)),output)
		else:
			return super().execQuery(query,output)

"""
class AuHSShell(__shell__.BaseShell):
	def __init__(self,homeDB):
		super().__init__(prompt=self.PROMPT)
		self.shell=Shell(homeDB)
	def execQuery(self,query,output):
		return self.shell.execQuery(query,output)
	def start(self):
		return self.shell.shell()
	def close(self):
		return self.shell.close()
"""
