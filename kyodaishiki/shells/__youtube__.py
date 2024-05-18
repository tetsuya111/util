from kyodaishiki import __shell__
from . import util
from . import select2
import docopt
import os
import sys
import _pyio

class Attr(util.Attr):
	M_S="M_S"
	TITLE="TITLE"
	USER="USER"

class Shell:
	@staticmethod
	def write(output=sys.stdout):
		output.write("M:")	
		m=input()
		output.write("S:")
		s=input()
		csm=__shell__.Shell.write()
		csm.tags=(*csm.tags,util.Attr(Attr.M_S)(m+"_"+s))
		return csm

class Docs:
	SELECT="""
	Usage:
		select <dbid>
	"""
	WRITE="""
	Usage:
		write (sh|shi|shiori) [(-t <tags>)] [(-T <title>)] [(-u <username>)]
		write tot
		write
	"""

class Command(util.Command):
	SELECT=("SE","SELECT")

class DBShell(select2.DBShell):
	def execQuery(self,query,output):
		if query.command in Command.WRITE:
			try:
				args=docopt.docopt(Docs.WRITE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["sh"] or args["shi"] or args["shiori"]:
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				if args["-T"]:
					title=args["<title>"] 
					tags.append(Attr(Attr.TITLE)(title))
				if args["-u"]:
					username=args["<username>"] 
					tags.append(Attr(Attr.USER)(username))
				csm=Shell.write()
				csm.tags=(*csm.tags,*tags)
				self.db.appendCSM(csm)

			else:
				return super().execQuery(query,output)
		else:
			return super().execQuery(query,output)

class SiteShell(__shell__.BaseHomeShell):
	PROMPT=":>>"
	def __init__(self,homeDB):
		self.homeDB=homeDB
		self.null=_pyio.StringIO()
		super().__init__(homeDB,DBShell,prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in Command.SELECT:
			try:
				args=docopt.docopt(Docs.SELECT,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"].upper()
			db=self.home.select(dbid)
			if not db:
				output.write("Dont find {0}.\n".format(dbid.lower()))
				return
			shell=DBShell(db)
			alias_fname=os.path.join(self.dname,select2.AuHSShell.ALL_ALIAS_TXT)
			shell.execAliasf(alias_fname,self.null)
			return shell.start()
		else:
			return super().execQuery(query,output)
	def start(self):
		self.stdout.write("*** welcome to youtube ***\n")
		return super().shell()

#SiteShell(None).execQuery(__shell__.Query(("APPEND","ttt","--date","2019-2-12,2020-1-1")),sys.stdout)
