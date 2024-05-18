from . import util
from . import select2
from kyodaishiki import _util
from kyodaishiki import __shell__
from kyodaishiki import __data__
from . import crawl as cr
import re
import os
import copy
from functools import *
import docopt
import sys
import datetime
import _pyio

DEFAULT_DUMP_FILE=_util.realpath(r"%USERPROFILE%\desktop\dumpeduserid.txt")
#userid as category


class List(util.CategoryTree):
	TITLE="XXX"
	def __init__(self,head,index):
		super().__init__(head,index)
		self.__userids=None
	def __add__(self,dst):
		return util.CategoryTree(\
		util.Category(self.TITLE,childs=self.head.childs+dst.head.childs),\
		self.add_index(self.index,dst.index)
		)
	def __get_cols2__(self,titles=[]):
#titles[0]=>titles[1]=>...
		for c in self.searchRec(titles):
			for userid in c.get_cols():
				yield userid
	def get_cols2(self,titles=[]):
		return set(self.__get_cols2__(titles))
	@property
	def cols(self):
		if not self.__userids:
			self.__userids=self.get_cols()
		return self.__userids
	def write(fname):
		with open(fname,"w") as f:
			f.write(str(self))
	@staticmethod
	def read(s):
		ct=util.CategoryTree.readAsOne(s,List.TITLE)
		return List(ct.head,ct.index)
	@staticmethod
	def readCSM(csm):
		return List.read(csm.comment)
	@staticmethod
	def readf(fname):
		with open(fname,"r") as f:
			return List.readCSM(__data__.CSM.read(fname))
#head => csm.memo => Category.read(csm.comment)

def crawl(tag,ids,tv=cr.DEFAULT_CRAWL_TV,limit=cr.DEFAULT_CRAWL_LIMIT):
	return cr.crawl(ids,[tag],tags=[tag],tv=tv,limit=limit)

def crawlf(tag,idFname,tv=cr.DEFAULT_CRAWL_TV,limit=cr.DEFAULT_CRAWL_LIMIT):
	ids=cr.readIDFile(idFname)
	return cr.crawl(ids,[tag],tags=[tag],tv=tv,limit=limit)

class Crawler(cr.Crawler):
	def __init__(tag,db,crawlTV,ids,limit=cr.DEFAULT_CRAWL_LIMIT):
		super().__init__(db,crawlTV,ids,tags=[tag],limit=limit)
	def crawl(self,*args,**kwargs):
		return crawl(*args,**kwargs)
	def append(self,csm):
		return self.db.appendCSM(csm)

class Manage(cr.BaseManage2):
	def __init__(self,homeDB,tag):
		super().__init__(homeDB)
		self.tag=tag
	def start(self,name,dbid,crawlTV,ids=[],limit=cr.DEFAULT_CRAWL_LIMIT,serve=False):
		return super().start(Crawler,name,dbid,[self.tag],serve,crawlTV,ids,tv,limit)

def writeShell(tag,title_text="Title : ",col_text="Col : ",output=sys.stdout):
	output.write(title_text)
	title=input()
	userids=_util.inputUntilSeq(col_text,output=output)
	date=str(datetime.datetime.now()).split(".",1)[0]
	return __data__.CSM("T:"+title,"*"+title+"\n"+"\n".join(map(lambda userid:"-"+userid,userids)),[tag],date)


class Docs(_util.Docs):
	class DB:
		WRITE="""
		Usage:
			write (c|category)
			write tot
			write
		"""
		APPEND="""
		Usage:
			append (c|category) <srcTitles> <dstTitles>
			append (c|category) rec <titles>...
			append (c|category) all
			append (c|category) csv <fname> [<title>]
			append (tot|totot) [(-t <tags>)] [(-m <memo>)]
			append (tot|totot) csv <fname> [<title>]
			append tag [(-t <tags>)] [(-m <memo>)] <tagsToAppend>...
			append tag [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)] <tagsToAppend>...

		Options:
			*** csv file of append category csv  ***
				<name>;<root>,...
					:
					:
		"""
		DUMP="""
		Usage:
			dump [(-T <titles>)] [(-t <tags>)] [(-m <memo>)] [(-o <output>)]
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
	SELECT="""
	Usage:
		select <category_tag> <dbid> [<query>...]
	"""
	HELP="""
		dump <dbid> [(-T <titles>)] [(-o <output>)]
		crawl start ((-f <idFname>)|(-u <userid>))  <dbId> [(-n <crawlerName>)] [(--tv <crawlTV>)] [--serve]
	"""

class Command(select2.Command):
	DUMP=("D","DUMP")

class DBShell(select2.DBShell):
	ALL_TITLE="All"
	DEF_DUMP_FILE=_util.realpath(r"%USERPROFILE%\desktop\dumpedlist.txt")
	TITLE_F="C:{0}"
	def __init__(self,db,expander,tag=None):
		super().__init__(db,expander)
		self.tag=tag if tag else "XXX"
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.DB.HELP+"\n")
		elif query.command in Command.DUMP:
			try:
				args=docopt.docopt(Docs.DB.DUMP,query.args)
			except SystemExit as e:
				print(e)
				return
			titles=args["<titles>"].split(",") if args["-T"] else []
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			tags.append(self.tag)
			memo=args["<memo>"] or ""
			outputFname=args["<output>"] if args["-o"] else self.DEF_DUMP_FILE
			outputFname=_util.realpath(outputFname)
			dname=os.path.split(outputFname)[0]
			if not os.path.exists(dname):
				os.makedirs(dname)
			with open(outputFname,"w") as f:
				def dump_get_cols():
					for csm in __data__.CSM.make(self.db.text,self.db.search(memo,tags)):
						l=List.readCSM(csm)
						for c in l.searchRec(titles):
							for col in c.cols:
								yield util.Category.clean_as_tag(col)
				for col in set(dump_get_cols()):
					f.write(col+"\n")
			output.write("Written in {0}\n".format(outputFname))
		elif query.command in Command.WRITE:
			try:
				args=docopt.docopt(Docs.DB.WRITE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["c"] or args["category"]:
				csm=writeShell(self.tag)
				self.db.appendCSM(csm)
			else:
				return super().execQuery(query,output)
			self.db.save()
		elif query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.DB.APPEND,query.args)
			except SystemExit as e:
				print(e)
				print("query",query)
				return
			if args["c"] or args["category"]:
				if args["rec"]:
					titles=args["<titles>"]
					if len(titles) < 2:
						output.write("too less number of title.\n")
						return
					n=len(titles)
					for i in range(n-1):
						self.execQuery(__shell__.Query.read("append category {0} {1}".format(titles[i],titles[i+1])),output)
						output.write("Append {0} to {1}\n".format(titles[i],titles[i+1]))
				elif args["all"]:
					def append_all_titles():
						for card in self.db.search(tags=[self.tag]):
							userid=List.read(card.comment(self.db.text))
							for child in userid.head.childs:
								yield child.title
					titles=append_all_titles()
					all_title=self.ALL_TITLE
					self.db.append("T:"+all_title,"*"+all_title,[self.tag],str(datetime.datetime.now()).split(".")[0],True)
					#self.db.append("U:"+all_title,"*"+all_title+"\n-xxx",[TAG],str(datetime.datetime.now()).split(".")[0],True)
					for title in titles:
						if title == all_title:
							continue
						DBShell.execQuery(self,__shell__.Query.read("append category {0} {1}".format(title,all_title)),output)
					output.write("Append {0}\n".format("T:"+all_title))
				elif args["<srcTitles>"]:
					srcTitles=args["<srcTitles>"].split(",")
					dstTitles=args["<dstTitles>"].split(",")
					def get_src_cols(srcTitles):
						for csm in __data__.CSM.make(self.db.text,self.db.search(tags=[self.tag])):
							l=List.readCSM(csm)
							for c in l.__searchRec__(srcTitles):
								yield c
					srcUserids=list(get_src_cols(srcTitles))
					for csm in __data__.CSM.make(self.db.text,self.db.search(tags=[self.tag])):
						l=List.readCSM(csm)
						for c in list(l.__searchRec__(dstTitles)):
							titles=list(map(lambda child:child.title,c.childs))
							c.childs.extend(filter(lambda u:u.title not in titles,srcUserids))
						self.db.append(csm.memo,"\n".join(map(lambda child:str(child),l.head.childs)),csm.tags,csm.date,True)
							#for col in c.cols:
							#	f.write(util.Category.clean_as_tag(col)+"\n")
				elif args["csv"]:
#<col>:<root>,...
					fname=_util.realpath(args["<fname>"])
					title=args["<title>"] or str(_util.hash(fname))
					ct=util.CategoryTree(util.Category(title))
					with open(fname,"r") as f:
						for line in f:
							col,root=line.rstrip().split(";",1)
							root=root.split(",")
							cs=list(ct.searchRec(root))
							if not cs:
								ct.appendRoot(root=root)
								cs=ct.searchRec(root)
							for c in cs:
								#print("root",root,c.title)
								c.cols.append(col)
					self.db.appendCSM(__data__.CSM(self.TITLE_F.format(title),str(ct),[self.tag]))
				self.db.save()
			elif args["tot"] or args["totot"]:
				if args["csv"]:
					title=args["<title>"] or str(_util.hash(fname))
					title_f=self.TITLE_F.format(title)
					self.execQuery(__shell__.Query(("append","category","csv",args["<fname>"],title)),self.null)
					self.execQuery(__shell__.Query(("append","tot","-m",title_f)),self.null)
					#self.execQuery(__shell__.Query(("remove","-m",title_f)),self.null)
					print("Appended",title,"as tot",file=output)
				else:
					memo=args["<memo>"] if args["-m"] else ""
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					tags.append(self.tag)
					for csm in __data__.CSM.make(self.db.text,self.db.search(memo,tags)):
						for tot in util.Category.toTOT3(csm):
							self.db.appendTOT(tot.name,tot.childs)
			else:
				return super().execQuery(query,output)
		else:
			return super().execQuery(query,output)
				


class DUShell(__shell__.BaseHomeShell):
	PROMPT=":>>"
	TAG="XXX"
	DB_SHELL=DBShell
	def __init__(self,dushell):
		super().__init__(dushell.homeDB,self.DB_SHELL,prompt=self.PROMPT)
		self.null=_pyio.StringIO()
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		elif query.command in Command.CRAWL:
			try:
				args=docopt.docopt(Docs.CRAWL,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["-u"]:
				ids=[args["<userid>"]]
			else:	#args["-f"]
				fname=args["<idFname>"]
		elif query.command in Command.DUMP:
			try:
				args=docopt.docopt(Docs.DUMP,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"].upper()
			db=self.home.select(dbid,self.TAG)
			if not db:
				output.write(dbid+" Don't be found.\n")
				return
			query=__shell__.Query(["DUMP"])
			if args["-T"]:
				query.extend(("-T",args["<titles>"]))
			if args["-o"]:
				query.extend(("-o",args["<output>"]))
			return DBShell(db).execQuery(query,output)
		else:
			return super().execQuery(query,output)
	def select(self,args,output):
		try:
			args=docopt.docopt(Docs.SELECT,args)
		except SystemExit as e:
			print(e)
			return
		dbid=args["<dbid>"].upper()
		category_tag=args["<category_tag>"]
		query=args["<query>"]
		dbids=list(self.home.getDBIDs(dbid))
		if not dbids:
			return False
		dbid=dbids[0].upper()
		db=self.home.select(dbid)
		if not db:
			output.write(dbid.lower()+" doesn't exist.\n")
			return False
		expander=util.Expander(self.home,dbid)
		shell=self.DBShell(db,expander,category_tag)
		all_alias=os.path.join(self.home.dname,select2.AuHSShell.ALL_ALIAS_TXT)
		_util.touch(all_alias)
		shell.execAliasf(all_alias,self.null)
		if query:
			shell.execQuery(__shell__.Query(query),output)
		else:
			shell.start()
	def start(self):
		self.stdout.write("*** welcome to category shell! ***\n")
		return super().shell()

