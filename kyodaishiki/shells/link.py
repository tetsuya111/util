from kyodaishiki import __data__
from kyodaishiki import __db__
from kyodaishiki import __index__
from kyodaishiki import _util
from kyodaishiki import __shell__
from kyodaishiki import __server__
from . import select2
from . import util
from . import crawl as cr
from . import augment_hs
import os
import docopt
import re
import shutil
import sys
import socketserver
import subprocess as sp
import json
import random

#dname of db = home/link
LINK_DIR="_link"
TAG="LINK"

DEFAULT_CSM_DIR_F=_util.realpath("%USERPROFILE%\desktop\{0}_link_csmFiles")

class Attr(select2.Attr):
	pass

class Index:
	class Query(__index__.Card):
		def __init__(self,memoIdx=__index__.Index(),tagIdxes=[]):
			super().__init__(memoIdx,tagIdxes=tagIdxes)
		@property
		def id(self):
			return __index__.Index(_util.hash(str(self.memoIdx)+"".join(map(str,self.tagIdxes))),0)
		@staticmethod
		def read(line):
			card=__index__.Card.read(line)
			return Index.Query(card.memoIdx,tagIdxes=card.tagIdxes)
	
	class Link(__index__.DB):
		pass

class Data:
	class Query:
		def __init__(self,memo="",tags=[]):
			self.memo=memo
			self.tags=tags
		@staticmethod
		def fromIndex(text,queryIdx):
			return Data.Query(queryIdx.memo(text),queryIdx.tags(text))

#Link = [DB,DB,DB,....]

		
#data=[(dbidIdx,memoIdx,tagIdxes),...]

class Home(__db__.BaseHomeDB):
	def __init__(self,dname,homeDB):
#res link of homeDB
		super().__init__(dname,CardDBClass=Index.Link,DBClass=Link,cardAsBytes=False)
		self.homeDB=homeDB
	def select(self,linkid):
		return super().select(linkid,self.homeDB)

class ServerHome(__server__.BaseServerHome):
	PORT=11411
	def __init__(self,dname,homeDB,host):
		self.homeDB=homeDB
		super().__init__(dname,host,CardDBClass=Index.Link,DBClass=ServerLink,cardAsBytes=False)
	def select(self,linkid):
		return super().select(linkid,homeDB=self.homeDB)


class Link(__db__.BaseTagDB):
	def __init__(self,dname,homeDB):	#data is list of DataOfTagDB.
#{<dbid>:[<query>],...}
		super().__init__(dname,Index.Query,cardAsBytes=False)
		self.homeDB=homeDB
		self.selectedDBs={}
	def listQuery(self):
		for key in self.tag:
			for queryIdx in self.tag[key].cardIDs:
				yield (key.get(self.text),Data.Query.fromIndex(self.text,self.cards[queryIdx]))
	def append(self,dbid,memo="",tags=[],override=False):
		if not super().append(override,[dbid.upper()],toIndex={"memoIdx":memo,"tagIdxes":tags},raw={}):
			queryIdx=Index.Query(memoIdx=self.find(memo),tagIdxes=list(map(lambda tag:self.find(tag.upper()),tags)))
			return super().appendTags(queryIdx.id,[dbid.upper()])
		return True
	def __dumpCSM(self):
		csms=[]
		for tagIdx in self.tag:
			dbid=tagIdx.get(self.text)
			if not self.selectedDBs.get(dbid):
				db=self.homeDB.select(dbid)
				if not db:
					continue
				self.selectedDBs[dbid]=db
			for key in self.tag[tagIdx]:
				db=self.selectedDBs[dbid]
				query=Data.Query.fromIndex(self.text,self.cards[key])
				for csm in __data__.CSM.make(db.text,db.search(query.memo,query.tags)):
					dbid_tag=util.Attr(select2.Attr.DBID)(dbid)
					if dbid_tag not in csm.tags:
						csm.tags.append(dbid_tag)
					yield (dbid,csm)
	def dumpCSM(self):
		return set(map(lambda data:data[1],self.__dumpCSM()))
	def search(self,memo="",tags=[]):	#res as csm.
		regMemo=re.compile(memo)
		for csm in self.dumpCSM():
			if re.search(regMemo,csm.memo) and (not tags or all(map(lambda tag:tag in csm.tags,tags))):
				yield csm
	def removeQuery(self,dbid,memo="",tags=[],log=None):
		regMemo=re.compile(memo)
		for dbid__ in __db__.getDBIDs(self.homeDB,dbid.upper()):
			dbidIdx=self.find(dbid__)
			if not dbidIdx:
				continue
			for queryid in list(self.tag.get(dbidIdx,[])):
				queryIdx=self.cards.get(queryid)
				if not queryIdx:
					continue
				tagsOfQuery=queryIdx.tags(self.text)
				if re.search(regMemo,queryIdx.memo(self.text)) and (not tags or all(map(lambda tag:tag in tagsOfQuery,tags))):
					self.tag[dbidIdx].cardIDs.remove(queryid)
					if log:
						log.write("Removed {0} => {1} {2}\n".format(dbid__,queryIdx.memo(self.text),str(queryIdx.tags(self.text))))
	def __getTags__(self):
		res={}
		for dbidIdx in self.tag:
			dbid=dbidIdx.get(self.text).upper()
			db=self.homeDB.select(dbid)
			if not db:
				continue
			for tagIdx in db.getU():
				tag=tagIdx.get(db.text)
				n=len(db.tag.get(tagIdx,[]))
				if not res.get(tag):
					res[tag]=0
				res[tag]+=n	
		return res.items()
	def getTags(self):
		return map(lambda data:data[0],self.__getTags__())
				
			

class TmpLink(Link):
	ID_FORMAT="TMP_{0}"
	def __init__(self,homeDB,data={},id_=None):
#data = {<dbid>:<query>,...}
		if not id_:
			id_=self.ID_FORMAT.format(hash(str(data)))
		dname=os.path.join(homeDB.dname,id_)
		#dname=dname.replace("||","__").replace("&&","__")
		super().__init__(dname,homeDB)
		for dbid,query in data.items():
			self.append(dbid,query.memo,query.tags)
		#for dbid__ in __db__.getDBIDs(homeDB,dbid):
		#	self.append(dbid__,tags=tags)
	def close(self):
		super().close()
		shutil.rmtree(self.dname)
	@staticmethod
	def asTag(homeDB,tag):
		#return TmpLink(homeDB,"[^_][^_].*",[tag.upper()])
		data={}
		for dbid in homeDB.getDBIDs("[^_][^_].*"):
			data[dbid]=Data.Query(tags=[tag.upper()])
		return TmpLink(homeDB,data)
	@staticmethod
	def asDB(homeDB,dbids=[]):
		def getDBIDs(homeDB,dbids):
			for dbid in dbids:
				dbid=dbid.upper()
				for dbid__ in homeDB.getDBIDs(dbid):
					yield dbid__
		data={}
		for dbid in getDBIDs(homeDB,dbids):
			data[dbid]=Data.Query()
		return TmpLink(homeDB,data)
	@staticmethod
	def all_link(homeDB):
		data={}
		for dbid in homeDB.getDBIDs("[^_][^_].*"):
			data[dbid]=Data.Query()
		return TmpLink(homeDB,data)
		#return TmpLink(homeDB,"[^_][^_].*",[])

class LinkHandler(socketserver.StreamRequestHandler):
	def __init__(self,request,client_addrress,server):
		super().__init__(request,client_addrress,server)
	def handle(self):
		userid=__server__.getID(self.client_address[0])
		if not userid:
			self.wfile.write("400 don't know userid.".encode())
			return
		while True:
			try:
				data=_util.recvForServer(self.request,self.server)
			except:
				return
			if not data:
				if not self.request._closed:
					self.wfile.write("400 $".encode())
				return
			data=data.decode("utf8","ignore")
			self.server.log_connection(self.client_address[0],{"data":data,"client_addrress":self.client_address})
			data=data.split(" ",1)
			command=data[0].upper()
			data=data[1] if len(data)>1 else ""
			if command in _util.Command.SEARCH:
				if not self.server.checkUser("R",userid):
					self.wfile.write("400 don't allow to read data from this server.".encode())
				if not data:
					memo=""
					tags=[]
				else:
					csm=__data__.CSM.readText(data)
					memo=csm.memo
					tags=csm.tags
				csms=list(map(str,self.server.search(memo,tags)))
				res=json.dumps(csms)
				self.wfile.write(("200 "+res).encode())

					

class ServerLink(Link,__server__.BaseDBServer):
	def __init__(self,dname,homeDB,server_addr):
		Link.__init__(self,dname,homeDB)
		__server__.BaseDBServer.__init__(self,dname,server_addr,LinkHandler)
	def close(self):
		Link.save(self)
		__server__.BaseDBServer.close(self)

class Client(__server__.BaseClient):
	def __init__(self,host):
		super().__init__((host,ServerHome.PORT))
	def search(self,memo="",tags=[]):
		csm=str(__data__.CSM(memo=memo,tags=tags))
		data=self.request("SEARCH",csm)
		status,data=data.split(" ",1)
		if status[0]!="2":
			return []
		return map(lambda text:__data__.CSM.loads(text),json.loads(data))
	def dumpCSM(self):
		return self.search()

class ClientU(Client):
	def __init__(self,userid):
		self.userid=userid
		host=__server__.getHost(userid)
		super().__init__(host)

class Docs(_util.Docs):
	LS="""
	Usage:
		ls
	"""
	APPEND="""
	Usage:
		append (td|todb) <linkid> <dbid> [(-m <memo>)] [(-t <tags>)] [(-O|--override)]
		append <linkid> <tags>...
	"""
	SELECT="""
	Usage:
		select <dbid> [(-u <userid>)]
		select db <dbids>...
	"""
	HELP="""
		help [(-a|--all)]
		append <linkid> <tags>...
		select <linkid> [(-u <userid>)]
		crawl
	"""
	class CSM:
		REMOVE="""
		Usage:
			remove <linkid>
		"""
	class Crawl:
		START="""
		Usage:
			start ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--lt <linkTags>)] [(-m <memo>)] [(-t <tags>)] [(--tv <crawlTV>)] [--serve]
		"""
	class Link:
		class CSM:
			WRITE="""
			Usage:
				write csm [(-t <tags>)] [(-m <memo>)] [(-d <dname>)]
				write [(-d <dname>)]
			"""
			REMOVE="""
			Usage:
				remove
			"""
		APPEND="""
		Usage:
			append (td|todb) <dbid> [(-m <memo>)] [(-t <tags>)] [(-O|--override)]
			append <dbid> [(-m <memo>)] [(-t <tags>)]
		"""
		SEARCH="""
		Usage:
			search [(-m <memo>)] [(-c <comment>)] [(-t <tags>)] [(-D <dbid>)] [(-p <pMode>)] [(--pn|--printNot)] [(-r|--random)]
		"""
		TAG="""
		Usage:
			tag [<tag>] [(-r|--random)]
		"""
		REMOVE="""
		Usage:
			remove <dbid> [(-m <memo>)] [(-t <tags>)]
		"""
		VIM="""
		Usage:
			vim (f|file) <fname>
			vim [(-t <tags>)] [(--nt <noTags>)] [(-m <memo>)] [(-D <dbid>)] [(--pn|--printNot)] [(-d <dname>)] [(-r|--random)]
		"""
		HELP="""
			ls
			append
			append
			search [(-m <memo>)] [(-t <tags>)] [(-D <dbid>)] [(-p <pMode>)]
			remove <dbid> [(-m <memo>)] [(-t <tags>)]
			csm write
			csm search
			csm remove
			vim
		"""

class Command(select2.Command):
	ALIAS=("ALS","ALIAS")


class LinkShell(__shell__.BaseShell3):
	PROMPT="=>"
	VIM_COUNT_OF_F=50
	def __init__(self,link):
		self.link=link
		super().__init__(link.dname,self.PROMPT)
	def execQuery(self,query,output):
		if not query:
			return
		elif query.command in Command.HELP:
			output.write(Docs.Link.HELP+"\n")
		elif query.command in _util.Command.DB.LS:
			data=""
			for id_,query in self.link.listQuery():
				data+="{0} {1} {2}\n".format(id_.lower(),query.memo,query.tags)
			output.write(data)
		elif query.command in _util.Command.APPEND:
			try:
				args=docopt.docopt(Docs.Link.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			memo=args["<memo>"] if args["-m"] else ""
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			if args["td"] or args["todb"]:
				override=args["-O"] or args["--override"]
				dbid=args["<dbid>"].upper()
				db=self.link.homeDB.select(dbid)
				if not db:
					self.link.homeDB.append(dbid,["FROM_LINK"])
					db=self.link.homeDB.select(dbid)
				for csm in self.link.search(memo=memo,tags=tags):
					db.appendCSM(csm,override)
				output.write("Append to {0}\n".format(dbid.lower()))
				db.save()
			else:
				data=""
				dbid=args["<dbid>"].upper()
				for dbid in self.link.homeDB.getDBIDs(dbid):
					db_tagIdxes=self.link.homeDB.cardToTags.get(self.link.homeDB.find(dbid),[])
					db_tags=list(map(lambda tagIdx:tagIdx.get(self.link.homeDB.text),db_tagIdxes))
					if util.BACKUP in db_tags:
						continue
					if self.link.append(dbid,memo,tags):
						data+="Append {0} {1} {2}\n".format(dbid,memo,tags)
				output.write(data)
				self.link.save()
		elif query.command in _util.Command.SEARCH:
			try:
				return self.search(query.args,output)
			except KeyboardInterrupt:
				pass
		elif query.command in _util.Command.TAG:
			try:
				args=docopt.docopt(Docs.Link.TAG,query.args)
			except SystemExit as e:
				print(e)
				return
			searchTag=args["<tag>"].upper() if args["<tag>"] else ""
			random_=args["-r"] or args["--random"]
			data=self.link.__getTags__()
			if random_:
				data=list(data)
				random.shuffle(data)
			else:
				data=sorted(data,key=lambda dat:dat[1])
			text=""
			for tag,n in data:
				if re.search(searchTag,tag):
					text+="{0} {1}\n".format(tag,n)
			output.write(text)
		elif query.command in _util.Command.REMOVE:
			try:
				args=docopt.docopt(Docs.Link.REMOVE,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"]
			memo=args["<memo>"] if args["-m"] else ""
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			self.link.removeQuery(dbid,memo,tags,log=sys.stdout)
		elif query.command in _util.Command.CSM:
			query=__shell__.Query(query.args)
			if query.command in Command.WRITE:
				try:
					args=docopt.docopt(Docs.Link.CSM.WRITE,query.args)
				except SystemExit as e:
					print(e)
					return
				dname=args["<dname>"] if args["-d"] else util.DEFAULT_CSM_DIR_F(self.link.dname)
				dname=_util.realpath(dname)
				if not os.path.exists(dname):
					os.makedirs(dname)
				if args["csm"]:
					memo=args["<memo>"] if args["-m"] else ""
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					csms=self.link.search(memo,tags)
				else:
					csms=self.link.search()
				for csm in csms:
					csm.write(os.path.join(dname,csm.fname))
			elif query.command in Command.REMOVE:
				dname=util.DEFAULT_CSM_DIR_F(self.link.dname)
				if os.path.exists(dname):
					shutil.rmtree(dname)
					output.write("Removed {0}\n".format(dname))
			else:
				if "-d" not in query.args:
					query.extend(("-d",util.DEFAULT_CSM_DIR_F(self.link.dname)))
				return __shell__.CSMShell(self.link).execQuery(query,output)
		elif query.command in ["VIM"]:
			try:
				args=docopt.docopt(Docs.Link.VIM,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["f"] or args["file"]:
				fnames=[_util.realpath(args["<fname>"])]
			else:
				memo=args["<memo>"] if args["-m"] else ""
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				noTags=args["<noTags>"].upper().split(",") if args["--nt"] else []
				dname=args["<dname>"] if args["-d"] else util.DEFAULT_CSM_DIR_F(self.link.dname)
				if args["-D"]:
					dbid=args["<dbid>"].upper()
					tags.append(Attr(Attr.DBID)(dbid))
				csms=list(self.link.search(memo,tags))
				if not (args["--pn"] or args["--printNot"]):
					noTags.append(select2.NOT)
				if noTags:
					def filter_nt(csms):
						for csm in csms:
							if not any(map(lambda noTag:noTag in csm.tags,noTags)):
								yield csm
					csms=filter_nt(csms)
				fnames=map(lambda csm:os.path.join(dname,csm.fname),csms)
				fnames=filter(lambda fname:os.path.exists(fname),fnames)
				if args["-r"] or args["--random"]:
					fnames=list(fnames)
					random.shuffle(fnames)
				fnames=list(fnames)
				n=len(fnames)//self.VIM_COUNT_OF_F + 1
				for i in range(n):
					if i != 0:
						output.write("Open next cards ?? (y.../n) : ")
						yn=input().upper()
						if yn == "N":
							break
					sp.call(["vim","-Z",*fnames[i*self.VIM_COUNT_OF_F:i*self.VIM_COUNT_OF_F+self.VIM_COUNT_OF_F]])
			#sp.call(["vim","-Z",*fnames])
		else:
			return super().execQuery(query,output)
	def search(self,args,output):
		try:
			args=docopt.docopt(Docs.Link.SEARCH,args)
		except SystemExit as e:
			print(e)
			return
		memo=args["<memo>"] if args["-m"] else ""
		comment=args["<comment>"] if args["-c"] else ""
		tags=args["<tags>"].upper().split(",") if args["-t"] else []
		random_=args["-r"] or args["--random"]
		if args["-D"]:
			tags.append(util.attr_to_format(select2.Attr.DBID).format(args["<dbid>"].upper()))
		pMode=args["<pMode>"].upper()+"M" if args["-p"] else "M"
		printNot=args["--pn"] or args["--printNot"]
		try:
			data=""
			csms=self.link.search(memo,tags)
			if random_:
				csms=list(csms)
				random.shuffle(csms)
			else:
				csms=sorted(csms,key=lambda csm:csm.date)
			for csm in csms: 
				if select2.NOT in csm.tags and not printNot:
					continue
				if not comment or re.search(comment,csm.comment):
					data+="* "+csm.dump(pMode)+"\n"
					data+="-----------------------------------------------\n"
			output.write(data)
		except Exception as e:
			print("EXCEPTION",e,e.__reduce__())
	def start(self):
		print("***",self.link.id,"***")
		super().start()
		self.close()
	def close(self):
		super().close()
		csm_dname=DEFAULT_CSM_DIR_F.format(self.link.id)
		if os.path.exists(csm_dname):
			shutil.rmtree(csm_dname)

def select(home,linkid):
#if you don't find linkid,res tmp link.
	linkid=linkid.upper()
	if linkid.upper()=="MAIN":
		return TmpLink.all_link(home.homeDB)
	else:
		linkids=list(__db__.getDBIDs(home,linkid))
		if not linkids:
			return TmpLink.asTag(home.homeDB,linkid)
		else:
			linkid=linkids[0]
			return home.select(linkid)



class ClientShell(__shell__.BaseShell):
	PROMPT="=>"
	def __init__(self,client):
		self.client=client
		super().__init__(prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in _util.Command.HELP:
			output.write("""
	$ search [(-t <tags>)] [(-m <memo>)] [(-p <pMode>)]
	$ csm write [(-d <dname>)]\n""")
		elif query.command in _util.Command.SEARCH:
			try:
				args=docopt.docopt(_util.Docs.SEARCH,query.args)
			except SystemExit as e:
				print(e)
				return
			memo=args["<memo>"] if args["-m"] else ""
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			for csm in self.client.search(memo,tags):
				output.write("* "+csm.memo+"\n")
		elif query.command in _util.Command.CSM:
			if query.args and query.args[0].upper() in Command.WRITE:
				return __shell__.CSMShell(self.client).execQuery(query,output)
		else:
			return super().execQuery(query,output)
	def start(self):
		print("*** welcome to {0} ***".format(self.client.dbid))
		super().start()

class ServerHomeShell(__shell__.BaseServerHomeShell,__shell__.BaseShell3):
	PROMPT=":>"
	LINK_ALIAS_TXT="link_alias.txt"
	def __init__(self,home):
		self.crawl_shell=CrawlShell(Manage(home.homeDB))
		__shell__.BaseServerHomeShell.__init__(self,home,LinkShell,self.PROMPT)
		self.link_alias=os.path.join(self.home.dname,self.LINK_ALIAS_TXT)
		_util.touch(self.link_alias)
	def execQuery(self,query,output):
		if not query:
			return
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
			if query.args and query.args[0] in ("-a","--all"):
				__shell__.BaseServerHomeShell.execQuery(self,query,output)
		elif query.command in Command.ALIAS:
			return self.alias(query.args,output)
		elif query.command in self.aliasCommands:
			query__=self.aliasCommands[query.command]
			query__.extend(query.args)
			return self.execQuery(query__,output)
		elif query.command in Command.DB.SELECT:
			try:
				args=docopt.docopt(Docs.SELECT,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["db"]:
				dbids=args["<dbids>"]
				link=TmpLink.asDB(self.home.homeDB,dbids)
				try:
					shell=self.DBShell(link)
					shell.execAliasf(self.link_alias,output)
					shell.aliasCommands.update(self.aliasCommands)	#
					shell.start()
				except Exception as e:
					print(e)
				link.save()
				link.close()
				print("***",self.home.id,"***")
			elif args["-u"]:
				userid=args["<userid>"]
				dbid=args["<dbid>"]
				with ClientU(userid) as c:
					if c.connect(dbid):
						ClientShell(c).start()
			else:
				try:
					linkid=args["<dbid>"]
					db=select(self.home,linkid)
					try:
						shell=self.DBShell(db)
						shell.execAliasf(self.link_alias,output)
						shell.aliasCommands.update(self.aliasCommands)	#
						shell.start()
					except Exception as e:
						print(e)
					db.save()
					db.close()
					print("***",self.home.id,"***")
				except Exception as e:
					print(e)
				#return super().execQuery(query,output)
		elif query.command in _util.Command.CRAWL:
			if query.args:
				return self.crawl_shell.execQuery(__shell__.Query(query.args),output)
			return self.crawl_shell.start()
		elif query.command in _util.Command.CSM:
			query__=__shell__.Query(query.args)
			if query__.command in _util.Command.REMOVE:
				try:
					args=docopt.docopt(Docs.CSM.REMOVE,query__.args)
				except SystemExit as e:
					print(e)
					return
				linkid=args["<linkid>"].upper()
				for linkid__ in self.home.getDBIDs(linkid):
					csm_dname=util.DEFAULT_CSM_DIR_F(os.path.join(self.home.dname,linkid__))
					if os.path.exists(csm_dname):
						shutil.rmtree(csm_dname)
						output.write("Removed {0}\n".format(csm_dname))
			else:
				return __shell__.BaseServerHomeShell.execQuery(self,query,output)
		elif query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["td"] or args["todb"]:
				linkid=args["<linkid>"]
				link=select(self.home,linkid)
				return LinkShell(link).execQuery(__shell__.Query(("append","todb",*query.args[2:])),output)
			else:
				return super().execQuery(query,output)
		else:
			return __shell__.BaseServerHomeShell.execQuery(self,query,output)
	def start(self):
		print("*** welcome to link home! ***")
		__shell__.BaseShell3.start(self)
		#super().start(self)
	def close(self):
		self.home.close()
		self.crawl_shell.close()

class AuHSShell(__shell__.BaseShell):
#qussion between AugmentHomeShell and ServerHomeShell
	PROMPT=">>"
	def __init__(self,home):
		super().__init__(prompt=self.PROMPT)
		self.homeDB=home.home
		try:
			host="127.0.0.1"
			try:
				home=ServerHome(os.path.join(self.homeDB.dname,LINK_DIR),self.homeDB,host)
				home.open()
				home_shell=ServerHomeShell(home)
			except:
				home=Home(os.path.join(self.homeDB.dname,LINK_DIR),self.homeDB)
				home_shell=HomeShell(home)
		except Exception as e:
			print(e)
			return home_shell
		self.home_shell=home_shell
	def execQuery(self,query,output):
		return self.home_shell.execQuery(query,output)
	def start(self):
		return self.home_shell.start()
	def close(self):
		return self.home_shell.close()

def searchLink(ids,linkTags=[],tv=cr.DEFAULT_CRAWL_TV,limit=cr.DEFAULT_CRAWL_LIMIT):
	for userid in ids:
		with ClientU(userid) as c:
			for link_data in c.searchDB(linkTags):
				if not link_data["served"]:
					continue
				limit-=1
				if limit<0:
					return
				link_data["userid"]=c.userid
				link_data["host"]=c.host
				yield link_data

def crawl(ids,linkTags=[],memo="",tags=[],tv=cr.DEFAULT_CRAWL_TV,limit=cr.DEFAULT_CRAWL_LIMIT):
	for link_data in searchLink(ids,linkTags,tv,limit):
		with Client(link_data["host"]) as c:
			if not c.connect(link_data["id"]):
				continue
			for csm in c.search(memo,tags):
				csm.tags.extend((TAG,util.attr_to_format(select2.Attr.USERID).format(link_data["userid"]),"LINKID:"+link_data["id"].upper()))
				yield csm

class Crawler(cr.BaseCrawler):
	def __init__(self,db,crawlTV=60*60*24,ids=[],linkTags=[],memo="",tags=[],limit=cr.DEFAULT_CRAWL_LIMIT):
		super().__init__(db,crawlTV,ids,linkTags,memo,tags,limit)
	def crawl(self,ids,linkTags,memo,tags,limit):
		return crawl(ids,linkTags,memo,tags,limit=limit)
	def append(self,csm):
		return self.db.appendCSM(csm)

class Manage(cr.BaseManage2):
	def start(self,name,dbid,crawlTV=60*60*24,ids=[],linkTags=[],memo="",tags=[],limit=cr.DEFAULT_CRAWL_LIMIT,serve=False):
		return super().start(Crawler,name,dbid,linkTags,serve,crawlTV,ids,linkTags,memo,tags,limit)

class CrawlShell(cr.BaseShell):
	def execQuery(self,query,output):
		if query.command in _util.Command.HELP:
			output.write("""
	start ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--lt <linkTags>)] [(-m <memo>)] [(-t <tags>)] [(--tv <crawlTV>)] [--serve]
			\n""")
			super().execQuery(query,output)
		elif query.command in cr.Command.START:
			try:
				args=docopt.docopt(Docs.Crawl.START,query.args)
			except SystemExit as e:
				print(e)
				return
			#start ((-f <idFname>)|(-u <userid>))  <dbid> [(-n <crawlerName>)] [(--lt <linkTags>)] [(-m <memo>)] [(-t <tags>)] [(--tv <crawlTV>)] [--serve]
			if args["-f"]:
				ids=__server__.readIDFile(self.manage.homeDB.dname,args["<idFname>"])
			else:
				ids=[args["<userid>"]]
			dbid=args["<dbid>"]
			crawlerName=args["<crawlerName>"] if args["-n"] else "CRAWLER_{0}".format(self.manage.n)
			linkTags=args["<linkTags>"] if args["--lt"] else []
			memo=args["<memo>"] if args["-m"] else ""
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			crawlTV=args["<crawlTV>"] if args["--tv"] else 60*60*24
			serve=args["--serve"]
			self.manage.start(crawlerName,dbid,crawlTV,ids,linkTags,memo,tags,serve=serve)
		else:
			return super().execQuery(query,output)
