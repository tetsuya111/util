from . import __utils__
import datetime
from functools import *
import json
import pickle

class Point:
	SEQ=","
	def __init__(self,data):
		self.__data=data
	@property
	def data(self):
		return self.__data
	@property
	def x(self):
		return self.__data[0]
	@property
	def y(self):
		return self.__data[1]
	def __bool__(self):
		return any(map(lambda a:a!=0,self))
	def __eq__(self,dst):
		return all(map(lambda a,b:a==b,self,dst))
	def __iter__(self):
		return iter(self.__data)
	def __str__(self):
		return "("+Point.SEQ.join(map(str,self))+")"
	def __hash__(self):
		return hash(str(self))
	def __getitem__(self,key):
		return self.__data[key]


class Index(Point):
	SEQ=","
	def __init__(self,start=0,length=0):	#x is start,y is length
		super().__init__([start,length])
	def __hash__(self):
		return hash(str(self))
	def __lt__(self,dst):
		if self.start==dst.start:
			return self.end<dst.end
		return self.start<dst.start
	def __gt__(self,dst):
		return not (self==dst or self<dst)
	def __str__(self):
		return Index.SEQ.join(map(str,self))
	@staticmethod
	def read(s):
		return Index(*map(int,s.split(Index.SEQ,1)))
	@property
	def start(self):
		return self.x
	@property
	def length(self):
		return self.y
	@property
	def end(self):
		return self.start+self.length
	def get(self,text):
		return text[self.start:self.end]
	def in_(self,dst):
		return dst.start<=self.start<=self.end<=dst.end
	def or_(self,dst):
		return Index(min(self.start,dst.start),max(self.end,dst.end)-min(self.start,dst.start))
	def else_(self,dst):
		if self.start<dst.start:
			yield Index(self.start,dst.start-self.start)
		if self.end>dst.end:
			yield Index(dst.end,self.end-dst.end)
	def match(self,dst):
		return self.start==dst.start and self.start<=dst.end<=self.end
	def finditer(self,tag):
		return re.finditer(tag,self.data)

class Mode:
	CARD=0
	MEMO=1
	COMMENT=2
	TAG=4
	DATE=8
	TOT=16
	MAX=16
	ALL=31


class BaseCard:
	"""
	property:
		id : id of Card
	function:
		__bool__ : Return if empty
		read : read line and to memoIdx
		__bytes__,__str__ : for write file.must not include "\n" because it is selialize lines and another memoIdx
	"""
	def __init__(self):
		pass
	@property
	def id(self):
		return ""
	def __hash__(self):
		return hash(self.id)
	def __eq__(self,dst):
		return self.id==dst.id
	def __bool__(self):
		return bool(self.id)
	def read(self,line):
		return pickle.loads(line)
	def __bytes__(self):
		return pickle.dumps(self)

class Tag(BaseCard):
	SEQ=" "
	SEQ_N=","
	def __init__(self,tagIdx,cardIDs=list()):
#CardID is Index
		self.tagIdx=tagIdx
		self.cardIDs=list(cardIDs)
	@property
	def id(self):
		return self.tagIdx
	def tag(self,text):
		return self.tagIdx.get(text)
	def toData(self):
		return (self.id.data,[cardID.data for cardID in self.cardIDs])
	def __str__(self):
		return json.dumps(self.toData())
	def append(self,cardID):
		self.cardIDs.append(cardID)
	def __iter__(self):
		return iter(self.cardIDs)
	def __len__(self):
		return len(self.cardIDs)
	@staticmethod
	def read(line):
		data=json.loads(line.rstrip())
		return Tag(Index(*data[0]),[Index(*data__) for data__ in data[1]])

class SimpleCard(BaseCard):
#Card don't have tagIdxes.
	def __init__(self,memoIdx=Index(),commentIdx=Index(),date=str(datetime.datetime.now())):
		self.memoIdx=memoIdx
		self.commentIdx=commentIdx
		self.date=date
	@property
	def id(self):
		return self.memoIdx
	def toData(self):
		return (self.memoIdx.data,self.commentIdx.data,self.date)
	def __str__(self):
		return json.dumps(self.toData())
	def memo(self,text):
		return self.memoIdx.get(text)
	def comment(self,text):
		return self.commentIdx.get(text)
	@staticmethod
	def read(line):
#<id> x,y x,y date
		data=json.loads(line.rstrip())
		return SimpleCard(Index(*data[0]),Index(*data[1]),data[2])


class Card(SimpleCard):
#Card have tagIdxes
	SEQ_TERM=" "
	SEQ_N=","
	def __init__(self,memoIdx=Index(),commentIdx=Index(),tagIdxes=list(),date=str(datetime.datetime.now())):
#(x,y) is index of file start and end.
		super().__init__(memoIdx,commentIdx,date)
		self.tagIdxes=tagIdxes
	def toData(self):
		return (self.memoIdx.data,self.commentIdx.data,[tagIdx.data for tagIdx in self.tagIdxes],self.date)
	def __str__(self):
		return json.dumps(self.toData())
	def tags(self,text):
		return [tagIdx.get(text) for tagIdx in self.tagIdxes]
	@staticmethod
	def read(line):
#<id> x,y x,y x,y x1,y1,x2,y2,... date
		data=json.loads(line.rstrip())
		return Card(Index(*data[0]),Index(*data[1]),[Index(*data__) for data__ in data[2]],data[3])


class TOT:
	def __init__(self,nameGroup,tagGroups):	
		self.nameGroup=nameGroup
		self.tagGroups=tagGroups
	@property
	def id(self):
		return self.nameGroup.id
	def __hash__(self):
		return hash(self.id)
	@staticmethod
	def getID(group):
		if type(group) is Index:
			return Index(group.start,group.end)
		elif type(group) is Logic.Tag:
			tags=[group]
		else:
			tags=group.iterTag()
		n=list()
		for tag in tags:
			n.append(tag.nameIdx.start)
			end=tag.nameIdx.end*(-1 if tag.not_ else 1)
			n.append(end)
		#n=list(filter(lambda n:n>0,group))
		return Index(min(n),max(n)) if n else Index()
	@staticmethod
	def read(line):
		data=line.rstrip().split(Card.SEQ_TERM)
		nameGroup=Logic.Group.make(list(map(int,data[0].split(Card.SEQ_N))))
		#if not nameGroup:
		#	return None
		nameGroup=nameGroup[0]
		if len(data)>1:
			tagGroups=Logic.Group.make(list(map(int,data[1].split(Card.SEQ_N))))
		else:
			tagGroups=list()
		return TOT(nameGroup,tagGroups)
	def __str__(self):
		return Card.SEQ_TERM.join(map(str,\
			(self.nameGroup,Card.SEQ_N.join(map(str,self.tagGroups)))\
			))
	def dump(self):
		return "NAME:{0} TAGS:{1}".format(self.nameGroup.dump(),",".join(map(lambda group:group.dump(),self.tagGroups)))
	def getChilds(self,tots):
		for tot in tots:
			if tot.nameGroup in self.tagGroups:
				yield tot
	def get(self,U,tots):
		for tagIdx in self.nameGroup.get(U,tots,[self.id]):
			yield tagIdx
		for tagIdx in self.getRec(U,tots,[self.id]):
			yield tagIdx
	def getRec(self,U,tots,exploredTOT=list()):	#get under this.
		if self.id in exploredTOT:
			return
#exploredTOT is special case of exploredG. tag have tot childs but tag possibilly have else childs.	(A&&B)
		for tagGroup in self.tagGroups:
			if tagGroup.isTOT():	#if group is range  of TOT,get only as TOT.
				for tagIdx in tagGroup.getAsTOT(U,tots,exploredTOT+[self.id]):
					yield tagIdx
			else:
#get data as child of TO
				for tagIdx in tagGroup.get(U,tots,exploredTOT+[self.id]):
					yield tagIdx



class Logic:
	NORMAL=0
	NOT=-1
	AND=-2
	OR=-4
	KAKKO=(-8,-16)
	def isLogical(n):
		return n<0
	class Data:
		def __init__(self,data=[],not_=False):
			self.data=list(data)
			self.not_=not_
		def isNot(self):
			return self.not_
		def alter(self):
			return type(self)(self.data,False if self.not_ else True)
		def __add__(self,dst):
			return self.or_(dst)
		def __call__(self,U):
			if self.not_:
				return list(filter(lambda tag:tag not in self.data,U))
			return self.data
		def and_(self,dst):
			if not self.not_:
				if not dst.not_:
					return type(self)(filter(lambda tag:tag in dst.data,self.data),False)
				return type(self)(filter(lambda tag:tag not in dst.data,self.data),False)
			else:
				if not dst.not_:
					return dst.and_(self)
				return self.alter().or_(dst.alter()).alter()
		def or_(self,dst):
			if not self.not_:
				if not dst.not_:
					return type(self)(set(self.data+dst.data))	#this is necesarry because it is used in and_.
			return self.alter().and_(dst.alter()).alter()
		def else_(self,dst):
			return self.and_(dst.alter())
	class Tag:
		IS_TOT=Index(-4545,-5454)
		def __init__(self,nameIdx=Index(),attr=0,not_=False):
			self.nameIdx=nameIdx
			self.attr=attr
			self.not_=not_
			self.id=TOT.getID(self.nameIdx)
		def __hash__(self):
			return hash(self.id)
		def name(self,text):
			return self.nameIdx.get(text)
		def isNot(self):
			return self.not_
		def __get__(self,U,tots,exploredTOT=list()):
			res=[self.nameIdx]	#res this
			tot=tots.get(self.id)
			#if tot and not (tot.id in exploredG or tot.id in exploredTOT):
			if tot:
#if this tag is tot,get childs rec.
				for tag in tot.getRec(U,tots,exploredTOT):	#res under this.
					res.append(tag)
			return Logic.Data(list(set((filter(lambda data__:data__,res)))),self.not_)	#remove Index(0,0)
		def get(self,U,tots):
			return self.__get__(U,tots).data
		def dump(self):
			return "(NAME:{0} NOT:{1})".format(self.nameIdx,self.not_)
		def __abs__(self):
			if self.isNot():
				return self.alter()
			return self
		def __bool__(self):
			return bool(self.nameIdx)
		def alter(self):
			not_=False if self.not_ else True
			return Logic.Tag(self.nameIdx,self.attr,not_)
		def __eq__(self,dst):
			return self.nameIdx==dst.nameIdx and self.attr==dst.attr and self.not_==dst.not_
		def __str__(self):
			if self.isNot():
				return Card.SEQ_N.join(map(str,(Logic.NOT,*self.nameIdx)))
			return Card.SEQ_N.join(map(str,self.nameIdx))
		def __iter__(self):
			if not self:	#if res Tag(),Tag() contained Group iterator.
				return iter([])
			if self.isNot():
				return iter([Logic.NOT,*self.nameIdx])
			return iter(self.nameIdx)
		def iterTag(self):	#for iterTag() of Group
			if self:
				yield self
		@staticmethod
		def isTOTTag():
			return Logic.Tag(Logic.Tag.IS_TOT)
		@staticmethod
		def specialTags():
			return [Logic.Tag.isTOTTag()]
	class Group:
#Tag() is dummy
		def __init__(self,left=None,right=None,attr=0,not_=False):
			self.left=left if left else Logic.Tag()
			self.right=right if right else Logic.Tag()
			self.attr=attr if attr else Logic.OR
			self.not_=not_
			self.id=self.getID()
		def getID(self):
			n=list()
			specialTags=Logic.Tag.specialTags()
			for tag in filter(lambda tag:tag not in specialTags,self.iterTag()):
				n.append(tag.nameIdx.start)
				end=tag.nameIdx.end*(-1 if tag.not_ else 1)
				n.append(end)
			#n=list(filter(lambda n:n>0,group))
			return Index(min(n),max(n)) if n else Index()
		def __hash__(self):
			return hash(self.id)
		def __bool__(self):
			return bool(self.left) or bool(self.right)
		def isTOT(self):
			return Logic.Tag.isTOTTag() in self.iterTag()
		def toTOT(self):
			return Logic.Group(Logic.Tag.isTOTTag(),self,Logic.AND)
		def dump(self):
			return "(LEFT:{0} RIGHT:{1} ATTR:{2})".format(self.left.dump(),self.right.dump(),self.attr)
		def __str__(self):
			if self.attr==Logic.NORMAL:
				return Card.SEQ_N.join(map(str,self))
			return Card.SEQ_N.join(map(str,self))
		def __eq__(self,dst):
			return self.id==dst.id and self.not_==dst.not_
			#return self.left==dst.left and self.right==dst.right and self.attr==dst.attr 
		def __iter__(self):
			if self.left:
				if self.right:
					res=(Logic.KAKKO[0],*self.left,self.attr,*self.right,Logic.KAKKO[1])
				else:
					res=(Logic.KAKKO[0],*self.left,Logic.KAKKO[1])
			else:
				res=(Logic.KAKKO[0],*self.right,Logic.KAKKO[1])
			if self.not_:
				return iter((Logic.NOT,*res))
			return iter(res)
		def iterTag(self):
			return iter((*self.left.iterTag(),*self.right.iterTag()))
		def __getAsTOT__(self,U,tots,exploredTOT=list()):
			if tots.get(self.id):	#first get tag as TOT.
				return Logic.Data(tots[self.id].getRec(U,tots,exploredTOT))
			return Logic.Data()
		def getAsTOT(self,U,tots,exploredTOT=list()):
			return self.__getAsTOT__(U,tots,exploredTOT).data
		def __get__(self,U,tots,exploredTOT=list()):	
			data0=self.__getAsTOT__(U,tots,exploredTOT)
			data1=self.left.__get__(U,tots,exploredTOT+[self.id])	#this is data
			data2=self.right.__get__(U,tots,exploredTOT+[self.id])	#this is data
			#print("LEFT",data1.data)
			#print("RIGHT",data2.data)
			if self.attr==Logic.AND:
				res=data0.or_(data1.and_(data2))
			elif self.attr==Logic.OR:
				res=data0.or_(data1.or_(data2))
			else:
				res=data0
			return res.alter() if self.not_ else res
		def get(self,U,tots,exploredTOT=list()):	#Group.get don't res attr.but Tag res.So we must use __get__
			return self.__get__(U,tots,exploredTOT)(U)
		@staticmethod
		def getInKAKKO(numbers,start):
#res (endOfKakko,data)
			if numbers[start]!=Logic.KAKKO[0]:
				return (-1,Logic.Tag())
			i=start+1
			end=-1
			lenNumbers=len(numbers)
			count=1
			while i<lenNumbers:
				if numbers[i]==Logic.KAKKO[0]:
					count+=1
				elif numbers[i]==Logic.KAKKO[1]:
					count-=1
				if count==0:
					end=i
					break
				i+=1
			if end>0:
				return (end,Logic.Group.make(numbers[start+1:end]))
			return (-1,Logic.Tag())
		@staticmethod
		def make(numbers):
			checked=[]
			lenN=len(numbers)
			i=0
			not_=False
			before_attr=None
#if before_attr is None ,it is start of group.
			while i+1<lenN:	#get one index a two number.
				if numbers[i]==Logic.NOT:
					not_=True
					i+=1
				elif numbers[i]==Logic.KAKKO[0]:
					end,g=Logic.Group.getInKAKKO(numbers,i)
					if end==-1:
						raise Exception('left of "(" is nothing.')
					if g:
						g=g[0]
						g.not_=not_
						not_=False
						if before_attr:
							checked.append(Logic.Group(checked.pop(),g,before_attr))
							before_attr=None
						else:
							checked.append(g)
					i=end+1
				else:
					attrs=list(filter(lambda attr:numbers[i]==attr,(Logic.AND,Logic.OR)))
					if attrs:
						before_attr=attrs[0]
						i+=1
					else:
						t=Logic.Tag(Index(numbers[i],numbers[i+1]),attr=Logic.NORMAL,not_=not_)
						i+=2
						not_=False
						if before_attr:
							checked.append(Logic.Group(checked.pop(),t,before_attr))
							before_attr=None
						else:
							checked.append(Logic.Group(t))
			return checked





class DB(BaseCard):
	SEQ_TERM=" "
	SEQ_N=","
	def __init__(self,idIdx):
		self.idIdx=idIdx
	def __bool__(self):
		return bool(self.id)
	def __str__(self):
		return json.dumps([self.idIdx.data])
	@property
	def id(self):
		return self.idIdx
	def getID(self,text):
		return self.idIdx.get(text)
	@staticmethod
	def read(line):
		data=json.loads(line.rstrip())
		return DB(Index(*data[0]))
