from kyodaishiki import __utils__
from kyodaishiki import __shell__
from . import wikipedia
from . import nichan
from . import augment_hs
import sys
import os

class Command:
	WIKIPEDIA=("W","WIKIPEDIA")
	NICHAN=("2CH","NICHAN")

HELP="""
	wikipedia <query>...
	nichan <query>...
"""


class Shell(__shell__.BaseShell3):
	PROMPT=":>"
	CHILD_SHELL="SiteShell"
	DNAME="_site"
	def __init__(self,homeDB):
		self.homeDB=homeDB
		dname=os.path.join(homeDB.dname,self.DNAME)
		super().__init__(dname=dname,prompt=self.PROMPT)
	def getShell(self,module_name):
		return super().getShell(module_name,self.homeDB)
	def start(self):
		self.stdout.write("*** welcome to site shell ***\n")
		return super().start()

class AuHSShell(__shell__.BaseShell3):
	PROMPT=">>"
	def __init__(self,homeShell):
		super().__init__(prompt=self.PROMPT)
		self.shell=Shell(homeShell.home)
	def execQuery(self,query,output):
		return self.shell.execQuery(query,output)
	def start(self):
		return self.shell.start()

		
	
