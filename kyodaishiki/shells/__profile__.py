from kyodaishiki import __shell__
from . import crawl as cr
from . import util
import docopt

DBID="__PROFILE"
TAG="IS_PROFILE"

class Crawler(cr.Crawler):
	def __init__(self,db,crawlTV=60*60*24,ids=list(),limit=cr.DEFAULT_CRAWL_LIMIT):
		super().__init__(db,crawlTV,ids,[TAG],"",[],limit)
	def append(self,csm):
		csm.tags.append(TAG)
		return super().append(csm)

class Manage(cr.Manage):
	def start(self,name,dbid,crawlTV,ids=list(),limit=cr.DEFAULT_CRAWL_LIMIT,serve=False):
		return cr.BaseManage2.start(self,Crawler,name,dbid,[TAG],serve,crawlTV,ids,limit)

		

class Docs:
	class Crawl:
		START="""
		Usage:
			start ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--tv <crawlTV>)] [--serve]
		"""
		HELP="""
	start ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--tv <crawlTV>)] [--serve]
		"""
	HELP="""
		db
		crawl ...
		server
	"""

class Command(cr.Command):
	DB=["DB"]
	SERVER=("SER","SERVER")

class CrawlShell(cr.BaseShell):
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.Crawl.HELP.rstrip()+"\n")
			super().execQuery(query,output)
		elif query.command in Command.START:
			self.manage.clean()
			if self.manage.n>cr.MAX_CRAWL:
				print("Number of Crawl reached Max.(Max is {0})".format(MAX_CRAWL))
				return
			try:
				args=docopt.docopt(Docs.Crawl.START,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"]
			serve=args["--serve"]		#if server is True.open DB as server
			crawlTV=args["<crawlTV>"] if args["--tv"] else "1"
			crawlTV=util.culcSecond(crawlTV)
			if args["-u"]:
				ids=[args["<userid>"]]
			elif args["-f"]:
				ids=__server__.readIDFile(os.path.join("../",crawler.db.dname),args["<idFname>"])
			name=args["<crawlerName>"] if args["-n"] else "crawler_{0}".format(self.manage.n)
			try:
				self.manage.start(name,dbid,crawlTV,ids,serve=serve)
				print("Crawling",name,"...")
			except Exception as e:
				print(e)
		else:
			return super().execQuery(query,output)


class AuHSShell(__shell__.BaseShell):
	PROMPT=":>"
	def __init__(self,home_shell):
		self.homeDB=home_shell.home
		self.manage=Manage(self.homeDB)
		super().__init__(prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		elif query.command in Command.DB:
			db=self.homeDB.select(DBID)
			if not db:
				self.homeDB.append(DBID,[TAG])
				db=self.homeDB.select(DBID)
			shell=__shell__.DBShell(db)
			if query.args:
				shell.execQuery(__shell__.Query(query.args),output)
			else:
				shell.start()
		elif query.command in Command.CRAWL:
			shell=CrawlShell(self.manage)
			if query.args:
				shell.execQuery(__shell__.Query(query.args),output)
			else:
				shell.start()
		elif query.command in Command.SERVER:
			query__=__shell__.Query(query.args)
			if query__.command in Command.START:
				query=__shell__.Query(("server","start",DBID))
				return __shell__.BaseServerHomeShell(self.homeDB,__shell__.DBShell).execQuery(query,output)
			elif query__.command in Command.STOP:
				query=__shell__.Query(("server","stop",DBID))
				return __shell__.BaseServerHomeShell(self.homeDB,__shell__.DBShell).execQuery(query,output)
			else:
				output.write("	server start\n	server stop\n")
		else:
			return super().execQuery(query,output)
	def start(self):
		self.stdout.write("*** welcome to shell for profile! ***\n")
		return super().start()
	def close(self):
		self.manage.close()
