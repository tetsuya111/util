from . import category
from . import select2
from . import util
from . import shiori
from kyodaishiki import __data__
from kyodaishiki import __shell__
from kyodaishiki import _util
from kyodaishiki import __db__
import docopt
import os
import sys
import re
import random
import datetime
from functools import *
import _pyio

READ="READ"
SAW="SAW"


class Attr(shiori.Attr):
	TITLE="TITLE"
	AUTHOR="AUTHOR"
	P_L="P_L"

class EnvKey:
	SHIORI_TITLE="SHIORITITLE"
	SHIORI_TAGS="SHIORITAGS"
	BOOK_TAGS="BOOKTAGS"

AUTHOR_NAME_F="<{0}>"

def is_book(csm):
	return any(map(lambda tag:tag in csm.tags,(READ,SAW)))

class Tag:
	#IS_BOOK=__data__.Logic.OR.join((SAW,READ))
	IS_BOOK="IS_BOOK"
	IS_SHIORI="IS_SHIORI"
	WANNA_READ="WANNA_READ"
	SAW="SAW"
	READ="READ"
	WANT="WANT"

def alter(db,card):
	tags=card.tags(db.text)
	if Tag.READ in tags:
		db.removeTags(card.id,[Tag.READ])
		db.appendTags(card.id,[Tag.SAW])
	elif Tag.SAW in tags:
		db.removeTags(card.id,[Tag.SAW])
		db.appendTags(card.id,[Tag.READ])


def count_title(db,author):
	return len(list(search(db,author=author)))

def writeAuthor(output=sys.stdout):
	output.write("Name:")
	name=AUTHOR_NAME_F.format(input())
	titles=[]
	while True:
		output.write("Title:")
		title=input()
		if not title:
			break
		titles.append(title)
	return __data__.TOT.make2(name,titles)

class Shiori:
	TAG=Tag.IS_SHIORI
	def __init__(self,db):
		self.db=db
	def dumpCSM(self):
		return self.db.search(tags=[self.TAG])
	def search(self,memo="",tags=[],title="",author="",p_from=0,p_until=10000):
		if author:
			book_titles=getBookTitles(self.db,author)
			tags=(*tags,__data__.Logic.OR.join(map(lambda book_title:Attr(Attr.TITLE)(book_title),book_titles)))
		if title:
			tags=(*tags,Attr(Attr.TITLE)(title))
		for card in self.db.search(memo,(self.TAG,*tags)):
			p_l=Attr.get(card.tags(self.db.text),Attr.P_L)
			p=p_l[0].split("_")[0] if p_l else 0
			try:
				p=int(p)
			except:
				p=0
			if p_from <= p < p_until:
				yield card
	def getTitles(self):
		return set(reduce(lambda a,b:a+b,map(lambda card:Attr.get(card.tags(self.db.text),Attr.TITLE),self.search())))
	def count_of_title(self,title):
		attr_title=Attr(Attr.TITLE)
		return len(list(self.db.tag.get(self.db.find(attr_title(title)),[])))
	@staticmethod
	def getCSM(bookcsm):
#get shiori in bookcsm as CSM.
		cates=list(filter(lambda cate:cate.title==Shiori.TAG,util.Category.read(bookcsm.comment)))
		if not cates:
			return
		for cate in cates:
			cate.title=bookcsm.memo
			for csm in shiori.getCSM(cate):
				attr_tags=util.AttrTags.read(csm.tags)
				#attr_tags.removes(Attr.TITLE)
				#attr_tags.append(Attr.TITLE,bookcsm.memo)
				data=attr_tags.get(Attr.DATA)
				if data:
					data=data[0]
					attr_tags.removes(Attr.DATA)
					p_l=data.replace(",","_")
				else:
					p_l="0_0"
				attr_tags.append(Attr.P_L,p_l)
				csm.tags=(*attr_tags.dump(),Shiori.TAG)
				csm.date=bookcsm.date
				yield csm
			
	@staticmethod
	def write(output=sys.stdout):
		output.write("P:")
		p=input() or 0
		output.write("L:")
		l=input() or 0
		csm=__shell__.Shell.write()
		csm.tags.append(Attr(Attr.P_L)("{0}_{1}".format(p,l)))
		csm.tags.append(Tag.IS_SHIORI)
		return csm
	
	@staticmethod
	def list_format(csm):
		p_l=Attr.get(csm.tags,Attr.P_L)
		p_l=p_l[0] if p_l else "0_0"
		return p_l+":"+csm.memo
	@staticmethod
	def makelistCSM(title,csms):
		return shiori.makelistCSM(title,csms,Shiori.list_format)
		
	


class Book(__data__.CSM):
	BOOK_TAG="BOOK"
	def getShiori(self):
		return Shiori.getCSM(self)
	def getRelated(self):
		res={}
		for cate in util.Category.read(self.comment):
			if not res.get(cate.title):
				res[cate.title]=[]
			#res[cate.title].extend(filter(lambda col:col,map(lambda col:util.Category.clean_as_tag(col),cate.get_cols())))
			res[cate.title].extend(cate.get_cols())
		return res
	def getBooks(self):
		return self.getRelated().get(self.BOOK_TAG,[])
	@property
	def title(self):
		return self.memo
	@staticmethod
	def convert(csm):
		return Book(csm.memo,csm.comment,csm.tags,csm.date)
	@staticmethod
	def write(db,output=sys.stdout):
		output.write("Author:")
		author=input()
		output.write("Title:")
		title=input()
		output.write("S(aw) or R(ead) or W(ant) : ")
		tag=input().upper()
		if tag == "S":
			tag=Tag.SAW
		elif tag == "R":
			tag=Tag.READ
		elif tag == "W":
			tag=Tag.WANT
		else:
			raise Exception("{0} not in S or R or W.".format(tag))
		#if tag not in (SAW,READ):
		#	raise Exception("your input data is not SAW or WRITE.")
		tags=list(_util.inputUntilSeq("Tags:"))
		tots=list(searchAuthorTOT(db,"{0}".format(author)))
		tot=__data__.TOT.make2(AUTHOR_NAME_F.format(author),[]) if not tots else tots[0]
		db.appendTOT(tot.name,(*tot.childs,title),True)
		return __data__.CSM(title,"",(*tags,tag,Tag.IS_BOOK),str(datetime.datetime.now()).split(".")[0])

def __searchAuthorTOT__(db,name=".*"):
	return db.searchTOT("<{0}>".format(name))
def searchAuthorTOT(db,name=".*"):
	return __data__.TOT.make(db.text,__searchAuthorTOT__(db,name))
def searchAuthor(db,name=".*"):
	for tot in searchAuthorTOT(db,name):
		yield re.search("<(?P<name>.*)>",tot.name).group("name")

def getBookTitles(db,author=".*",U=None):
	if not U:
		U=db.getU()
	author=__data__.Logic.OR.join(map(lambda author:AUTHOR_NAME_F.format(author),searchAuthor(db,author)))
	#author=AUTHOR_NAME_F.format(author)
	return filter(lambda title:not re.fullmatch("<.+>",title),db.getTagsRec([author],U))


def __search__(db,tags=[],title="",author=""):
	U=db.getU()
	if author:
		book_titles=util.reduce(util.addMemo,getBookTitles(db,author,U),"")
	else:
		book_titles=""
	for card in db.search(tags=tags):
		memo=card.memo(db.text)
		if re.match(book_titles,memo.upper()) and re.search(title,memo):
			yield card

def search(db,tags=[],title="",author=""):
#search of IS_BOOK
	tags=(*tags,Tag.IS_BOOK)
	return __search__(db,tags,title,author)

def getBooksAsTOT(db,tags=[],title="",author=""):
	name="READ_BOOKS"
	return __data__.TOT.make2(name,map(lambda card:card.memo(db.text),search(db,tags,title,author)))
	

def getRelated(db,tags=[],title="",author="",relatedTags=[]):
	res={}
	for csm in __data__.CSM.make(db.text,search(db,tags,title,author)):
		book=Book.convert(csm)
		related=book.getRelated()
		for key in related:
			if not res.get(key):
				res[key]=util.Category(key)
			res[key].childs.append(util.Category(csm.memo,list(related[key]),[]))
			#print(key,related[key],res[key].childs)
	if not relatedTags:
		return res
	return dict(map(lambda key:(key,res[key]),filter(lambda key:key in relatedTags,res)))



class Docs:
	class DB:
		ALTER="""
		Usage:
			alter [(-t <tags>)] [(-T <title>)] [(-a <author>)]
		"""
		SEARCH_CARD="""
		Usage:
			search_card (b|book) [(-t <tags>)] [(-T <title>)] [(-a <author>)] 
			search_card (sh|shi|shiori) [(-m <memo>)] [(-t <tags>)] [(-T <title>)] [(-a <author>)] [(--pf <p_from>)] [(--pu <p_until>)]
			search_card [(-t <tags>)] [(--nt <noTags>)] [(-m <memo>)] [(--mm <lowUpMemo>)] [(--em <escapedMemo>)] [(-c <comment>)] [(-F <from>)] [(-U <until>)] [(-u <userid>)] [(-D <dbid>)] [(--pn|--printNot)]
		"""
		SEARCH="""
		Usage:
			search (b|book) [(-t <tags>)] [(-T <title>)] [(-a <author>)] [(-p <pMode>)] [(-r|--random)]
			search (sh|shi|shiori) [(-m <memo>)] [(-t <tags>)] [(-T <title>)] [(-a <author>)] [(--pf <p_from>)] [(--pu <p_until>)] [(-p <pMode>)] [(-r|--random)]
			search [(-t <tags>)] [(-m <memo>)] [(-c <comment>)] [(-p <pMode>)] [(-r|--random)]
		"""
		APPEND="""
		Usage:
			append (sh|shi|shiori) [(-t <tags>)] [(-T <title>)] [(-a <author>)] [(-O|--override)]
			append (sh|shi|shiori) (l|list) <list_title> [(-m <memo>)] [(-t <tags>)] [(-T <title>)] [(-a <author>)] [(--pf <p_from>)] [(--pu <p_until>)]
			append related [(-t <tags>)] [(-T <title>)] [(-a <author>)] [(--rt <relatedTags>)] [(-O|--override)]
			append tag [(-t <tags>)] [(-m <memo>)] <tagsToAppend>... 
		"""
		LIST="""
		Usage:
			list (au|author) [(-n <name>)]
			list (ti|title) (sh|shi|shiori) [(-T <title>)] [(-r|--random)]
			list (ti|title) [(-T <title>)] [(-a <author>)]
			list tot [<tag>] [(-a|--all)]
			list (t|tag) [<tag>] [(-r|--random)]
		"""
		WRITE="""
		Usage:
			write (b|book)
			write (au|author)
			write (sh|shi|shiori) [(-t <tags>)] [(-T <title>)] 
			write tot
			write 
		"""
		DUMP="""
		Usage:
			dump (s|saw|r|read) [(-o output)] [(-t <tags>)] [(-T <title>)] [(-a <author>)] 
			dump (w|want) [(-T <titles>)] [(-o <output>)] [(-t <tags>)] [(-m <memo>)]
		"""
		HELP="""
			append
			search
			alter
			author
			title
			write
		"""
	ALTER="""
	Usage:
		alter <dbid> [(-t <tags>)] [(-T <title>)]
	"""
	HELP="""
		alter <dbid> [(-t <tags>)] [(-T <title>)]
	"""

class Command(select2.Command):
	ALTER=("AL","ALTER")
	AUTHOR=("AU","AUTHOR")
	TITLE=("TI","TITLE")

class DBShell(select2.DBShell):
	DEF_TITLE=b'(\xe6\x9c\xac)|(books)'.decode()
	def __init__(self,db,*args,**kwargs):
		super().__init__(db,*args,**kwargs)
		se2_alias=os.path.join(os.path.split(self.db.dname)[0],select2.AuHSShell.ALL_ALIAS_TXT)
		self.execAliasf(se2_alias,self.null)
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.DB.HELP+"\n")
			if query.args and query.args[0] in ("-a","--all"):
				return super().execQuery(query,output)
		elif query.command in Command.ALTER:
			try:
				args=docopt.docopt(Docs.DB.ALTER,query.args)
			except SystemExit as e:
				print(e)
				return
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			tags.append(Tag.IS_BOOK)
			title=args["<title>"] if args["-T"] else ""
			data=""
			for card in self.db.search(memo=title,tags=tags):
				csm=__data__.CSM.makeOne(self.db.text,card)
				alter(self.db,card)
				data+="Altered {0}\n".format(csm.memo)
			output.write(data)
			self.db.save()
		elif query.command in Command.SEARCH_CARD:
			try:
				args=docopt.docopt(Docs.DB.SEARCH_CARD,query.args)
			except SystemExit as e:
				print(e)
				return
			#search_card (b|book) [(-t <tags>)] [(-T <title>)] [(-a <author>)] 
			#search_card (sh|shi|shiori) [(-m <memo>)] [(-t <tags>)] [(-T <title>)] [(-a <author>)] [(--pf <p_from>)] [(--pu <p_until>)]
			if args["b"] or args["book"]:
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				tags.append(Tag.IS_BOOK)
				title=args["<title>"] or ""
				author=args["<author>"] or ""
				return search(self.db,tags,title,author)
			elif args["sh"] or args["shi"] or args["shiori"]:
				memo=args["<memo>"] or ""
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				title=args["<title>"] or ""
				author=args["<author>"] or ""
				p_from=args["<p_from>"] or 0
				p_from=int(p_from)
				p_until=args["<p_until>"] or 10000
				p_until=int(p_until)
				return Shiori(self.db).search(memo,tags,title,author,p_from,p_until)
			else:
				return super().execQuery(query,output)
		elif query.command in Command.SEARCH:
			try:
				args=docopt.docopt(Docs.DB.SEARCH,query.args)
			except SystemExit as e:
				print(e)
				return
			#tags=args["<tags>"].upper().split(",") if args["-t"] else []
			args__,_,_=util.partitionArgs(query.args,["-p","-r","--random"])
			cards=self.execQuery(__shell__.Query(("search_card",*args__)),output)
			cards=list(cards)
			pMode=args["<pMode>"] or ""
			pMode=pMode.upper()+"M"
			random_=args["-r"] or args["--random"]
			if random_:
				cards=list(cards)
				random.shuffle(cards)
			else:
				cards=sorted(cards,key=lambda card:card.date)
			data=""
			for csm in __data__.CSM.make(self.db.text,cards):
				data+="* "+csm.dump(pMode)+"\n"
				data+="------------------------------------------------\n"
			output.write(data)
		elif query.command in Command.DUMP:
			try:
				args=docopt.docopt(Docs.DB.DUMP,query.args)
			except SystemExit as e:
				print(e)
				return
			issaw=args["s"] or args["saw"]
			isread=args["r"] or args["read"]
			if issaw or isread:
			#dump (s|saw|r|read) [(-o output)] [(-t <tags>)] [(-T <title>)] [(-a <author>)] 
				_,_,args__=util.partitionArgs(query.args,("s","saw","r","read","-o"))
				query=__shell__.Query(("search_card","book",*args__))
				fname=args["<output>"] or category.DBShell.DEF_DUMP_FILE
				cards=self.execQuery(query,output)
				tag=Tag.SAW if issaw else Tag.READ
				cards=filter(lambda card:tag in card.tags(self.db.text),cards)
				with open(fname,"w") as f:
					for card in cards:
						book_title=card.memo(self.db.text)
						print(book_title,file=f)
			elif args["w"] or args["want"]:
				up,_,low=util.partitionArgs(query.args,("w","want"))
				if not low or low[0] != "-T":
					low=("-T",self.DEF_TITLE,*low)
				query=__shell__.Query(("dump",*low))
				return category.DBShell(self.db,None,None,tag=Tag.WANT).execQuery(query,output)
		elif query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.DB.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["sh"] or args["shi"] or args["shiori"]:
				if args["l"] or args["list"]:
					list_title=args["<list_title>"]
					memo=args["<memo>"] if args["-m"] else ""
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					p_from=int(args["<p_from>"]) if args["--pf"] else 0
					p_until=int(args["<p_until>"]) if args["--pu"] else 100000
					title=args["<title>"] if args["-T"] else ""
					if args["-a"]:
						author=args["<author>"]
						book_titles=getBookTitles(self.db,author)
						tags.append(__data__.Logic.OR.join(map(lambda book_title:Attr(Attr.TITLE)(book_title),book_titles)))
					cards=Shiori(self.db).search(memo,tags,title,p_from,p_until)
					csms=__data__.CSM.make(self.db.text,cards)
					csm=Shiori.makelistCSM(list_title,csms)
					self.db.appendCSM(csm)
					print(csm.memo,file=output)
				else:
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					title=args["<title>"] if args["-T"] else ""
					author=args["<author>"] if args["-a"] else ""
					override=args["-O"] or args["--override"]
					data=""
					for bookcsm in __data__.CSM.make(self.db.text,search(self.db,tags,title,author)):
						for csm in Shiori.getCSM(bookcsm):
							if self.db.appendCSM(csm,override):
								data+="Append {0}\n".format(csm.memo)
					output.write(data)
			elif args["related"]:
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				title=args["<title>"] if args["-T"] else ""
				author=args["<author>"] if args["-a"] else ""
				relatedTags=args["<relatedTags>"].split(",") if args["--rt"] else ""
				override=args["-O"] or args["--override"]
				comment=""
				related=getRelated(self.db,tags,title,author,relatedTags=relatedTags)
				for key in related:
					comment+=str(related[key])+"\n"
					#comment+="*"+key+"\n"+"\n".join(map(lambda col:"-"+col,related[key]))+"\n"
				self.db.append("Related",comment.rstrip(),["related",Tag.WANNA_READ,"WANT"],override=override)
				output.write("Append Related.\n")

			else:
				return super().execQuery(query,output)
		elif query.command in Command.LIST:
			try:
				args=docopt.docopt(Docs.DB.LIST,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["au"] or args["author"]:
				name=args["<name>"] if args["-n"] else ""
				name=".*"+name+".*"
				name=AUTHOR_NAME_F.format(name)
				data=""
				for tot in __data__.TOT.make(self.db.text,self.db.searchTOT(name)):
					name=re.search("<(?P<name>.*)>",tot.name).group("name")
					data+="{0} {1}\n".format(name,count_title(self.db,name))
				output.write(data)
			elif args["ti"] or args["title"]:
				title=args["<title>"] if args["-T"] else ""
				if args["sh"] or args["shi"] or args["shiori"]:
					text=""
					sh=Shiori(self.db)
					titles=sh.getTitles()
					data=map(lambda title:(title,sh.count_of_title(title)),titles)
					if args["-r"] or args["--random"]:
						data=list(data)
						random.shuffle(data)
					else:
						data=sorted(data,key=lambda x:x[1])
					for title__,n in data:
						if re.search(title,title__):
							text+="* "+title__+" "+str(n)+"\n"
					output.write(text)
				else:
					author=args["<author>"] if args["-a"] else ".*"
					data=""
					for title__ in getBookTitles(self.db,author):
						if re.search(title,title__):
							data+="* "+title__+"\n"
					output.write(data)
			else:
				return super().execQuery(query,output)
		elif query.command in Command.WRITE:
			try:
				args=docopt.docopt(Docs.DB.WRITE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["b"] or args["book"]:
				csm=Book.write(self.db)
				if self.environ.get(EnvKey.BOOK_TAGS):
					csm.tags=(*csm.tags,*self.environ[EnvKey.BOOK_TAGS].upper().split(","))
				self.db.appendCSM(csm)
			elif args["au"] or args["author"]:
				tot=writeAuthor()
				self.db.appendTOT(tot.name,tot.childs)
				self.db.save()
			elif args["sh"] or args["shi"] or args["shiori"]:
				tags=args["<tags>"].upper().split(",") if args["-t"] else self.environ.get(EnvKey.SHIORI_TAGS,"").upper().split(",")
				title=args["<title>"] if args["-T"] else self.environ.get(EnvKey.SHIORI_TITLE,"UNKNOWN")
				csm=Shiori.write()
				if title:
					csm.tags.append(Attr(Attr.TITLE)(title))
				csm.tags.extend(tags)
				self.db.appendCSM(csm)
				self.db.save()
			else:
				return super().execQuery(query,output)
		else:
			return super().execQuery(query,output)

class DUShell(__shell__.BaseHomeShell):
	PROMPT="::>"
	def __init__(self,dushell):
		super().__init__(dushell.homeDB,DBShell,prompt=self.PROMPT)
		self.null=_pyio.StringIO()
		self.environ={}
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
			if query.args and query.args[0] in ("-a","--all"):
				return super().execQuery(query,output)
		elif query.command in Command.ALTER:
			try:
				args=docopt.docopt(Docs.ALTER,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"].upper()
			db=self.home.select(dbid)
			if not db:
				output.write("Don't find {0}.\n".format(dbid.lower()))
				return
			query=__shell__.Query(["alter"])
			if args["-t"]:
				query,extend(("-t",args["<tags>"]))
			if args["-T"]:
				query,extend(("-T",args["<title>"]))
			return self.DBShell(db).execQuery(query,output)
		else:
			return super().execQuery(query,output)
	def select(self,args,output):
		query=__shell__.Query(args)
		dbids=list(self.home.getDBIDs(query.command))
		if not dbids:
			return False
		dbid=dbids[0].upper()
		db=self.home.select(dbid)
		if not db:
			output.write(dbid.lower()+" doesn't exist.\n")
			return False
		expander=util.Expander(self.home,dbid)
		shell=DBShell(db,expander,self.environ)
		all_alias=os.path.join(self.home.dname,select2.AuHSShell.ALL_ALIAS_TXT)
		_util.touch(all_alias)
		shell.execAliasf(all_alias,self.null)
		if query.args:
			shell.execQuery(__shell__.Query(query.args),output)
		else:
			shell.start()
	def start(self):
		self.stdout.write("*** welcome to shell for book. ***\n")
		return super().shell()


