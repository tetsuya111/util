from . import _util
from . import __index__
from . import __data__
from .__index__ import Index
import re
import datetime
import os
from socketserver import *
import socket
import selectors
import threading
import shutil
from functools import *
import random



class BaseDB:	#BaseDB has data.
	"""	
dname
dataFile
find(s)
appendText(s)
save()
"""
	DATA_FILE="data.txt"

	def __init__(self,dname):
		self.__dname=dname
		if not os.path.exists(dname):
			os.makedirs(dname)
		self.__dataFile=os.path.join(dname,BaseDB.DATA_FILE)
		self.text=__data__.Text()
		self.lenText=0
		self.__id=None
		self.mutex=threading.Lock()
		if os.path.exists(self.dataFile):
			with open(self.dataFile,"r") as f:
				self.text=__data__.Text(f.read())
		self.lenText=len(self.text)
	@property
	def id(self):	#dname : <path>.../<id>
		if not self.__id:
			self.__id=os.path.split(self.dname)[1]
		return self.__id
	def __hash__(self):
		return self.id
	@property
	def dname(self):
		return self.__dname
	@property
	def dataFile(self):
		return self.__dataFile
	def clear(self):
		with self.mutex:
			self.text=__data__.Text()
			self.lenText=0
	def find(self,s):
		return __data__.find(s,self.text)
	def appendText(self,s):
		if not s:
			return Index()
		idx=self.find(s)
		if idx:	#if found text.
			return idx
		with self.mutex:
			lenS=len(s)
			self.text+=s
			self.lenText+=lenS
		return Index(self.lenText-lenS,lenS)
	def save(self):
		if not os.path.exists(self.dname):
			os.mkdir(self.dname)
		with self.mutex:
			with open(self.dataFile,"w") as f:
				f.write(str(self.text))
	def close(self):
		self.save()
	def __enter__(self):
		return self
	def __exit__(self,*args,**kwargs):
		self.close()

class TOT_DB(BaseDB):	#TOT_DB has TOT.
	TOT_FILE="tot.txt"
	def __init__(self,dname):
		super().__init__(dname)
		self.__totFile=os.path.join(dname,TOT_DB.TOT_FILE)
		self.__tots={}
		if os.path.exists(self.totFile):
			with open(self.totFile,"r") as f:
				for line in f:
					tot=__index__.TOT.read(line)
					self.__tots[tot.id]=tot
	@property
	def totFile(self):
		return self.__totFile
	@property
	def tots(self):
		return self.__tots
	def clear(self):
		super().clear()
		with self.mutex:
			self.__tots={}
	def dumpTOT(self):
		return __data__.TOT.make(self.text,self.tots.values())
	def getTagsInTOT(self):
		for tot in self.tots.values():
			yield str(__data__.Logic.Group.makeFromIndex(tot.nameGroup,self.text))
			for tagGroup in tot.tagGroups:
				yield str(__data__.Logic.Group.makeFromIndex(tagGroup,self.text))
	def getTOT(self,tag):	#wrapper for tag is str.
		if not tag:
			return None
			#eeturn self.__tots
		tagIdx=self.find(tag)
		if tagIdx:
			return self.tots.get(__index__.TOT.getID(__index__.Logic.Tag(tagIdx)))
		return None
	def searchTOT(self,tag):
		regTag=re.compile(tag)
		for tot in self.tots.values():
			if re.search(regTag,str(__data__.Logic.Group.makeFromIndex(tot.nameGroup,self.text))):
				yield tot
	def removeTOT(self,nameIdx):
		with self.mutex:
			return self.__tots.pop(nameIdx)
	def appendTOT(self,name,tags,override=False):
		if not tags:
			return False
		nameGroup=self.makeGroup(name.upper(),append=True)
		tags_of_name=list(nameGroup.iterTag())
		if len(tags_of_name)>1:
# A&&B   A=>A&&B b=>A&&B
			for tagIdx in map(lambda tag:tag.nameIdx,tags_of_name):	#A&&B&&C => A,B,C
				totid=__index__.TOT.getID(tagIdx)
				tot=self.tots.get(totid)	#A etc...
				#if tot and nameGroup in map(lambda tagGroup:tagGroup.id,tot.tagGroups):	#if already A&&B in A 
				#	continue
				if not tot:
					tot=__index__.TOT(__index__.Logic.Group(__index__.Logic.Tag(tagIdx)),[nameGroup.toTOT()])
					self.__tots[tot.id]=tot
				self.__tots[totid].tagGroups.append(nameGroup.toTOT())
				self.__tots[totid].tagGroups=list(set(self.__tots[totid].tagGroups))
					
		tagGroups=[self.makeGroup(tag.upper(),append=True) for tag in tags]
		tot=__index__.TOT(nameGroup,tagGroups)
		if self.__tots.get(tot.id):
			if override:
				self.removeTOT(tot.id)
		with self.mutex:
			self.__tots[tot.id]=tot
		return True
	def appendCSM(self,csm,override=False):
		if not __data__.TOT.isTOT(csm):
			return False
		tot=__data__.TOT.toTOT(csm)
		return self.appendTOT(tot.name,tot.childs)
	def appendCSMs(self,csms,override=False):
		for csm in csms:
			self.appendCSM(csm,override)
	def makeGroup(self,s,append=False):
		g=__data__.Logic.Group.make(s)
		if append:
			for tag in g.iterTag():
				self.appendText(tag)
		return g.toIndex(self.text)
	def __getTagIdxesRec__(self,tags,U):
		allTags=list(map(lambda tagIdx:tagIdx.get(self.text),U))	#allTags for expandReg in Logic.Group.make
		for tag in tags:
			tag=tag.upper()
			tagG=__data__.Logic.Group.make(tag,allTags).toIndex(self.text)
			for tagIdx in tagG.get(U,self.__tots):
				yield tagIdx
	def getTagIdxesRec(self,tags,U):
		return self.__getTagIdxesRec__(tags,U)
	def getTagsRec(self,tags,U):
		return list(map(lambda tagIdx:tagIdx.get(self.text),self.getTagIdxesRec(tags,U)))
	def save(self):
		super().save()
		with self.mutex:
			with open(self.totFile,"w") as f:
				for tot in self.__tots.values():
					f.write(str(tot)+"\n")
	def close(self):
		self.save()
	def appendDB(self,dstDB,override=False):
		for tot in __data__.TOT.make(dstDB.text,dstDB.tots.values()):
			self.appendTOT(tot.name,tot.childs,override)


class BaseCardDB(TOT_DB):
	class Mode:
		CARD=0
		MEMO=1
		COMMENT=2
		TAG=4
		DATE=8
		TOT=16
		MAX=16
		ALL=31
	
	CARD_FILE="card.txt"
	def __init__(self,dname,CardClass=__index__.BaseCard,cardAsBytes=True):
#cardClass must have reads.
		super().__init__(dname)
		self.__dname=dname
		self.CardClass=CardClass
		self.__cardFile=os.path.join(dname,self.CARD_FILE)
		self.cards=dict()
		self.cardAsBytes=cardAsBytes	#for Card
		if os.path.exists(self.__cardFile):
			mode="rb" if self.cardAsBytes else "r"
			with open(self.__cardFile,mode) as f:
				for line in f:
					card=CardClass.read(line)
					self.cards[card.id]=card
	@property
	def cardFile(self):
		return self.__cardFile
	def clear(self):
		super().clear()
		with self.mutex:
			self.cards={}
	def get(self,cardID):
		return self.cards.get(cardID)
	def append(self,override,toIndex=dict(),raw=dict()):
#args are to index and append text.
#cardKwArgs are to args for card as raw.
		for key in toIndex:
			if type(toIndex[key]) in (list,tuple):
				raw[key]=list(map(lambda arg__:self.appendText(arg__),toIndex[key]))
			else:
				raw[key]=self.appendText(toIndex[key])
		card=self.CardClass(**raw)
		if self.cards.get(card.id):
			if override:
				self.remove(card.id)
			else:
				return None
		with self.mutex:
			self.cards[card.id]=card
		return card
	def searchFunc(self,card,**data):
		return True
	def search(self,toIndex=dict(),raw=dict()):
#args are to index.
#searchFunc must first arge card and return bool
#yield card if searchFunc res True.
		cardArgs=list()
		for key in toIndex.keys():
			if type(toIndex[key]) in (list,tuple):
				raw[key]=list(map(lambda arg__:self.find(arg__),toIndex[key]))
			else:
				raw[key]=self.find(toIndex[key])
		for card in self.cards.values():
			if self.searchFunc(card,**raw):
				yield card
#args is cards because you may use better cards as dict.

	def remove(self,id_):
		if not self.get(id_):
			return None
		with self.mutex:
			return self.cards.pop(id_)
	def getU(self):
		return []
	def save(self):
		super().save()
		with self.mutex:
			mode="wb" if self.cardAsBytes else "w"
			if self.cardAsBytes:
				nn="\n".encode()
				to_data=bytes
			else:
				nn="\n"
				to_data=str
			with open(self.__cardFile,mode) as f:
				f.write(nn.join(map(to_data,self.cards.values())))
	def close(self):
		super().close()
		self.save()


class BaseTagDB(BaseCardDB):
#BaseTagDB have tag.
#tag have card IDs.
#searchForTag is to search cards by tags.
	TAG_FILE="tag.txt"
	def __init__(self,dname,CardClass=__index__.BaseCard,cardAsBytes=True):
		super().__init__(dname,CardClass,cardAsBytes)
		self.tag=dict()
		self.__tagFile=os.path.join(dname,BaseTagDB.TAG_FILE)
		if os.path.exists(self.__tagFile):
			with open(self.__tagFile,"r") as f:
				for line in f:
					tag=__index__.Tag.read(line)
					self.tag[tag.id]=tag
		self.cardToTags=self.reverseTag()
	def clear(self):
		super().clear()
		with self.mutex:
			self.tag={}
	def reverseTag(self):
#res {<cardID>:[<tagIdxes>,...],...}
		res=dict()
		for tagIdx in self.tag:
			for cardID in self.tag[tagIdx]:
				if not res.get(cardID):
					res[cardID]=list()
				res[cardID].append(tagIdx)
		return res
	def __searchForTag__(self,tags):
#yield (tagIdx,card)
		if not tags:
			for cardID,card in self.cards.items():
				yield (cardID,card)
			return
		U=self.getU()
		tagIdxes__=list(map(lambda tag:self.getTagIdxesRec([tag],U),tags))
#<tags> => [<tagIdxes1>,...]
#<tagIdxes1> : cardIDs1 ,...
#res <tagIdxes1>&&<tagIdxes2>&&<tagIdxes3>,...
		data=[None]*len(tagIdxes__)
		for i,tagIdxes in enumerate(tagIdxes__):
#tagIdxes => cardIDs
			cardIDs=[]
			for tagIdx in tagIdxes:
				cardIDs.extend(self.tag.get(tagIdx,[]))
			data[i]=__data__.Logic.Data(cardIDs)
		for cardID in reduce(lambda a,b:a.and_(b),data)(U):
			if self.cards.get(cardID):
				yield (cardID,self.cards.get(cardID))
	def searchForTag(self,tags):
#Don't res same card.
		searched={}
		for tagIdx,card in self.__searchForTag__(tags):
			if not searched.get(card.id):
				yield (tagIdx,card)
				searched[card.id]=True
	def searchForTagOnlyCard(self,tags):
#res only card 
		return map(lambda data:data[1],self.searchForTag(tags))
	def searchForTagWithTags(self,tags):
		for card in self.searchForTagOnlyCard(tags):
			tagIdxes=self.cardToTags.get(card.id,[])
			yield (card,list(map(lambda tagIdx:tagIdx.get(self.text),tagIdxes)))
	def append(self,override,tags,toIndex={},raw={}):
		card=super().append(override,toIndex,raw)
		if not card:
			return False
		tagIdxes=list(map(lambda tag:self.appendText(tag.upper()),tags))
		with self.mutex:
			for tagIdx in tagIdxes:
				if not self.tag.get(tagIdx):
					self.tag[tagIdx]=__index__.Tag(tagIdx)
				if card.id not in self.tag[tagIdx]:
					self.tag[tagIdx].append(card.id)
			self.cardToTags[card.id]=tagIdxes
		return card
	def appendTags(self,id_,tags):	#append tags to card that id is id_.
		#print(tags)
		if not self.get(id_):
			return False
		tagIdxes=list(map(lambda tag:self.appendText(tag.upper()),tags))
		with self.mutex:
			for tagIdx in tagIdxes:
				if not self.tag.get(tagIdx):
					self.tag[tagIdx]=__index__.Tag(tagIdx)
				if id_ not in self.tag[tagIdx]:	#don't have admitted
					self.tag[tagIdx].append(id_)
			if self.cardToTags.get(id_):
				self.cardToTags[id_].extend(tagIdxes)
				self.cardToTags[id_]=list(set(self.cardToTags[id_]))
			else:
				self.cardToTags[id_]=tagIdxes
		return True
	def remove(self,id_):
		if not super().remove(id_):
			return False
		with self.mutex:
			for tagIdx in self.tag:
#remove from tag.
				if id_ in self.tag[tagIdx]:
					self.tag[tagIdx].cardIDs.remove(id_)
			if self.cardToTags.get(id_):
				self.cardToTags.pop(id_)
		return True
	def __removeTags__(self,ids,tags):
		tagIdxes=list(map(lambda tag:self.find(tag.upper()),tags))
		ids=list(ids)
		with self.mutex:
			for tagIdx in tagIdxes:
				if not self.tag.get(tagIdx):
					continue
				self.tag[tagIdx].cardIDs=list(filter(lambda cardID:cardID not in ids,self.tag[tagIdx].cardIDs))
			for id_ in ids:
				if self.cardToTags.get(id_):
					self.cardToTags[id_]=list(filter(lambda tagIdx:tagIdx not in tagIdxes,self.cardToTags[id_]))
	def removeTags(self,id_,tags):
		return self.__removeTags__([id_],tags)
	def cleanTag(self):
		for key in list(self.tag):
			if not self.tag[key]:
				self.tag.pop(key)
			else:
				self.tag[key].cardIDs=list(filter(lambda cardID:self.get(cardID),self.tag[key]))
		
	def getTags(self):
		return list(map(lambda tagIdx:tagIdx.get(self.text),self.getU()))
	def getAllTags(self):
		return list(set(self.getTags()+list(self.getTagsInTOT())))
	def getU(self):
		return self.tag.keys()
	def save(self):
		super().save()
		with self.mutex:
			self.cleanTag()
			with open(self.__tagFile,"w") as f:
				for tag__ in self.tag:
					if self.tag[tag__].cardIDs:
						f.write(str(self.tag[tag__])+"\n")

class CSM_DB:
	def appendCSMs(self,csms):
		pass
	def dumpCSM(self):
		pass

class CardDB(BaseCardDB):
	class Mode:
		CARD=0
		MEMO=1
		COMMENT=2
		TAG=4
		DATE=8
		TOT=16
		MAX=16
		ALL=31
	
	
			
	def __init__(self,dname):
		super().__init__(dname,__index__.Card,False)
	def dumpCSM(self):
		return __data__.CSM.make(self.text,self.cards.values())

	def dump(self,card,mode=15):
		return __data__.CSM.makeOne(self.text,card).dump(mode)
	def append(self,memo,comment=str(),tags=list(),date=str(datetime.datetime.now()).split(".",1),override=False):
		return super().append(override,toIndex={"memoIdx":memo,"commentIdx":comment.replace("\n\n","\n-\n"),"tagIdxes":list(map(lambda tag:tag.upper(),tags))},raw={"date":date})
	def appendCSM(self,csm,override=False):
		return self.append(csm.memo,csm.comment,csm.tags,csm.date,override)
	def appendDB(self,dst,memo=str(),tags=list(),override=False):
		TOT_DB.appendDB(self,dst,override)
		for csm in __data__.CSM.make(dst.text,dst.search(memo,tags)):
			self.appendCSM(csm,override)
	def searchFunc(self,card,regMemo,tagIdxes):
		if re.search(regMemo,card.memo(self.text)):
			if not tagIdxes:
				return True
			return all(map(lambda tagIdxes__:any((tagIdx in card.tagIdxes for tagIdx in tagIdxes__)),tagIdxes))
	def search(self,memo=str(),tags=list()):
		regMemo=re.compile(memo)
		U=self.getU()
		tagIdxes=list(map(lambda tag:list(self.getTagIdxesRec([tag],U)),tags))	#[[tagIdx,...],...]
		return super().search(raw={"regMemo":regMemo,"tagIdxes":tagIdxes})
	def search2(self,memo=str(),tags=str()):
		tags=self.getTagsRec(tags,self.getU())
		for card in self.search(memo):
			cardMemo=card.memo(self.text)
			if any(map(lambda tag:tag in cardMemo,tags)):
				yield card
	def getTags(self):
		return list(map(lambda tagIdx:tagIdx.get(self.text),self.getU()))
	def getAllTags(self):
		return list(set(self.getTags()+list(self.getTagsInTOT())))
	def getU(self):
		tags=list()
		for card in self.cards.values():
			tags.extend(card.tagIdxes)
		return list(set(tags))

class TagDB(BaseTagDB):
	TAG_FILE="tag.txt"
#tag:[cardID,...]
#card : memo,comment,date
	def __init__(self,dname):
		super().__init__(dname,__index__.SimpleCard,False)
	def dump(self,card,mode=15):
		return __data__.CSM.makeOne(self.text,card).dump(mode)
	def dumpCSM(self):
		for key in self.cardToTags:
			card=self.cards.get(key)
			if not card:
				continue
			card=__index__.Card(card.memoIdx,card.commentIdx,self.cardToTags[key],card.date)
			yield __data__.CSM.makeOne(self.text,card)
	def append(self,memo,comment=str(),tags=list(),date=str(datetime.datetime.now()),override=False):
		if not tags:
			return False
		return super().append(override,tags,toIndex={"memoIdx":memo,"commentIdx":comment},raw={"date":date})
	def searchForTagAsCard(self,tags):
#res as Card
		for card in self.searchForTagOnlyCard(tags):
			yield __index__.Card(card.memoIdx,card.commentIdx,self.cardToTags.get(card.id,[]),card.date)
	def search(self,memo="",tags=[]):
		if not memo:
			for card in self.searchForTagAsCard(tags):
				yield card
		else:
			regMemo=re.compile(memo)
			for card in self.searchForTagAsCard(tags):
				#csm=list(__data__.CSM.makeForSimpleCard(self.text,[card]))[0]
				if re.search(regMemo,card.memo(self.text)):
					yield card
	def appendCSM(self,csm,override=False):
		return self.append(csm.memo,csm.comment,csm.tags,csm.date,override)
	def appendCSMs(self,csms,override=False):
		for csm in csms:
			self.appendCSM(csm,override)
	def appendDB(self,dst,memo=str(),tags=list(),override=False):
		TOT_DB.appendDB(self,dst,override)
		for csm in __data__.CSM.make(dst.text,dst.search(memo,tags)):
			self.appendCSM(csm,override)
	def appendCardDB(self,cardDB,override=False):
		TOT_DB.appendDB(self,cardDB,override)
		for csm in __data__.CSM.make(cardDB.text,cardDB.cards.values()):
			self.appendCSM(csm,override)
	def clean(self):	#clean data 
		tmpDname="___"+str(random.random()).replace(".","___")
		os.makedirs(tmpDname)
		#save data to tmp dname.
		for tot in self.dumpTOT():
			tot.write(os.path.join(tmpDname,tot.fname))
		for csm in __data__.CSM.make(self.text,self.search()):
			csm.write(os.path.join(tmpDname,csm.fname))
		shutil.rmtree(self.dname)	#remove all file
		self.clear()	#remove clear data
		os.makedirs(self.dname)
#append data from tmp dir.
		for fname in os.listdir(tmpDname):
			fname=os.path.join(tmpDname,fname)
			if __data__.CSM.EXT not in fname:
				continue
			csm=__data__.CSM.read(fname)
			if __data__.TOT.isTOT(csm):
				tot=__data__.TOT.toTOT(csm)
				self.appendTOT(tot.name,tot.childs)
			else:
				self.appendCSM(csm)
		shutil.rmtree(tmpDname)	#remove tmp
		self.save()
				

class BaseHomeDB(BaseTagDB):
	"""
	HomeDB manage DB.
	"""
	def __init__(self,dname,CardDBClass=__index__.DB,DBClass=CardDB,cardAsBytes=True):
#DBClass is for select
		super().__init__(dname,CardDBClass,cardAsBytes)
		self.CardDBClass=CardDBClass
		self.DBClass=DBClass
		self.selectedDBs={}	#have DataBases for select. {<dbid>:<DB Object>,...}
	def getPath(self,dbid):
#getPath of dname specified by dbid
		return os.path.join(self.dname,dbid)
	def listDB(self):
		return self.cards.values()
	def search(self,dbid=".*",tags=[]):
		dbid=dbid.upper()
		for card in self.searchForTagOnlyCard(tags):
			card_dbid=card.getID(self.text)
			if re.fullmatch(dbid,card_dbid):
				yield card
	def dumpDB(self):
		return filter(lambda db:db,map(lambda dbIdx:self.select(dbIdx.getID(self.text)),self.listDB()))
	def select(self,dbid,*args,**kwargs):	#return DB of DataBase
#return ServerDB specified by dbid.
#server_addr is of returned ServerDB
		dbid=dbid.upper()
		if self.selectedDBs.get(dbid):
			return self.selectedDBs.get(dbid)
		db=self.get(self.find(dbid))
		if db:
			try:
				db=self.DBClass(self.getPath(dbid),*args,**kwargs)
			except Exception as e:
				print(e)
				raise e
			self.selectedDBs[dbid]=db
			return db
		return None
		
	def append(self,dbid,tags):
#append DB.
		dbid=dbid.upper()
		dbDname=self.getPath(dbid)
		if not super().append(False,tags,toIndex={"idIdx":dbid}):
			return
		if not os.path.exists(dbDname):
			os.mkdir(dbDname)
	def remove(self,dbid):
#Remove DB specified by dbid
		dbidIdx=self.find(dbid)
		if super().remove(dbidIdx):	#if index is removed
			try:
				shutil.rmtree(os.path.join(self.dname,dbid))	#remove data
			except:
				pass
			if self.selectedDBs.get(dbid):	
				self.selectedDBs.pop(dbid)
			return True
		return False
	def getDBIDs(self,dbid):
		return getDBIDs(self,dbid)
	def getDBID(self,dbid):
		dbids=list(getDBIDs(self,dbid))
		return dbids[0] if dbids else None
	def close(self):
		super().close()
		self.cleanTag()
		for db in self.selectedDBs.values():
			db.close()
		self.save()

class HomeTagDB(BaseHomeDB):
	def __init__(self,dname):
		super().__init__(dname,DBClass=TagDB,cardAsBytes=False)


def compile_dbid(s):
	s__=""
	for i,c in enumerate(s):
		if c=="*":
			if i==0 or not _util.is_rechar(s[i-1]):
				s__+=".*"
			else:
				s__+=c
		else:
			s__+=c
	return re.compile(s__)

def getDBIDs(homeDB,dbid):
#get DBID .it is not locked.
#if locked is True,you can get db locked.
	#dbid=re.sub(".*",".*",dbid.upper())
	if type(dbid) is str:
		dbid=dbid.upper()
		#dbid=re.compile(dbid)
		dbid=compile_dbid(dbid)
	for db in list(homeDB.listDB()):
		dbid__=db.getID(homeDB.text)
		if re.fullmatch(dbid,dbid__):
			yield dbid__

