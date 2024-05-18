from . import _util
from . import __db__
from . import __index__
import re
import os
import datetime

class Text:	#For don't copy and to reference
	def __init__(self,text=str()):
		self.data=text
	def __getattr__(self,attr):
		return getattr(self.data,attr)
	def __str__(self):
		return self.data
	def __getitem__(self,key):
		return self.data[key]
	def __len__(self):
		return len(self.data)
	def __add__(self,s):
		return self.data+s
	def __iadd__(self,s):
		self.data=self.data+s
		return self

def find(s,text):
	if not s:
		return __index__.Index(0,0)
	n=text.find(s)
	if n==-1:
		return __index__.Index()
	return __index__.Index(n,len(s))



class CSM:
	EXT="csm"
	SEQ="\n\n"
	TAG_SEQ=","
	def __init__(self,memo=str(),comment=str(),tags=list(),date=str()):
		self.id=_util.hash(memo) if memo else 123456789
		self.memo=memo
		self.comment=comment
		self.tags=tags
		self.date=date or str(datetime.datetime.now()).split(".",1)[0]
	def __hash__(self):
		return hash(self.id)
	def __eq__(self,dst):
		return self.id==dst.id
	def __str__(self):
		return CSM.SEQ.join((self.memo,self.comment,CSM.TAG_SEQ.join(self.tags),self.date))
	def __bool__(self):
		return bool(self.memo)
	def dump(self,mode="mctd"):
		res=str()
		mode=mode.upper()
		if "A" in mode:
			return str(self)+"\n\n"+self.fname
		if "M" in mode:
			res+=self.memo+"\n\n"
		if "C" in mode:
			res+=self.comment+"\n\n"
		if "T" in mode:
			res+=",".join(self.tags)+"\n\n"
		if "D" in mode:
			res+=self.date+"\n\n"
		if "F" in mode:
			res+=self.fname
		return res.rstrip()
	def write(self,fname):
		with open(fname,"w") as f:
			f.write(str(self))
	@property
	def fname(self):
		return str(self.id)+"."+CSM.EXT	#Escape because if id start is "-" it's bad.
	@staticmethod
	def isCSM(fname):
		return "."+CSM.EXT in fname
	@staticmethod
	def read(fname):
		with open(fname,"r") as f:
			data=f.read().split(CSM.SEQ,3)
			len_data=len(data)
			memo=data[0].rstrip() if len_data>0 else ""
			comment=data[1].rstrip() if len_data>1 else ""
			tags=data[2].rstrip().split(CSM.TAG_SEQ) if len_data>2 else ""
			if len(data)>=4:
				date=data[3].rstrip()
			else:
				date=str()
			return CSM(memo,comment,tags,date)
	def readDir(dname):
		for fname in os.listdir(dname):
			fname=os.path.join(dname,fname)
			if CSM.EXT in fname:
				yield CSM.read(fname)
	@staticmethod
	def makeForSimpleCard(text,cards=None):
		for card in cards:
			yield CSM(card.memo(text),card.comment(text),[],card.date)
	@staticmethod
	def make(text,cards=None):
		for card in cards:
			yield CSM(card.memo(text),card.comment(text),card.tags(text),card.date)
	@staticmethod
	def makeOne(text,card):
		return list(CSM.make(text,[card]))[0]
	@staticmethod
	def readText(text):
		text=text.split(CSM.SEQ)
		lenText=len(text)
		memo=text[0] if lenText>=1 else ""
		comment=text[1] if lenText>=2 else ""
		tags=text[2].split(CSM.TAG_SEQ) if lenText>=3 and text[2] else []
		date=text[3] if lenText>=4 else "1900-12-31"
		return CSM(memo,comment,tags,date)
	@staticmethod
	def loads(text):
		return CSM.readText(text)



class TOT(CSM):
#{"name":"* ...","tags":["- ...","- ...",...]}
	TAG="TAG_OF_TAG"
	NAME_HEAD="*"
	CHILD_HEAD="-"
	@property
	def name(self):
		name=self.comment.split("\n")[0]
		if name[0]==TOT.NAME_HEAD:
			return name[1:]
		return name
	@property
	def childs(self):
		lines=self.comment.split("\n")
		if len(lines)>1:
			return list((map(lambda line:line[1:] if line and line[0]==TOT.CHILD_HEAD else line,lines[1:])))
		else:
			return []
	@staticmethod
	def isTOT(csm):
		return TOT.TAG in csm.tags
	@staticmethod
	def __toTOT__(memo,comment,tags,date):
		return TOT(memo,comment,tags,date)
	@staticmethod
	def toTOT(csm):
		if not TOT.isTOT(csm):
			return TOT()
		return TOT.__toTOT__(csm.memo,csm.comment,csm.tags,csm.date)
	@staticmethod
	def unEscapeName(s):
		if not s:
			return s
		elif s[0]==TOT.NAME_HEAD:
			return s[1:]
		else:
			return s
	@staticmethod
	def unEscapeChild(tag):
		if not tag:
			return tag
		elif tag[0]==TOT.CHILD_HEAD:
			return tag[1:]
		else:
			return tag
	@staticmethod
	def unEscapeChilds(tags):
		return list(map(lambda tag:TOT.unEscapeChild(tag),tags))
	@staticmethod
	def read(fname):	#Res Empty TOT if csm isn't TOT.
		csm=CSM.read(fname)
		return TOT.toTOT(csm)
	@staticmethod
	def readText(text):
		csm=CSM.readText(text)
		if TOT.isTOT(csm):
			return TOT.toTOT(csm)
		return TOT()
	@staticmethod
	def readDir(dname):
		for fname in os.listdir(dname):
			fname=os.path.join(dname,fname)
			if CSM.EXT in fname:
				csm=CSM.read(fname)
				if TOT.isTOT(csm):
					yield TOT.toTOT(csm)

	@staticmethod
	def make(text,tots=None):
		for tot in tots:
			yield TOT.make2(str(Logic.Group.makeFromIndex(tot.nameGroup,text)),[str(Logic.Group.makeFromIndex(tagGroup,text)) for tagGroup in tot.tagGroups])
	@staticmethod
	def makeOne(text,tot):
		return list(TOT.make(text,[tot]))[0]
	@staticmethod
	def make2(name,tags):
		comment=TOT.NAME_HEAD+TOT.unEscapeName(name)
		tags="\n".join(map(lambda tag:TOT.CHILD_HEAD+TOT.unEscapeChild(tag),tags))
		if tags:
			comment+="\n"+tags
		return TOT(str(_util.hash(name)),comment,[TOT.TAG],"1900")	#you may not need to care name because name don't associate when this is read.




class Logic:
	KAKKO=("(",")")
	NORMAL=str()
	NOT="-"
	AND="&&"
	OR="||"
	@staticmethod
	def expandReg(s,allTags):
		try:
			regS=re.compile(s) if type(s) is not re.Pattern else s
		except Exception as e:
			#print(e,s)
			return s
		tags=list(filter(lambda tag:re.fullmatch(regS,tag),allTags))
		if not tags:
			return s
		return Logic.OR.join(tags)
	class Attr:
		@staticmethod
		def toIndex(attr):
			if attr==Logic.KAKKO[0]:
				return __index__.Logic.KAKKO[0]
			elif attr==Logic.KAKKO[1]:
				return __index__.Logic.KAKKO[1]
			elif attr==Logic.NOT:
				return __index__.Logic.NOT
			elif attr==Logic.AND:
				return __index__.Logic.AND
			elif attr==Logic.OR:
				return __index__.Logic.OR
			return __index__.Logic.NORMAL
		@staticmethod
		def toStr(attr):
			if attr==__index__.Logic.KAKKO[0]:
				return Logic.KAKKO[0]
			elif attr==__index__.Logic.KAKKO[1]:
				return Logic.KAKKO[1]
			elif attr==__index__.Logic.NOT:
				return Logic.NOT
			elif attr==__index__.Logic.AND:
				return Logic.AND
			elif attr==__index__.Logic.OR:
				return Logic.OR
			return Logic.NORMAL
	
	Data=__index__.Logic.Data
	
	class Tag:
		IS_TOT="%TOT%"
		def __init__(self,tag=str(),attr=str(),not_=False):
			self.tag=tag
			self.attr=attr
			self.not_=not_
		def __iter__(self):
			if not self:
				return
			if self.not_:
				return iter((Logic.NOT,self.tag))
			return iter([self.tag])
		def iterTag(self):
			if self:
				return iter([self.tag])
		@staticmethod
		def make(s):
			if not s:
				return Logic.Tag()
			elif s[0]==Logic.NOT:
				if len(s)==1:
					return Logic.Tag(not_=True)
				return Logic.Tag(s[1:],not_=True)
			return Logic.Tag(s)
		@staticmethod
		def isTag(s):
			return not ( Logic.AND in s or Logic.OR in s or (Logic.KAKKO[0] in s and Logic.KAKKO[1] in s) )
		def __bool__(self):
			return bool(self.tag)
		def __eq__(self,dst):
			return self.tag==dst.tag and self.not_==dst.not_
		def __str__(self):
			return "".join(self)
		def dump(self):
			return "(TAG:{0} ATTR:{1})".format(self.tag,self.attr)
		def toIndex(self,text):
			if self==self.isTOTTag():
				return __index__.Logic.Tag.isTOTTag()
			tagIdx=find(self.tag,text)
			if not tagIdx:
				return __index__.Logic.Tag()
			return __index__.Logic.Tag(tagIdx,Logic.Attr.toIndex(self.attr),__index__.Logic.NOT if self.not_ else 0)
		@staticmethod
		def isTOTTag():
			return Logic.Tag(Logic.Tag.IS_TOT)
		@staticmethod
		def specialTags():
			return [Logic.Tag.isTOTTag()]
	class Group:
		def __init__(self,left=None,right=None,attr=None,not_=False):
			self.left=left if left else Logic.Tag()
			self.right=right if right else Logic.Tag()
			self.attr=attr if attr else Logic.OR
			self.not_=not_
		def __iter__(self):
			if self.left:
				if self.right:
					res=(*self.left,self.attr,*self.right)
				else:
					res=self.left
			else:
				if self.right:
					res=self.right
				else:
					res=[]
			if self.not_:
				return iter((Logic.NOT,*res))
			return iter(res)
		def iterTag(self):
			res=list()
			if self.left:
				res.extend(self.left.iterTag())
			if self.right:
				res.extend(self.right.iterTag())
			return iter(res)
		def __eq__(self,dst):
			return str(self)==str(dst)
		def __str__(self):
			return "("+"".join(iter(self))+")"
		def dump(self):
			return "LEFT:\n\t{0} \nRIGHT:\n\t{1} \nATTR:{2}".format("\n\t".join(self.left.dump().split("\n")),"\n\t".join(self.right.dump().split("\n")),self.attr)
		def __bool__(self):
			return bool(self.left) or bool(self.right)
		def toIndex(self,text):
			return __index__.Logic.Group(self.left.toIndex(text),self.right.toIndex(text),Logic.Attr.toIndex(self.attr),self.not_)
		@staticmethod
		def getInKAKKO(s,start):
			if s[start]!=Logic.KAKKO[0]:
				return (-1,Logic.Tag())
			i=start+1
			end=-1
			lenS=len(s)
			count=1
			while i<lenS:
				if s[i]==Logic.KAKKO[0]:
					count+=1
				elif s[i]==Logic.KAKKO[1]:
					count-=1
				if count==0:
					end=i
					break
				i+=1
			if end>0:
				return (end,Logic.Group.make(s[start+1:end]))
			return (-1,Logic.Tag())
		@staticmethod
		def make(s,allTags=list()):
#allTags is for expandReg.
			checked=Logic.Group()
			i=0
			data=""
			beforeAttr=Logic.OR
			if Logic.Tag.isTag(s):	#if tag 
				s=Logic.expandReg(s,allTags)
				if Logic.Tag.isTag(s):	#if pure tag return
					return Logic.Group(Logic.Tag.make(s))
			lenS=len(s)
			not_=False
			while i<lenS:
				if s[i]==Logic.NOT and not data:
					not_=True
					i+=1
				elif s[i]==Logic.KAKKO[0]:
					end,g=Logic.Group.getInKAKKO(s,i)
					if end==-1:
						raise Exception('left of "(" is nothing.')
					g.not_=not_
					checked=Logic.Group(checked,g,beforeAttr)
					beforeAttr=Logic.OR
					not_=False
					i=end+1
				else:
					if i+1>=lenS:
						attrs=[]
					else:
						attrs=list(filter(lambda attr:s[i:i+2]==attr,(Logic.AND,Logic.OR)))
					if attrs:
						attr=attrs[0]
						data=Logic.expandReg(data,allTags)
						g=Logic.Group.make(data)
						g.not_=not_	
						checked=Logic.Group(checked,g,beforeAttr)
						data=""		#init data because data is checked
						not_=False
						beforeAttr=attr
						i+=2
					else:
						data+=s[i]
						i+=1
			g=Logic.Group.make(Logic.expandReg(data,allTags))	#data is tag or group
			g.not_=not_
			return Logic.Group(checked,g,beforeAttr)
		@staticmethod
		def makeFromIndex(g,text):
			#print("GGG",g,type(g),type(text))
			if type(g) is __index__.Logic.Tag:
				if g==__index__.Logic.Tag.isTOTTag():
					return Logic.Tag.isTOTTag()
				return Logic.Tag(g.name(text),Logic.Attr.toStr(g.attr),g.not_)
			return Logic.Group(Logic.Group.makeFromIndex(g.left,text),Logic.Group.makeFromIndex(g.right,text),Logic.Attr.toStr(g.attr),g.not_)


