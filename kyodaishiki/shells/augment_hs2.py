from kyodaishiki import __utils__
from kyodaishiki import __shell__
from kyodaishiki import __db__
from kyodaishiki import __server__
from kyodaishiki import __index__
from kyodaishiki import __data__
from . import augment_hs
import os
import docopt
import re
import json
import sys
from functools import *

class Index:
	class DB(__index__.DB):
		def __init__(self,idIdx=__index__.Index(),pwIdx=__index__.Index()):
			super().__init__(idIdx)
			self.pwIdx=pwIdx
		def pw(self,text):
			return self.pwIdx.get(text)
		@property
		def locked(self):
			return self.pwIdx
		def __str__(self):
			return json.dumps((self.idIdx.data,self.pwIdx.data))
		@staticmethod
		def read(line):
			data=json.loads(line.rstrip())
			if len(data)==1:
				return Index.DB(__index__.Index(*data[0]))
			return Index.DB(__index__.Index(*data[0]),__index__.Index(*data[1]))

class ServerTagDB(__server__.ServerTagDB):
	EXPAND="~"
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
	def __searchForTag__(self,tags):
#yield (tagIdx,card)
		if not tags:
			for data in super().__searchForTag__(tags):
				yield data
			return
		U=self.getU()
		allTags=list(map(lambda tagIdx:tagIdx.get(self.text),U))
		tagIdxes__=list(map(lambda tag:self.getTagIdxesRec([tag],U),tags))
#<tags> => [<tagIdxes1>,...]
#<tagIdxes1> : cardIDs1 ,...
#res <tagIdxes1>&&<tagIdxes2>&&<tagIdxes3>,...
		data=[None]*len(tagIdxes__)
		for i,tagIdxes in enumerate(tagIdxes__):
#tagIdxes => cardIDs
			cardIDs=[]
			for tagIdx in tagIdxes:
				tag=tagIdx.get(self.text)
				if tag[0]==self.EXPAND:
					tags=__data__.Logic.expandReg(tag[1:],allTags).split(__data__.Logic.OR)
					tagIdxes__=map(lambda tag:self.find(tag),tags)
				else:
					tagIdxes__=[tagIdx]
				for tagIdx__ in tagIdxes__:
					cardIDs.extend(self.tag.get(tagIdx__,[]))
				cardIDs.extend(self.tag.get(tagIdx,[]))
			data[i]=__data__.Logic.Data(cardIDs)
		for cardID in reduce(lambda a,b:a.and_(b),data)(U):
			if self.get(cardID):
				yield (cardID,self.get(cardID))

class ServerHome(__server__.BaseServerHome):
	PORT=__server__.ServerHome.PORT
	def __init__(self,dname,host,aliasDBIDs={}):
		super().__init__(dname,host,CardDBClass=Index.DB,DBClass=ServerTagDB)
		self.aliasDBIDs=aliasDBIDs
	def appendAlias(self,aliasid,dbid):
		self.aliasDBIDs[aliasid.upper()]=dbid.upper()
	def getAlias(self,aliasid):
		dbid=aliasid.upper()
		while True:
			dbid=self.aliasDBIDs.get(dbid,"")
			if not dbid:
				return None
			if self.get(self.find(dbid)):
				return dbid
	def select(self,dbid,select_locked=False):
		dbid=dbid.upper()
		dbIdx=self.get(self.find(dbid))
		if not dbIdx or (dbIdx.locked and not select_locked):
			dbid=self.getAlias(dbid)
			if not dbid:
				return None
			return self.select(dbid)
		return super().select(dbid)
	def lock(self,dbid,pw):
		dbid=dbid.upper()
		db=self.get(self.find(dbid))
		if not db or db.locked:
			return False
		self.cards[self.find(dbid)].pwIdx=self.appendText(pw)
		return True
	def unlock(self,dbid,pw):
		dbid=dbid.upper()
		db=self.get(self.find(dbid))
		if not db or not db.locked:
			return False
		if pw==db.pw(self.text):
			self.cards[self.find(dbid)].pwIdx=__index__.Index()
			return True
		return False
	def __getDBIDs__(self,dbid):
		res=[]
		dbid=dbid.upper()
		dbid=__db__.compile_dbid(dbid)
		for aliasid in self.aliasDBIDs:
			if re.fullmatch(dbid,aliasid):
				dbid__=self.getAlias(aliasid)
				if dbid__:
					yield dbid__
		for dbid__ in super().getDBIDs(dbid):
			yield dbid__
	def getDBIDs(self,dbid):
		return set(self.__getDBIDs__(dbid))




class Docs:
	LS="""
	Usage:
		ls [(-p <pMode>)] [(-a|--all)]
	"""
	ALIAS="""
	Usage:
		alias db <aliasid> <dbid>
		alias (rm|remove) <command>
		alias <command> <query>...
	"""
	LOCK="""
	Usage:
		lock (u|un) <dbid>
		lock <dbid>
	"""
	HELP="""
# ls [(-a|--all)]
# lock [-u] <dbid>
# exec file <fname>
	"""

class Command:
	LOCK=("LOCK","LO")
	EXEC=("EX","EXEC")
	ALIAS=("ALS","ALIAS")


class HomeShell(augment_hs.HomeShell):
	PROMPT="%"
	def execQuery(self,query,output=sys.stdout):
		if not query:
			return
		if query.command in __utils__.Command.HELP:
			output.write(Docs.HELP+"\n")
			return super().execQuery(query,output)
		elif query.command in __utils__.Command.DB.LS:
			try:
				args=docopt.docopt(Docs.LS,query.args)
			except SystemExit as e:
				print(e)
				return
			all_=args["-a"] or args["--all"]
			pMode=args["<pMode>"].upper() if args["-p"] else ""
			cardToTags=self.home.cardToTags
			data=""
			for db in self.home.listDB():
				dbid=db.getID(self.home.text)
				tags=list(map(lambda tagIdx:tagIdx.get(self.home.text),cardToTags.get(db.id,[])))
				if not re.match("__",dbid) or all_:
					data+="ID:"+dbid.lower()
					if "T" in pMode:
						data+=" -> {0}".format(",".join(tags))
					if hasattr(db,"locked"):
						data+=" Locked" if db.locked else ""
					data+="\n"
					#print("ID:",db.getID(self.home.text).lower())
			output.write(data)
		elif query.command in Command.LOCK:
			try:
				args=docopt.docopt(Docs.LOCK,query.args)
			except SystemExit:
				return
			dbid=args["<dbid>"].upper()
			if args["u"] or args["un"]:
				pw=input("Password : ")
				for dbid__ in self.home.getDBIDs(dbid):
					if self.home.unlock(dbid__,pw):
						output.write("Unlocked "+dbid__+"\n")
					else:
						output.write("Unlock failed. (db isn't locked or pw is illegal or etc...)\n")
			else:
				output.write("Password : ")
				pw=input()
				for dbid__ in self.home.getDBIDs(dbid):
					if self.home.lock(dbid__,pw):
						output.write("Locked "+dbid__+"\n")
		elif query.command in __utils__.Command.DB.SERVER:
			if query.args and query.args[0]=="start":
				super().execQuery(query,output)
				super().execQuery(__shell__.Query(("server","stop","__*")),output)
			else:
				super().execQuery(query,output)
		elif query.command in Command.ALIAS:
			return self.alias(query.args,output)
		else:
			return super().execQuery(query,output)
	def alias(self,args__,output):
		if args__ and args__[0] not in ("rm","remove","db"):
			return super().alias(args__,output)
		try:
			args=docopt.docopt(Docs.ALIAS,args__)
		except SystemExit as e:
			output.write("*** db ***\n")
			for aliasid in self.home.aliasDBIDs:
				output.write("{0} -> {1}\n".format(aliasid.lower(),self.home.aliasDBIDs[aliasid].lower()))
			return super().alias(args__,output)
		if args["db"]:
			aliasid=args["<aliasid>"]
			dbid=args["<dbid>"]
			self.home.appendAlias(aliasid.upper(),dbid.upper())
			output.write("Alias db {0} as {1}\n".format(dbid,aliasid))
		else:
			return super().alias(args__,output)

def loadHome(dname,host="127.0.0.1"):
	home=ServerHome(dname,host)
	return HomeShell(home)
