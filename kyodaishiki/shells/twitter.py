import sys

sys.path.append(r"C:\Users\tetsu\code\kyodaishiki2")

from kyodaishiki import __shell__
from . import util
import docopt
import datetime

DEFAULT_FROM_UNTIL="1900-1-1,2200-45-45"
SEQ_BETWEEN_FROM_AND_UNTIL=","

class Type:
	TWEET="TWEET"
	USER_INFO="USER_INFO"

class Tweet(util.Tree.Node):
	TAG="TWEET"
	class Title:
		TWEET="Tweet"
		RES_LIST="List of res"
	class Attr(util.Attr):
		ID="ID"
		NAME="NAME"
		FAV="FAV"
		RT="RT"
	def __init__(self,data,id_,name="",fav=0,rt=0,date=datetime.datetime(1900,1,1),res=[],fname=""):
		super().__init__((data,id_,name,fav,rt,date,fname),res)
	@property
	def tweet(self):
		return self.data[0]
	@property
	def id(self):
		return self.data[1]
	@property
	def name(self):
		return self.data[2]
	@property
	def fav(self):
		return self.data[3]
	@property
	def rt(self):
		return self.data[4]
	@property
	def date(self):
		return self.data[5]
	@property
	def fname(self):
		return self.data[6]
	@property
	def res(self):
		return self.childs
	def tocsm(self):
		tweet=self.tweet.split("\n")
		comment=str(util.Category(self.Title.TWEET,tweet))+"\n"+str(util.Category(self.Title.RES_LIST,map(lambda res:res.fname,self.res)))
		tags=(util.Attr(self.Attr.ID)(self.id),util.Attr(self.Attr.NAME)(self.name),\
		util.Attr(self.Attr.FAV)(self.fav),util.Attr(self.Attr.RT)(self.rt))
		return __data__.CSM(tweet[0],comment,tags,str(self.date))
	def __str__(self):
		return str(self.tocsm())
	@staticmethod
	def read(expander,csm):
		Attr=Tweet.Attr
		data=""
		childs=[]
		for cate in util.Category.read(csm.comment):
			title=util.Category.clean_as_tag(cate.title)
			if title==Tweet.TITLE.Tweet:
				data="\n".join(cate.get_cols())
			elif title==Tweet.TITLE.RES_LIST:
				for col in cate.get_cols():
					for csm in expander.getCSM(col):
						childs.append(Tweet.read(csm))
		attrs=Attr.parse(csm.tags)
		id_=attrs[Attr.ID][0] if attrs[Attr.ID] else ""
		name=attrs[Attr.NAME][0] if attrs[Attr.NAME] else ""
		fav=int(attrs[Attr.FAV][0]) if attrs[Attr.FAV] else 0
		rt=int(attrs[Attr.RT][0]) if attrs[Attr.RT] else 0
		date=util.to_datetime(csm.date)
		return Tweet(data,id_,name,fav,rt,date,childs,csm.fname)
	@staticmethod
	def readf(fname):
		return Tweet.read(__data__.CSM.read(fname))

		
	

class Docs:
	APPEND="""
	Usage:
		append <dbid> <userid> [(--date <date_from,until>)]
	"""

class Command(util.Command):pass

class SiteShell(__shell__.BaseShell):
	PROMPT=":>>"
	def __init__(self,homeDB):
		self.homeDB=homeDB
		super().__init__(prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"].upper()
			userid=args["<userid>"]
			from_until=args["<date_from,until>"] if args["--date"] else DEFAULT_FROM_UNTIL
			from_,until=map(int,from_until.split(DEFAULT_FROM_UNTIL,1))
			for csm in getCSM(userid,from_,until):
				db.appendCSM(csm)
		else:
			return super().execQuery(query,output)
	def start(self):
		self.stdout.write("*** welcome to twitter ***\n")
		return super().start()

#SiteShell(None).execQuery(__shell__.Query(("APPEND","ttt","--date","2019-2-12,2020-1-1")),sys.stdout)
