from . import util
from kyodaishiki import __utils__
from kyodaishiki import __shell__
from . import picture
from bs4 import BeautifulSoup as bs4

"""
picture comment ... userid
memo  => comment[0]
comment => comment,url of picture
tags => "USERID:<userid>"
"""

class Attr(util.Attr):
	USERID="USERID"

class Data:
	def __init__(self,userid,comment,picture_url,else_data={}):
		self.userid=userid
		self.comment=comment
		self.picture_url=picture_url
		self.else_data=else_data

class Article:
	def __init__(self,url):
		self.url=url
		res=requests.get(url)
		self.soup=bs(res.text,"html.parser")
	def get_data(self):
		pass
	def dumpCSM(self):
		pass

class Docs(__utils__.Docs):
	APPEND="""
	Usage:
		append <dbid> <url>
	"""

class Command(util.Command):pass

class SiteShell(__shell__.BaseShell):
	def __init__(self,homeDB):
		self.homeDB=homeDB
		super().__init__()
	def execQuery(self,query,output):
		if query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except Exception as e:
				print(e)
				return
			dbid=args["<dbid>"].upper()
			url=args["<url>"]
			db=self.homeDB.select(dbid)
			if not db:
				self.homeDB.append(dbid,[TAG])
				db=self.homeDB.select(dbid)
			for csm in Article(url).dumpCSM():
				db.appendCSM(csm)
		elif query.command in Command.DUMP:
			return picture.Shell(self.homeDB).execQuery(query,output)
		else:
			return super().execQuery(query,output)
	def start(self):
		self.stdout.write("*** welcome to instagram ***\n")
		return super().start()

