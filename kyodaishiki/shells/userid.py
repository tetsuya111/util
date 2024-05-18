from kyodaishiki import _util
from kyodaishiki import __shell__
from kyodaishiki import __data__
from . import util
from . import select2
from . import crawl as cr
from . import category
import re
import os
import copy
from functools import *
import docopt
import sys
import datetime
import _pyio

TAG="USERID"
DEFAULT_DUMP_FILE=_util.realpath(r"%USERPROFILE%\desktop\dumpeduserid.txt")
#userid as category


class Userid(category.List):
	TITLE="USER_ID"
	def get_userids(self,titles=[]):
		return self.get_cols2(titles)
	@property
	def userids(self):
		if not self.__userids:
			self.__userids=self.get_cols()
		return self.__userids
#head => csm.memo => Category.read(csm.comment)

def crawl(ids,tv=cr.DEFAULT_CRAWL_TV,limit=cr.DEFAULT_CRAWL_LIMIT):
	return cr.crawl(ids,[TAG],tags=[TAG],tv=tv,limit=limit)

def crawlf(idFname,tv=cr.DEFAULT_CRAWL_TV,limit=cr.DEFAULT_CRAWL_LIMIT):
	ids=cr.readIDFile(idFname)
	return cr.crawl(ids,[TAG],tags=[TAG],tv=tv,limit=limit)

class Crawler(category.Crawler):
	def __init__(db,crawlTV,ids,limit=cr.DEFAULT_CRAWL_LIMIT):
		super().__init__(TAG,db,crawlTV,ids,limit)
	def crawl(self,*args,**kwargs):
		return crawl(*args,**kwargs)
	def append(self,csm):
		return self.db.appendCSM(csm)

class Manage(cr.Manage):
	def __init__(self,homeDB):
		super().__init__(homeDB,TAG)
	def start(self,name,dbid,crawlTV,ids=[],limit=cr.DEFAULT_CRAWL_LIMIT,serve=False):
		return super().start(Crawler,name,dbid,[self.tag],serve,crawlTV,ids,tv,limit)

def writeShell(output=sys.stdout):
	csm=category.writeShell(TAG,"Title : ","Userid : ",output)
	csm.memo=csm.memo.replace("T:","U:")
	return csm


class Docs(_util.Docs):
	class DB:
		WRITE="""
		Usage:
			write (u|userid)
			write tot
			write
		"""
		APPEND="""
		Usage:
			append (u|user) <srcTitles> <dstTitles>
			append (u|user) rec <titles>...
			append (u|user) all
			append tag [(-t <tags>)] [(-m <memo>)] <tagsToAppend>...
			append tag [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)] <tagsToAppend>...
		"""
		DUMP="""
		Usage:
			dump [(-T <titles>)] [(-o <output>)]
		"""
		HELP="""
			dump [(-T <titles>)] [(-o <output>)]
			append
			write
		"""
	CRAWL="""
	Usage:
		crawl start ((-f <idFname>)|(-u <userid>))  <dbId> [(-n <crawlerName>)] [(--tv <crawlTV>)] [--serve]
	"""
	DUMP="""
	Usage:
		dump <dbid> [(-T <titles>)] [(-o <output>)]
	"""
	HELP="""
		dump <dbid> [(-T <titles>)] [(-o <output>)]
		crawl start ((-f <idFname>)|(-u <userid>))  <dbId> [(-n <crawlerName>)] [(--tv <crawlTV>)] [--serve]
	"""

class Command(select2.Command):
	DUMP=("D","DUMP")

class DBShell(category.DBShell):
	ALL_TITLE="All"
	DEF_DUMP_FILE=_util.realpath(r"%USERPROFILE%\desktop\dumpeduserid.txt")
	def __init__(self,db,expander,*_):
		super().__init__(db,expander,TAG)
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.DB.HELP+"\n")
		elif query.command in Command.WRITE:
			try:
				args=docopt.docopt(Docs.DB.WRITE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["u"] or args["userid"]:
				csm=writeShell()
				self.db.appendCSM(csm)
			else:
				return super().execQuery(query,output)
			self.db.save()
		elif query.command in Command.APPEND:
			print(query)
			try:
				args=docopt.docopt(Docs.DB.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["u"] or args["user"]:
				if args["rec"]:
					titles=args["<titles>"]
					return super().execQuery(__shell__.Query.read("append category rec {0}".format(" ".join(titles))),output)
				elif args["all"]:
					return super().execQuery(__shell__.Query.read("append category all"),output)
				else:
					srcTitles=args["<srcTitles>"]
					dstTitles=args["<dstTitles>"]
					return super().execQuery(__shell__.Query.read("append category {0} {1}".format(srcTitles,dstTitles)),output)
				self.db.save()
			else:
				return super().execQuery(query,output)
		else:
			return super().execQuery(query,output)
				


class DUShell(category.DUShell):
	PROMPT=":>>"
	TAG=TAG
	DB_SHELL=DBShell
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		else:
			return super().execQuery(query,output)
	def select(self,args,output):
		return super().select((self.TAG,*args),output)
	def start(self):
		self.stdout.write("*** welcome to userid shell! ***\n")
		return super().start()

