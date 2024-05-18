from kyodaishiki import __shell__
from . import augment_hs
import docopt
import os

class Docs:
	HELP="""
	login
	append src <srcid> <dstid>
	append dst <dstid> <srcid>
	"""
	class AuHS:
		INIT="""
		Usage:
			github (-u <userid>)
		"""
class Home:
	def __init__(self,homeid=""):
		self.homeid=homeid
	def getDBIDs(self,dbid=""):
		pass

class User:
	def __init__(self,userid="",password=""):
		self.userid=userid
		self.password=password
		self.homes=[]
	def __bool__(self):
		return bool(self.userid)
	def login(self):
		pass
	def close(self):
		pass

class Shell(__shell__.BaseShell3):
	PROMPT="~>"
	def __init__(self,homeDB):
		self.homeDB=homeDB
		super().__init__(prompt=self.PROMPT)
		self.user=User()
	def setUser(self,user):
		if self.user:
			self.user.close()
		self.user=user


class AuHSShell(__shell__.BaseShell3):
	PROMPT=">>"
	DNAME="_github"
	def __init__(self,home):
		self.homeDB=home.home
		self.shell=Shell(self.homeDB)
		dname=os.path.join(home.dname,self.DNAME)
		super().__init__(dname=dname,prompt=self.PROMPT)
	def execQuery(self,query,output):
		try:
			args=docopt.docopt(Docs.AuHS.INIT,("github",*query))
		except SystemExit as e:
			output.write(e)
			return
		userid=args["<userid>"]
		user=User(userid)
		self.shell.setUser(user)
		return self.shell.start()
	def start(self):
		return self.shell.start()
