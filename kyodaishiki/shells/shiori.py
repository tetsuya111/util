import sys
from kyodaishiki import __data__
from kyodaishiki import __shell__
from kyodaishiki import __utils__
from kyodaishiki import __server__
from . import util
from . import crawl as cr
import re
import docopt
import datetime

#TAG=b'\xe3\x81\x97\xe3\x81\x8a\xe3\x82\x8a'.decode()	#search by TAG
TAG="SHIORI"
MEMO_TAG="SHIORI_MEMO"

class Attr(util.Attr):
	SUPER_TITLE="SUPER_TITLE"	#csm.memo
	TITLE="TITLE"
	SUBTITLE="SUBTITLE"
	DATA="DATA"
attr_to_format=Attr.to_format

class Tag:
	IS_SHIORI="IS_SHIORI"
	IS_LIST="IS_SHIORI_LIST"

class Memo:
	SEQ=":"
	MEMO_OF_SHIORI=re.compile("[^\"\#]*:.*")
	def __init__(self,col,title="",subtitles=[]):
		if not re.match(self.MEMO_OF_SHIORI,col):
			raise Exception("It is not memo of shiori,")
		data,memo=self.split(col)
		self.memo=memo
		self.data=data
		self.title=title
		self.subtitles=subtitles
	@property
	def col(self):
		return self.data+Memo.SEQ+self.memo
	@staticmethod
	def split(col):
		return col.split(Memo.SEQ,1)

def getMemo(category):
	title=util.Category.clean_as_tag(category.title)
	for col in category.cols:
		if re.match(Memo.MEMO_OF_SHIORI,col):
			yield Memo(col,title)
	for child in category.childs:
		for memo in getMemo(child):
			yield Memo(memo.col,title,memo.subtitles+[memo.title])

def getCSM(category):
	title=util.Category.clean_as_tag(category.title)
	title_tag=attr_to_format(Attr.TITLE).format(title)
	subtitle_format=attr_to_format(Attr.SUBTITLE)
	for memo in getMemo(category):
		yield __data__.CSM(memo.memo,tags=(Tag.IS_SHIORI,title_tag,attr_to_format(Attr.DATA).format(memo.data),\
		*map(lambda subtitle:subtitle_format.format(subtitle),memo.subtitles)))


def __getShiori__(db,tags):
	res={}
	for csm in __data__.CSM.make(db.text,db.search(tags=tags)):
		attr_data=Attr.parse(csm.tags)
		if not attr_data.get(Attr.TITLE):
			continue
		title=attr_data[Attr.TITLE][0]
		data=attr_data[Attr.DATA][0]
		col=data+Memo.SEQ+csm.memo
		if not res.get(title):
			res[title]=util.Category(title)
		res[title].cols.append(col)
	return res.values()
def getShiori(db):
	return __getShiori__(db,[MEMO_TAG])

def makelist(csms,format_=lambda csm:":"+csm.memo):
	data={}
	for csm in csms:
		title=Attr.get(csm.tags,Attr.TITLE,[""])[0]
		if not title:
			continue
		if not data.get(title):
			data[title]=util.Category(title)
		data[title].cols.append(format_(csm))
	return data.values()

def makelistCSM(title,csms,format_=lambda csm:":"+csm.memo):
	l=makelist(csms,format_)
	return __data__.CSM(title,"\n".join(map(str,l)),[Tag.IS_LIST],str(datetime.datetime.now()).split(".",1)[0])


class Crawler(cr.Crawler):
	def __init__(self,db,crawlTV=60*60*24,ids=[],dbTags=[],limit=cr.DEFAULT_CRAWL_LIMIT):
		super().__init__(db,crawlTV,ids,dbTags,"",[TAG],limit)

class Manage(cr.BaseManage2):
	def start(self,name,dbid,crawlTV=60*60*24,ids=[],dbTags=[],limit=cr.DEFAULT_CRAWL_LIMIT,serve=False):
		return super().start(Crawler,name,dbid,dbTags,serve,crawlTV,ids,dbTags,limit)


class Docs(__utils__.Docs):
	APPEND="""
	Usage:
		append <srcid> <dstid>
	"""
	DUMP="""
	Usage:
		dump <srcid> <dstid>
	"""
	class Crawl:
		START="""
		Usage:
			start ((-u <userid>)|(-f <idFname>)) <dbid> [(-n <crawlerName>)] [(--dt <dbTags>)] [(--tv <crawlTV>)] [--serve]
		"""
	HELP="""
$ append <srcid> <dstid>
$ dump <srcid> <dstid>
	"""

class Command(__utils__.Command):
	START=("ST","START")
	CRAWL=("CR","CRAWL")
	DUMP=("D","DUMP")

class CrawlShell(cr.BaseShell):
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write("""
	start ((-u <userid>)|(-f <idFname>)) <dbid> [(-n <crawlerName>)] [(--dt <dbTags>)] [(--tv <crawlTV>)] [--serve]
			\n""")
		if query.command in Command.START:
			try:
				args=docopt.docopt(Docs.Crawl.START,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["-u"]:
				ids=[args["<userid>"]]
			else:
				ids=__server__.readIDFile(args["<idFname>"])
			dbid=args["<dbid>"]
			crawlerName=args["<crawlerName>"] if args["-n"] else "crawler_{0}".format(self.manage.n)
			dbTags=args["<dbTags>"].upper().split(",") if args["--dt"] else []
			crawlTV=args["<crawlTV>"] if args["--tv"] else 60*60*24
			serve=args["--serve"]
			limit=cr.DEFAULT_CRAWL_LIMIT
#def start(self,name,dbid,crawlTV=60*60*24,ids=[],dbTags=[],limit=cr.DEFAULT_CRAWL_LIMIT,serve=False):
			self.manage.start(crawlerName,dbid,crawlTV,ids,dbTags,limit,serve)
		else:
			return super().execQuery(query,output)

class DBShell(__shell__.DBShell):
	def search(self,args,output):
		try:
			args=docopt.docopt(Docs.SEARCH,args)
		except SystemExit as e:
			print(e)
			return
		if args["-T"] or args["--title"]:
			tags.append(attr_to_format(Attr.TITLE).format(args["<title>"]))
		if args["--st"]:
			tags.append(attr_to_format(Attr.TITLE).format(args["<subtitle>"]))

class DUShell(__shell__.BaseShell):
	PROMPT=":>"
	def __init__(self,dushell):
		self.homeDB=dushell.homeDB
		self.manage=Manage(self.homeDB)
		super().__init__(prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		elif query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			srcid=args["<srcid>"].upper()
			dstid=args["<dstid>"].upper()
			srcDB=self.homeDB.select(srcid)
			if not srcDB:
				output.write("Don't find {0}.\n".format(srcid))
				return
			dstDB=self.homeDB.select(dstid)
			if not dstDB:
				self.homeDB.append(dstid,[MEMO_TAG])
				dstDB=self.homeDB.select(dstid)
			else:
				cards=srcDB.search(tags=[TAG])
				convertAsCSM=getCSM
			for csm in __data__.CSM.make(srcDB.text,cards):
				tags=list(filter(lambda tag:tag!=TAG,csm.tags))+[attr_to_format(Attr.SUPER_TITLE).format(csm.memo)]		#remove TAG
				for category in util.Category.read(csm.comment):
					for csm__ in convertAsCSM(category):
						csm__.tags=(*csm__.tags,*tags)
						dstDB.appendCSM(csm__)
						output.write("Append "+csm__.memo+" to "+dstid+".\n")
		elif query.command in Command.DUMP:
			try:
				args=docopt.docopt(Docs.DUMP,query.args)
			except SystemExit as e:
				print(e)
				return
			srcid=args["<srcid>"].upper()
			dstid=args["<dstid>"].upper()
			srcDB=self.homeDB.select(srcid)
			if not srcDB:
				output.write("Don't find {0}.\n".format(srcid))
				return
			dstDB=self.homeDB.select(dstid)
			if not dstDB:
				self.homeDB.append(dstid,[TAG])
				dstDB=self.homeDB.select(dstid)
			comment="\n".join(map(str,getShiori(srcDB)))
			csm=__data__.CSM(srcid+" "+TAG,comment,("DBID:"+srcid,TAG),str(datetime.datetime.now()))
			dstDB.appendCSM(csm)
			output.write("Append {0} to {1}\n".format(csm.memo,dstid))

		elif query.command in Command.CRAWL:
			if query.args:
				query=__shell__.Query(query.args)
				return CrawlShell(self.manage).execQuery(query,output)
			else:
				return CrawlShell(self.manage).start()
		else:
			return super().execQuery(query,output)
	def start(self):
		self.stdout.write("**** welcome to shiori shell ***\n")
		super().start()
		#self.manage.close()

