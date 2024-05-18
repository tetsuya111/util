from kyodaishiki import __shell__
from kyodaishiki import _util
from kyodaishiki import __db__
from kyodaishiki import __data__
from kyodaishiki import __index__
from . import select2
from . import util
import os
import sys
import random
import _pyio
import docopt
import datetime
import re

TAG="REVIEW"

COMMENT_SEQ="\n-\n"

class Attr(util.Attr):
	POINT="POINT"
	SORT_OF="SORT_OF"
	PRICE="PRICE"

class ReviewCard(__index__.Card):
	def __init__(self,memoIdx=__index__.Index(),commentIdx=__index__.Index(),tagIdxes=list(),date=str(datetime.datetime.now()).split(".")[0]):
		super().__init__(memoIdx,commentIdx,tagIdxes,date)
		self.__point=-1
		self.__price=-1
	def point(self,text):
		if self.__point < 0:
			self.__point=getPoint(self.tags(text))
		return self.__point
	def price(self,text):
		if self.__price < 0:
			self.__price=int(Attr.get(self.tags(text),Attr.PRICE,[0])[0])
		return self.__price
	@staticmethod
	def make(cards):
		return map(lambda card:ReviewCard(card.memoIdx,card.commentIdx,card.tagIdxes,card.date),cards)

def write_shell(output=sys.stdout):
	output.write("Name:")
	name=input()
	output.write("Point:")
	point=int(input())
	output.write("Price:")
	price=int(input())
	output.write("Comment(one liner):")
	comment=input()
	sortofs=list(_util.inputUntilSeq("Sort of:",output=output))
	return __data__.CSM(name,comment,(*map(lambda sortof:Attr(Attr.SORT_OF)(sortof),sortofs),Attr(Attr.POINT)(point),Attr(Attr.PRICE)(price),TAG),str(datetime.datetime.now()).split(".",1)[0])

def getPoint(tags):
	return int(Attr.get(tags,Attr.POINT,[0])[0])

def __search__(db,name="",sortsof=[],fromP=0,untilP=100,tags=[]):
	tags=(*tags,*map(lambda sortof:Attr(Attr.SORT_OF)(sortof),sortsof)) if sortsof else tags
	for card in ReviewCard.make(db.search(name,tags=tags)):
		if fromP <= card.point(db.text) <= untilP:
			yield card
def search(db,name="",sortsof=[],fromP=0,untilP=100):
	return __search__(db,name,sortsof,fromP,untilP,[TAG])
	


class Docs:
	WRITE="""
	Usage:
		write (re|review)
		write tot
		write
	"""
	GET="""
	Usage:
		get (so|sortof) [<sortof>]
		get <sortsof> [(--fp <fromP>)] [(--up <untilP>)] [(--fpr <fromPrice>)] [(--upr <untilPrice>)]
		get [(-n <name>)] [(-s <sortsof>|--sortof <sortsof>)] [(--fp <fromP>)] [(--up <untilP>)] [(--fpr <fromPrice>)] [(--upr <untilPrice>)]
	"""
	HELP="""
		help [(-a|--all)]
		write
		get
	"""
class Command(select2.Command):
	GET=("G","GET")

class DBShell(select2.DBShell):
	def execQuery(self,query,output):
		if query.command in  Command.HELP:
			output.write(Docs.HELP+"\n")
			if query.args and query.args[0] in ("-a","--all"):
				return super().execQuery(query,output)
		elif query.command in  Command.WRITE:
			try:
				args=docopt.docopt(Docs.WRITE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["re"] or args["review"]:
				csm=write_shell()
				point=int(Attr.get(csm.tags,Attr.POINT)[0])
				if not 0<=point<=100:
					output.write("Point isn't between 0 and 100.\n")
					return
				self.db.appendCSM(csm)
			else:
				return super().execQuery(query,output)
		elif query.command in  Command.GET:
			try:
				args=docopt.docopt(Docs.GET,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["so"] or args["sortof"]:
				sortof=args["<sortof>"] if args["<sortof>"] else ""
				sos=Attr.get(self.db.getTags(),Attr.SORT_OF)
				sos=filter(lambda so:re.search(sortof,so),sos)
				data=map(lambda so:(so,len(self.db.tag[self.db.find(Attr(Attr.SORT_OF)(so))])),sos)
				data=sorted(data,key=lambda data__:data__[1])
				for so,n in data:
					output.write("{0} {1}\n".format(so,n))
				return
			name=args["<name>"] if args["-n"] else ""
			sortsof=args["<sortsof>"].upper().split(",") if args["<sortsof>"] else []
			fromP=int(args["<fromP>"]) if args["--fp"] else 0
			untilP=int(args["<untilP>"]) if args["--up"] else 100
			fromPrice=int(args["<fromPrice>"]) if args["--fpr"] else 0
			untilPrice=int(args["<untilPrice>"]) if args["--upr"] else 10*64
			text=""
			cards=search(self.db,name,sortsof,fromP,untilP)
			cards=sorted(cards,key=lambda card:card.point(self.db.text))
			for card in cards:
				if not fromPrice <= card.price(self.db.text) < untilPrice:
					continue
				csm=__data__.CSM.makeOne(self.db.text,card)
				text+="* {0} -> [{1}] {2}\n".format(card.memo(self.db.text),card.point(self.db.text),card.comment(self.db.text).split(COMMENT_SEQ,1)[0])
				#text+="-"*75+"\n"
			output.write(text)
		else:
			return super().execQuery(query,output)

class DUShell(__shell__.BaseShell):
	PROMPT=">>"
	def __init__(self,dushell):
		super().__init__(prompt=self.PROMPT)
		self.DBShell=DBShell
		self.homeDB=dushell.homeDB
	def execQuery(self,query,output):
		dbid=query.command.upper()
		if not dbid:
			output.write("Select dbid.\n")
			return
		db=self.homeDB.select(dbid)
		if not db:
			output.write("Don't find {0}.\n".format(dbid.lower()))
			return
		alias_txt=os.path.join(self.homeDB.dname,select2.AuHSShell.ALL_ALIAS_TXT)
		try:
			shell=self.DBShell(db)
			shell.execAliasf(alias_txt,_pyio.StringIO())
			shell.start()
		except Exception as e:
			output.write(str(e)+"\n")
	def start(self):
		return self.execQuery(__shell__.Query(),self.stdout)


