from . import augment_hs
from kyodaishiki import __shell__
import os
import selenium

class AuHSShell(__shell__.BaseShell3):
	PROMPT=":>"
	CHILD_SHELL="SNMShell"
	DNAME="_selenium"
	def __init__(self,home):
#objs is for save objects.
#if command is <command>,do_<command> is called 
		self.home_shell=home
		self.homeDB=home.home
		self.browser=None
		dname=os.path.join(self.homeDB.dname,self.DNAME)
		super().__init__(dname,prompt=self.PROMPT)
	def getShell(self,module_name):
		return super().getShell(module_name,self,self.browser)
	def shell(self):
		self.stdout.write("**** welcome to selenium shell ***\n")
		return super().shell()
	def close(self):
		if self.browser:
			self.browser.close()




