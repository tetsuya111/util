from kyodaishiki import __shell__
from kyodaishiki import __utils__
from . import augment_hs
from . import shiori
from . import userid
from . import crawl as cr
import docopt
import sys
import os


class Docs(__utils__.Docs):
	HELP="""
$ ls
$ clean
	"""

def is_shell(obj):
	return issubclass(type(obj),__shell__.BaseShell)

class Shell(__shell__.BaseShell3):
	PROMPT=":>"
	CHILD_SHELL="DUShell"
	DNAME="_dbutil"
	def __init__(self,homeDB):
#objs is for save objects.
#if command is <command>,do_<command> is called 
		dname=os.path.join(homeDB.dname,self.DNAME)
		self.homeDB=homeDB
		super().__init__(dname,prompt=self.PROMPT)
	def getShell(self,module_name):
		return super().getShell(module_name,self)
	def shell(self):
		self.stdout.write("**** welcome to dbutil shell ***\n")
		return super().shell()

class AuHSShell(__shell__.BaseShell):
	def __init__(self,home):
		super().__init__(prompt=self.PROMPT)
		self.shell=Shell(home.home)
	def execQuery(self,query,output):
		return self.shell.execQuery(query,output)
	def start(self):
		return self.shell.shell()
	def close(self):
		return self.shell.close()




