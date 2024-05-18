from . import augment_hs
from . import augment_hs2
from kyodaishiki import __db__
from kyodaishiki import __index__
from kyodaishiki import __server__
import docopt
import os
import json

class Docs:
	SELECT="""
	Usage:
		select <path> [(-u <userid>)]
	"""
	APPEND="""
	Usage:
		append home <dbid> <tags>...
		append <dbid> <tags>...
	"""
class Index:
	class DB(augment_hs2.Index.DB):
		class Type:
			DB=0
			HOME=1
		def __init__(self,idIdx=__index__.Index(),pwIdx=__index__.Index(),type_=0):
			super().__init__(idIdx,pwIdx)
			self.type=type_
		@property
		def ishome(self):
			return self.type==self.Type.HOME
		@property
		def isdb(self):
			return self.type==self.Type.DB
		def __str__(self):
			return json.dumps((self.idIdx.data,self.pwIdx.data,self.type))
		@staticmethod
		def read(line):
			data=json.loads(line.rstrip())
			lenData=len(data)
			idIdx=data[0]
			pwIdx=data[1] if lenData>1 else __index__.Index()
			type_=data[2] if lenData>2 else 0
			return Index.DB(__index__.Index(*idIdx),__index__.Index(*pwIdx),type_)
class ServerHome(augment_hs2.ServerHome):
#ServerHome can select both of DBClass and HomeClass
	def __init__(self,dname,host,aliasDBIDs={}):
		try:
			__server__.BaseServerHome.__init__(self,dname,host,CardDBClass=Index.DB,DBClass=augment_hs2.ServerTagDB,cardAsBytes=False)
		except:
			__db__.BaseHomeDB.__init__(self,dname,CardDBClass=Index.DB,DBClass=augment_hs2.ServerTagDB,cardAsBytes=False)
			self.serve_forever2=lambda *args,**kwargs:1
		self.HomeClass=ServerHome
		self.selectedHomes={}
		self.aliasDBIDs=aliasDBIDs
	def ishome(self,dbid):
		dbid=dbid.upper()
		card=self.get(self.find(dbid))
		return card.ishome if card else False
	def append(self,dbid,tags,ishome=False):
		dbid=dbid.upper()
		type_=Index.DB.Type.HOME if ishome else Index.DB.Type.DB
		super().append(dbid,tags)
		card=self.cards[self.find(dbid)]
		card.type=type_
		return True

	def select(self,dbid,select_locked=False):
		dbid=dbid.upper()
		dbIdx=self.get(self.find(dbid))
		if not dbIdx:
			return None
		if dbIdx.ishome:
			if self.selectedHomes.get(dbid):
				return self.selectedHomes[dbid]
			self.selectedHomes[dbid]=type(self)(os.path.join(self.dname,dbid),self.host)
			return self.selectedHomes[dbid]
		else:
			return super().select(dbid)

	def close(self):
		for home in self.selectedHomes.values():
			home.close()
		super().close()

def ishome(db):
	return issubclass(type(db),__db__.BaseHomeDB)

def chhome(home,path):
#<path> : <home>/<home>/.../(<db> or <home>)
	SEQ="/"
	for dbid in path.split(SEQ):
		dbids=list(home.getDBIDs(dbid))
		if not dbids:
			Exception("Failed.(don't find {0}.)".format(dbid))
		home=home.select(dbids[0])
	return home

class HomeShell(augment_hs2.HomeShell):
	def __init__(self,home):
		self.HomeShell=HomeShell
		augment_hs.HomeShell.__init__(self,home)
	def select(self,args,output):
		try:
			args__=docopt.docopt(Docs.SELECT,args)
		except SystemExit as e:
			print(e)
			return
		#dbid=args__["<dbid>"].upper()
		path=args__["<path>"].upper()
		if args__["-u"]:
			return super().select(args,output)
		try:
			db=chhome(self.home,path)
		except Exception as e:
			output.write(str(e))
			return
		if not db:
			output.write("Don't find {0}\n".format(path.lower()))
			return
		if ishome(db):
			shell=self.HomeShell(db)
			output.write("*** {0} ***\n".format(db.id))
			shell.shell()
			output.write("*** {0} ***\n".format(self.home.id))
		else:
			shell=self.DBShell(db)
			shell.start()
		#return super().select(args,output)
	def append(self,args,output):
		try:
			args__=docopt.docopt(Docs.APPEND,args)
		except SystemExit as e:
			print(e)
			return
		if args__["home"]:
			dbid=args__["<dbid>"].upper()
			tags=args__["<tags>"]
			self.home.append(dbid,tags,ishome=True)
			output.write("Append {0} -> {1} as home.\n".format(dbid.lower(),tags))
		else:
			return super().append(args,output)
	def start(self):
		super().start()
	def close(self):
		super().close()

def loadHome(dname,host="127.0.0.1"):
	home=ServerHome(dname,host)
	return HomeShell(home)
