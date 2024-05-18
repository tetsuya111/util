from kyodaishiki import __server__
from kyodaishiki import __dns__
from kyodaishiki import __utils__
from kyodaishiki import __shell__
from . import select2
from . import util
import time
import os
import threading
import docopt
import queue
import sys
import re

DEFAULT_CRAWL_TV=1
DEFAULT_CRAWL_LIMIT=50
MAX_CRAWL=5
DEFAULT_CRAWL_DIR=__utils__.realpath("%USERPROFILE%\\Desktop\\KyodaishikiCrawled")

DEFAULT_HOST="127.0.0.1"

DEFAULT_DUMP_SECOND_FORMAT="{0}d {1}h {2}m {3}s"

TAG="CRAWL"


def dumpSecond(t,format_=DEFAULT_DUMP_SECOND_FORMAT):
	return format_.format(t//(60*60*24),t%(60*60*24)//(60*60),t%(60*60*24)%(60*60)//60,t%(60*60*24)%(60*60)%60//1)

def searchDB(ids,dbTags=list(),tv=DEFAULT_CRAWL_TV,limit=DEFAULT_CRAWL_LIMIT):
#res dbData.it have userID.
	for userid in ids:
		#print("ID",id_,"Host",host)
		with __server__.ClientU(userid) as c:
		#	print("dbTags",dbTags)
			for dbData in c.searchDB(dbTags):
				#print("XXX",dbData)
				if not dbData["served"]:
					continue
				if util.BACKUP in dbData["tags"]:
					continue
				limit-=1
				if limit<0:
					return
				dbData["userID"]=c.userid
				dbData["host"]=c.host
				yield dbData
		time.sleep(tv)




def crawl(ids,dbTags=list(),memo=str(),tags=list(),tv=DEFAULT_CRAWL_TV,limit=DEFAULT_CRAWL_LIMIT,add_userid_to_memo=True):
#Return CSM have USER_ID
	USERID_F=util.attr_to_format(select2.Attr.USERID)
	for dbData in searchDB(ids,dbTags,tv,limit):
		#print(dbData)
		with __server__.Client(dbData["host"]) as c:
			if not c.connect(dbData["id"]):
				continue
			for csm in c.search(memo,tags):
				csm.tags.append(util.attr_to_format(select2.Attr.USERID).format(dbData["userID"]))
				csm.tags.append(util.attr_to_format(select2.Attr.DBID).format(dbData["id"].upper()))
				if add_userid_to_memo and \
					not re.match(".*\({0}:.+\)$".format(select2.Attr.USERID),csm.memo): #didn't add userid to memo
					csm.memo+=" ({0})".format(USERID_F.format(dbData["userID"]))
				yield csm


def crawlTOT(ids,dbTags=list(),totTag=str(),tv=DEFAULT_CRAWL_TV,limit=DEFAULT_CRAWL_LIMIT):
#Return CSM have USER_ID
	for dbData in searchDB(ids,dbTags,tv,limit):
		#print(dbData)
		with __server__.Client(dbData["host"]) as c:
			if not c.connect(dbData["id"]):
				continue
			for tot in c.getTOTs(totTag):
				yield tot


class Command(util.Command):
	START=("S","START")
	STOP=("ST","STOP")
	LS=("L","LS")
	POST=("P","POST")
class Docs:
	START="""
	Usage:
		start all ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--dt <dbTags>)] [(--tv <crawlTV>)] [--serve]
		start tot ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--dt <dbTags>)] [(-T <totTag>)] [(--tv <crawlTV>)] [--serve]
		start ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--dt <dbTags>)] [(-m <memo>)] [(-t <tags>)] [(--tv <crawlTV>)] [--serve]
	
	Options:
		crawlTV : d-h-m   ex) 1-12-30
	"""
	STOP="""
	Usage:
		stop <name>
		stop all
	"""
	POST="""
	Usage:
		post <id> <host>
	"""
	HELP="""
		ls
		start all ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--dt <dbTags>)] [(--tv <crawlTV>)] [--serve]
		start tot ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--dt <dbTags>)] [(-T <totTag>)] [(--tv <crawlTV>)] [--serve]
		start ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--dt <dbTags>)] [(-m <memo>)] [(-t <tags>)] [(--tv <crawlTV>)] [--serve]
		stop <name>
		stop all
		post <id> <host>
	"""

DEFAULT_MAX_CRAWL=5

class BaseShell(__shell__.BaseShell):
#shell for BaseManage
	PROMPT=">>"
	def __init__(self,manage):
		self.manage=manage
		super().__init__(prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in __utils__.Command.HELP:
			output.write("""
	stop <crawler_name>
	stop all
	ls
			\n""")
		elif query.command in Command.STOP:
			if not query.args:
				output.write("name don't found\n")
				return
			name=query.args[0]
			if name.upper()=="ALL":
				for name in self.manage.crawlers:
					if self.manage.stop(name):
						output.write("Stopped "+name+"\n")
			else:
				if self.manage.stop(name):
					output.write("Stopped "+name+"\n")
		elif query.command in Command.LS:
			self.manage.clean()
			for name,crawler__ in self.manage.crawlers.items():
				t=crawler__.nextCrawl-time.time()
				output.write("{0} {1} {2}\n".format(name,crawler__.db.id,dumpSecond(t)))
				if type(crawler__) is Crawler:
					output.write("-> db_tags:{0} memo:{1} tags:{2}".\
					format(",".join(crawler__.dbTags),crawler__.memo,",".join(crawler__.tags)))
		else:
			return super().execQuery(query,output)
	def start(self):
		self.stdout.write("*** welcome to crawl shell ***\n")
		return super().start()
	def close(self):
		self.execQuery(__shell__.Query(("STOP","ALL")),self.stdout)


class CrawlShell(BaseShell):
	PROMPT=">>"
	def execQuery(self,query,output):
		if query.command in __utils__.Command.HELP:
			print(Docs.HELP)
		elif query.command in Command.START:
			self.manage.clean()
			if self.manage.n>MAX_CRAWL:
				output.write("Number of Crawl reached Max.(Max is {0})\n".format(MAX_CRAWL))
				return
			try:
				args=docopt.docopt(Docs.START,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"]
			dbTags=list(map(lambda tag:tag.upper(),args["<dbTags>"].split(","))) if args["--dt"] else list()
			serve=args["--serve"]		#if server is True.open DB as server
			crawlTV=args["<crawlTV>"] if args["--tv"] else "1"
			crawlTV=util.culcSecond(crawlTV)
			getTOT=False
			getCSM=False
			if args["-u"]:
				ids=[args["<userid>"]]
			elif args["-f"]:
				ids=__server__.readIDFile(os.path.join("../",crawler.db.dname),args["<idFname>"])
			totTag=""
			memo=""
			tags=[]
			if args["all"]:
				getCSM=True
				getTOT=True
			if args["tot"]:
				totTag=args["<totTag>"] if args["-T"] else str()
				getTOT=True
			else:
				memo=args["<memo>"] if args["-m"] else str()
				tags=args["<tags>"].upper().split(",") if args["-t"] else list()
				getCSM=True
				#print(args)
			if getCSM:
				name=args["<crawlerName>"] if args["-n"] else "crawler_{0}".format(self.manage.n)
				try:
					self.manage.start(name,dbid,crawlTV,ids,dbTags,memo,tags,serve=serve)
					output.write("Crawling "+name+" ...\n")
				except Exception as e:
					print(e)
			if getTOT:
				name=args["<crawlerName>"] if args["-n"] else "crawler_{0}".format(self.manage.n)+":TOT"
				try:
					self.manage.startTOT(name,dbid,crawlTV,ids,dbTags,totTag,serve=serve)
					output.write("Crawling "+name+" ...\n")
				except Exception as e:
					print(e)
		elif query.command in Command.POST:
			try:
				args=docopt.docopt(Docs.POST,query.args)
			except Exception as e:
				print(e)
				return
			id_=args["<id>"]
			host=args["<host>"]
			#with __dns__.Client(dns_host) as c:
			#	c.post(id_,host)
			print("Posted",id_,host)
		else:
			return super().execQuery(query,output)


class AuHSShell(__shell__.BaseShell):
	def __init__(self,home):
		super().__init__(prompt=self.PROMPT)
		crawler=Manage(home.home)
		self.shell=CrawlShell(crawler)
	def execQuery(self,query,output):
		return self.shell.execQuery(query,output)
	def start(self):
		self.stdout.write("*** Start to Crawl! ***\n")
		return self.shell.shell()
	def close(self):
		return self.shell.close()


class BaseCrawler:
#crawl data
#append data to db
#override:
#	crawl()
#	append(data)
	UNDER_LIMIT_CRAWL_TV=60*60
	def __init__(self,db,crawlTV,*args,**kwargs):
		if crawlTV<self.UNDER_LIMIT_CRAWL_TV:
			raise Exception("Crawl TV is too less.Under limit is {0}.".format(self.UNDER_LIMIT_CRAWL_TV))
		self.nextCrawl=time.time()
		self.crawlTV=crawlTV
		self.endEvent=threading.Event()
		self.db=db
		self.t=threading.Thread(target=self.__start,args=args,kwargs=kwargs)
	def crawl(self,*args,**kwargs):
#yield data
		return []
	def append(self,data):
#append data to self.db
		pass
	def __start(self,*args,**kwargs):
		startCrawl=time.time()
		while True:
			#print(self,i,time.time())
			if self.endEvent.is_set():
				return
			if time.time()>self.nextCrawl:
				print("crawl!!")
				for data in self.crawl(*args,**kwargs):
					if self.endEvent.is_set():
						self.db.save()
						return
					self.append(data)
				self.nextCrawl+=self.crawlTV
				self.db.save()
			time.sleep(1)
	def start(self):
#Start can be called only once
		if self.endEvent.is_set():
			return False
		self.t.start()
		return True
	def stop(self):
		self.endEvent.set()
	@property
	def stopped(self):
		return not self.t.is_alive()

class Crawler(BaseCrawler):
	def __init__(self,db,crawlTV=60*60*24,ids=list(),dbTags=list(),memo=str(),tags=list(),limit=DEFAULT_CRAWL_LIMIT):
		self.dbTags=dbTags
		self.memo=memo
		self.tags=tags
		super().__init__(db,crawlTV,ids,dbTags,memo,tags,limit)
	def crawl(self,*args,**kwargs):
		return crawl(*args,**kwargs)
	def append(self,csm):
		return self.db.appendCSM(csm)

class TOTCrawler(BaseCrawler):
	UNDER_LIMIT_CRAWL_TV=60*60
	def __init__(self,db,crawlTV=60*60*24,ids=list(),dbTags=list(),totTag=str(),limit=DEFAULT_CRAWL_LIMIT):
		self.dbTags=dbTags
		self.tag=tag
		super().__init__(db,crawlTV,ids,dbTags,totTag,limit)
	def crawl(self,*args,**kwargs):
		return crawlTOT(*args,**kwargs)
	def append(self,tot):
		return self.db.appendTOT(tot.name,tot.childs)
			

class BaseManage:
#manage BaseCrawler
#override:
#	start()
	def __init__(self,homeDB):
		self.crawlers={}	#[{"thread":,"res":,"event":,"name":}...}
		self.homeDB=homeDB
	def clean(self):	#remove thread don't alive
		for name,crawler in self.crawlers.items():
			if crawler.stopped:
				self.crawlers.pop(name)
	@property
	def n(self):
		return len(self.crawlers)
	def get(self,name):
		return self.crawlers.get(name)
	def start(self,*args,**kwargs):
		pass
	def stop(self,name):
		c=self.get(name)
		if not c:
			return False
		c.stop()
		return True
	def close(self):
		for c in self.crawlers.values():
			c.stop()
	def __enter__(self):
		return self
	def __exit__(self,*args):
		self.close()
		
class BaseManage2(BaseManage):
#expendition of BaseCrawler
	def getDB(self,dbid,dbTags=[],serve=False):
		dbid=dbid.upper()
		db=self.homeDB.select(dbid)
		if not db:
			self.homeDB.append(dbid,[TAG,*dbTags])
			db=self.homeDB.select(dbid)
		else:
			self.homeDB.appendTags(dbid,dbTags)
		if serve:
			try:
				db.open()
			except Exception as e:
				print(e)
		return db
	def start(self,CrawlerClass,name,dbid,dbTags,serve,crawlTV,*args,**kwargs):
		if self.get(name):
			return False
		db=self.getDB(dbid,dbTags,serve)
		self.crawlers[name]=CrawlerClass(db,crawlTV,*args,**kwargs)
		return self.crawlers[name].start()
	

class Manage(BaseManage2):	#manage crawlers
	def start(self,name,dbid,crawlTV,ids=list(),dbTags=list(),memo=str(),tags=list(),limit=DEFAULT_CRAWL_LIMIT,serve=False):
		return super().start(Crawler,name,dbid,dbTags,serve,crawlTV,ids,dbTags,memo,tags,limit)
	def startTOT(self,name,dbid,crawlTV,ids=list(),dbTags=list(),totTag=str(),limit=DEFAULT_CRAWL_LIMIT,serve=False):
		return super().start(TOTCrawler,name,dbid,dbTags,serve,crawlTV,ids,dbTags,totTag,limit)
		self.crawlers[name]=TOTCrawler(db,crawlTV,ids,dbTags,totTag,limit)
		return self.crawlers[name].start()
		
	
