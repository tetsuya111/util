from . import book
from kyodaishiki import __shell__
from . import util
from . import select2
import os
import docopt
from bs4 import BeautifulSoup as bs

HOST="www.bookmeter.co.jp"
URL="https://"+HOST

class Attr(util.Attr):
	ID="ID"

class Mode:
	READ="R"
	READING="S"
	TSUNDOKU="T"
	WANT="W"
	ALL="RSTW"

HOME_F=None
class Url:
	SEARCH_F=None
	HOME_F=HOME_F
	READ_F=HOME_F # + ...
	READING_F=HOME_F # + ...	
	TSUNDOKU_F=HOME_F # + ...	
	WANT_F=HOME_F # + ...	

class Book:
	#def __init__(self,title="")
	pass

def getBooks(url):
	pass


class Docs:
	class DB:
		HELP="""
		Usage:
			help [(-a|--all)]
		"""
		APPEND="""
		Usage:
			append (q|query) <query> [(-n <number>)]
			append id <id> [(-m <mode>)] [(-n <number>)]
		
		Options:
			*** mode ***
			R -> READ
			S -> READING
			T -> TSUNDOKU 
			W -> WANT
		"""
		HELP_TEXT="""
			append
		"""
	HELP="""
		select <dbid>
	"""

class Command(util.Command):
	pass


class DBShell(select2.DBShell):
	DEF_APPEND_MAX="100"
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			try:
				args=docopt.docopt(Docs.DB.HELP,query.args)
			except SystemExit as e:
				print(e)
				return
			output.write(Docs.DB.HELP_TEXT+"\n")
			if args["-a"] or args["--all"]:
				return super().execQuery(query,output)
		elif query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.DB.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["q"] or args["query"]:
				s_query=args["<query>"]
				books=[]
			elif args["id"]:
				id_=args["<id>"]
				books=[]
			max_=int(args["<number>"]) if args["-n"] else self.DEF_APPEND_MAX
			for i,book in enumerate(books):
				if i > max_:
					break
		else:
			return super().execQuery(query,output)

class SiteShell(__shell__.BaseShell):
	def __init__(self,homeDB):
		self.homeDB=homeDB
		super().__init__()
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		elif query.command in Command.DB.SELECT:
			if not query.args:
				output,write("	select <dbid>\n")
				return
			dbids=list(self.homeDB.getDBIDs(query.args[0].upper()))
			if not dbids:
				output.write("Don't find.\n")
				return
			dbid=dbids[0]
			db=self.homeDB.select(dbid)
			if not db:
				output.write("Don't find "+dbid+" .\n")
			shell=DBShell(db)
#exec alias.txt of select2 in homeDB
			all_alias=os.path.join(self.homeDB.dname,select2.AuHSShell.ALL_ALIAS_TXT)
			shell.execAliasf(all_alias,shell.null)
			return shell.start()
		else:
			return super().execQuery(query,output)
	def start(self):
		self.stdout.write("*** welcome to bookmeter ***\n")
		return super().start()

