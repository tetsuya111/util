from kyodaishiki import __shell__
from kyodaishiki import __server__
from kyodaishiki import __utils__
from kyodaishiki import _path
import sys
import os
import _pyio


class Docs:
	ALIAS="""
	Usage:
		alias <command> <query>...
	"""

class Command(__utils__.Command):
	ECHO=["ECHO"]
	ALIAS=("ALS","ALIAS")
	PATH=["PATH"]


class HomeShell(__shell__.HomeShell,__shell__.BaseShell3):
#HomeShell have commandToModule
	#COMMAND_CONF="auhs_command.conf"
	CHILD_SHELL="AuHSShell"
	class ShellStream:	#shell as stream
		def __init__(self,shell):
			self.shell=shell
		def write(self,s):
			sio=_pyio.StringIO()
			sio.write(s)
			sio.seek(0,0)
			self.shell.__begin__(sio,self.shell.stdout)
			#for line in s.split("\n"):
			#	self.shell.execQuery(__shell__.Query.read(line),self.shell.stdout)
		def __getattr__(self,attr):
			return getattr(self.shell,attr)
			
	def __init__(self,home):
		__shell__.BaseShell3.__init__(self,home.dname)
		__shell__.HomeShell.__init__(self,home)
		self.aliasCommands["PATH"]=__shell__.Query(["kyodaishiki._path"])
	def execQuery(self,query,output=sys.stdout):
		if not query:
			return
		if query.command in Command.ECHO:
			output.write(os.path.expandvars(" ".join(query.args))+"\n")
		elif query.command in __utils__.Command.HELP:
			__shell__.HomeShell.execQuery(self,query,output)
			__shell__.BaseShell2.execQuery(self,query,output)
		else:
			if query.command in (*Command.DB.LS,*Command.CLEAN,*Command.ALIAS,*self.aliasCommands,*map(lambda name:name.upper(),self.childNames)):
				return __shell__.BaseShell2.execQuery(self,query,output)
			return __shell__.HomeShell.execQuery(self,query,output)
	def getShell(self,module_name):
		return	__shell__.BaseShell2.getShell(self,module_name,self)
	def do_shell(self,module_name,args,output,*args__,**kwargs):
		super().do_shell(module_name,args,output,*args__,**kwargs)
		#self.stdout.write("*** {0} ***\n".format(self.home.id))
	def start(self):
		os.environ["KYODAISHIKI_HOME_DIR"]=self.dname
		os.environ["KYODAISHIKI_HOME_ID"]=self.id
		super().start()
	def parse_query(self,query):
#<query>... > <command>
		query__,output,mode=self.__parse_query__(query)
		if output:
			command=output.upper()
			if command.lower() in self.childNames:
				shell=self.getShell(command.lower())
				return (query__,self.ShellStream(shell),False)
			return super().parse_query(query)
		return super().parse_query(query)

def loadHome(dname,host="127.0.0.1"):
	home=__server__.ServerHome(dname,host)
	return HomeShell(home)
