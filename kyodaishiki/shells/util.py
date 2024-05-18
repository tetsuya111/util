from kyodaishiki import __data__
from kyodaishiki import _util
from kyodaishiki import __server__
from kyodaishiki import __shell__
from kyodaishiki import __db__
from . import augment_hs
import docopt
import os
import subprocess as sp
import shutil
import re
import copy
import random
import sys
import datetime
import functools
import winshell

DEFAULT_DUMP_HOME_DIR=_util.realpath("%USERPROFILE%\\desktop\\dumpedHome")
DEFAULT_BACKUP_DIR=_util.realpath("%USERPROFILE%\\desktop\\buckeupedHome")
DEFAULT_BACKUP_HOME_DIR=_util.realpath("%USERPROFILE%\\desktop\\buckeupedHomeData")
DEFAULT_DUMP_TAG_FNAME=_util.realpath("%USERPROFILE%\\desktop\\dumpedtag.csm")
DEFAULT_CSM_DIR_F=lambda db_dname:r"{0}\csmFiles".format(_util.realpath(db_dname))
DEFAULT_DUMP_CSM_DIR_F=_util.realpath(r"%USERPROFILE%\desktop\util_dumped_db")
BACKUP="BACKUP"

TMP=lambda:random.randint(10**24,10**36)

ATTR_SEQ=":"

class Attr:
	URL="URL"
	SEQ=":"
	def __init__(self,attr):
		self.attr=attr
	def format(self,value):
		return Attr.to_format(self.attr).format(value)
	def __call__(self,value):
		return self.format(value)
	@staticmethod
	def to_format(attr):
		return attr+ATTR_SEQ+"{0}"
	@staticmethod
	def parse(tags):
#res : {<attr>:[<values>...],...}
		res={}
		for attr,value in map(lambda tag:tag.split(Attr.SEQ,1),\
			filter(lambda tag:tag.find(Attr.SEQ)!=-1,tags)):
			if not res.get(attr):
				res[attr]=[]
			res[attr].append(value)
		return res
	@staticmethod
	def get(tags,attr,default=[]):
		return Attr.parse(tags).get(attr,default)

class AttrTags:
	def __init__(self,data={},else_tags=[]):
#data = {<attr>:<values>...,...}
		self.data=data
		self.else_tags=list(else_tags)
	def append(self,attr,value):
		if not self.data.get(attr):
			self.data[attr]=[]
		return self.data[attr].append(value)
	def appendN(self,tag):	#N is normal.
		return self.else_tags.append(tag)
	def remove(self,attr,value):
		if not self.data.get(attr) or not value not in self.data[attr]:
			return
		return self.data[attr].remove(value)
	def removes(self,attr):
		if not self.data.get(attr):
			return
		self.data[attr]=[]
		return
	def get(self,attr):
		return self.data.get(attr,[])
	def dump(self):
		for tag in self.else_tags:
			yield tag
		for attr in self.data:
			for value in self.data[attr]:
				yield Attr(attr).format(value)
	@staticmethod
	def read(tags):
		data={}
		else_tags=[]
		for tag in tags:
			if tag.find(Attr.SEQ)!=-1:
				attr,value=tag.split(Attr.SEQ,1)
				if not data.get(attr):
					data[attr]=[]
				data[attr].append(value)
			else:
				else_tags.append(tag)
		return AttrTags(data,else_tags)
attr_to_format=Attr.to_format

class Data:
	class DB:
		def __init__(self,dname):
			dname=_util.realpath(dname)
			if not os.path.exists(dname):
				os.makedirs(dname)
			self.dname=dname
			self.csms=[]
			self.tots=[]
			self.read(dname)
		def read(self,dname):
			for fname__ in os.listdir(dname):
				if ".csm" not in fname__:
					continue
				try:
					csm=__data__.CSM.read(os.path.join(dname,fname__))
				except:
					continue
				if __data__.TOT.isTOT(csm):
					self.tots.append(__data__.TOT.toTOT(csm))
				else:
					self.csms.append(csm)
		@property
		def id(self):
			return os.path.split(self.dname)[1]
		def __bool__(self):
			return bool(self.id)
		def search(self,memo="",tags=[]):
			def is_res(csm):
				return (not tags or all(map(lambda tag:tag in csm.tags,tags))) and \
					(not memo or re.search(memo,csm.memo))
			return filter(is_res,self.csms)
		def searchTOT(self,tag=""):
			return filter(lambda tot:re.search(tag,tot.name),self.tots)

	class Home:
		DB_TAG_FILE="db_tag.txt"
		#data directory instead of db.
		def __init__(self,dname):
			self.dname=dname
		@property
		def id(self):
			return os.path.split(self.dname)[1]
		def listDB(self):
			for fname in os.listdir(self.dname):
				fullname=os.path.join(self.dname,fname)	#DB dname
				if os.path.isdir(fullname):
					yield fullname
		def dumpDB(self):
			for fullname in self.listDB():
				yield Data.DB(fullname)
							
		@staticmethod
		def make(srcDname,dstDname):
			dstDname=_util.realpath(dstDname)
			if os.path.exists(dstDname):
				return None
			os.makedirs(dstDname)
			homeDB=__db__.HomeTagDB(_util.realpath(srcDname))
			for db in homeDB.dumpDB():
				db_dname=os.path.join(dstDname,db.id)
				os.makedirs(db_dname)
				for csm in db.dumpCSM():
					csm.write(os.path.join(db_dname,csm.fname))
				for tot in db.dumpTOT():
					tot.write(os.path.join(db_dname,tot.fname))
			with open(os.path.join(dstDname,Data.Home.DB_TAG_FILE),"w") as f:
				text=Data.Home.makeDBTagText(homeDB)
				f.write(text)
			return Data.Home(dstDname)
		@staticmethod
		def makeDBTagText(homeDB):
			text=""
			for card in homeDB.search():
				dbid=card.getID(homeDB.text)
				tags=map(lambda tagIdx:tagIdx.get(homeDB.text),homeDB.cardToTags.get(card.id,[]))
				text+="{0};{1}\n".format(dbid.lower(),",".join(tags))
			return text


class Tree:
	class Node:
		def __init__(self,data,childs=()):
			self.data=data
			self.childs=list(childs)
		def __hash__(self):
			return hash(self.data)
		def getRec(self):
			yield self
			for child in self.getChildsRec():
				yield child
		def getChildsRec(self):
			explored=[]
			frontiers=[self]
			while frontiers:
				now=frontiers.pop()
				if hash(now) in explored:
					continue
				for child in now.childs:
					yield child
					frontiers.append(child)
				explored.append(hash(now))
		def getDataRec(self):
			return map(lambda node:node.data,self.getRec())


class Category(Tree.Node):
	TITLE_HEAD="*"
	COL_HEAD="-"
	COMMENT=re.compile("[#\"].*")
	ATTR_FORMAT="{0}&&:{1}"
	def __init__(self,title="",cols=[],childs=()):
		super().__init__((title,list(cols)),childs)
	@property
	def title(self):
		return self.data[0]
	@property
	def cols(self):
		return self.data[1]
	def id(self):
		return self.title+str(self.childs)
	def __hash__(self):
		return hash(self.id)
	def __bool__(self):
		return bool(self.title)
	def __eq__(self,dst):	
		return self.id==dst.id
	def get_cols(self):
		for c in self.getRec():	
			for col in c.cols:
				yield col
	def toLines(self):
		yield self.TITLE_HEAD+self.title
		for col in self.cols:
			yield self.COL_HEAD+col
		for child in self.childs:
			for line in child.toLines():
				yield self.COL_HEAD+line
	def __str__(self):
		return "\n".join(self.toLines())
	def asTag(self):
		return Category(self.clean_as_tag(self.title),map(lambda col:self.clean_as_tag(col),self.cols),\
		map(lambda child:child.asTag(),self.childs))
	def __add__(self,dst):
		return Category(self.title+__data__.Logic.OR+dst.title,self.cols+dst.cols,self.childs+dst.childs)
	def concat(self,dst):
		for child in self.getChildsRec():
			if child==dst:
				child.cols.extend(dst.cols)
				child.childs.extend(dst.childs)
				return
		self.childs.append(dst)
		return
	@staticmethod
	def make_from_tot(tot,tots,text,explored=[]):
		if tot.id in explored:
			return None
		name=str(__data__.Logic.Group.makeFromIndex(tot.nameGroup,text))
		childs=[]
		cols=[]
		for tagG in tot.tagGroups:
			child=tots.get(tagG.id)
			if child:
				c=Category.make_from_tot(child,tots,text,explored+[tot.id])
				if c:
					childs.append(c)
			else:
				cols.append(str(__data__.Logic.Group.makeFromIndex(tagG,text)))
		return Category(name,cols,childs)

	@staticmethod
	def make_from_db(db):
		for key in db.tots:
			yield Category.make_from_tot(db.tots[key],db.tots,db.text)
	@staticmethod
	def subComment(s):
		return re.sub(Category.COMMENT,"",s)
	@staticmethod
	def clean_as_tag(s):
		return _util.subSpace(Category.subComment(s))
	@staticmethod
	def __read__(lines,start=0,depth=0,direct=False,title_head=None,col_head=None,lenLines=-1):
#yield (end_of_lines,Category_object)
		if lenLines<0:
			lenLines=len(lines)
		if start>=lenLines:
			return
		if not title_head:
			title_head=(Category.COL_HEAD*depth)+Category.TITLE_HEAD
		if not col_head:
			col_head=Category.COL_HEAD*(depth+1)
		reg_title_head=re.compile("^"+re.escape(title_head))
		reg_col_head=re.compile("^"+re.escape(col_head))
		#if direct and not re.match(reg_title_head,lines[start]):
		#	return
		i=start
		while i<lenLines:
			if re.match(reg_title_head,lines[i]):
				name=re.sub(reg_title_head,"",lines[i]).rstrip()
				cols=[]
				childs=[]
				i+=1
				while i<lenLines and re.match(reg_col_head,lines[i]):
					col=re.sub(reg_col_head,"",lines[i]).rstrip()
					if col and col[0]==Category.TITLE_HEAD:
						data=list(Category.__read__(lines,i,depth=depth+1,direct=True,\
						title_head=Category.COL_HEAD+title_head,col_head=Category.COL_HEAD+col_head,lenLines=lenLines))
						if data:
							for end,c in data:
								childs.append(c)
								i=end
						else:
							i+=1

					else:
						if col:
							cols.append(col)
						i+=1
				#if cols or childs:
				yield (i,Category(name,cols,childs))
			elif direct:
				return
			else:
				i+=1
	@staticmethod
	def read(comment):
		return map(lambda res:res[1],Category.__read__(comment.split("\n")))
	@staticmethod
	def toTOT(fname):
#read csm.
#name is csm.memo.
#tags is cotegory col in csm.comment.
		csm=__data__.CSM.read(fname)
		if __data__.TOT.isTOT(csm):
			return __data__.TOT.toTOT(csm)
		cols=[]
		for c in Category.read(csm.comment):
			for c__ in c.getRec():
				cols.extend(map(lambda col:Category.clean_as_tag(col),c__.cols))
		return __data__.TOT.make2(Category.clean_as_tag(csm.memo),cols)
	@staticmethod
	def __toTOT2__(category,parent_tag=""):
#name is parent_tag&&:category.title
#tags is cols
		name=Category.ATTR_FORMAT.format(parent_tag,Category.clean_as_tag(category.title))
		yield __data__.TOT.make2(name,map(lambda col:Category.clean_as_tag(col),category.cols))
		for child in category.childs:
			for tot in Category.__toTOT2__(child,name):
				yield tot
	@staticmethod
	def toTOT2(csm):
#read csm.
#name is csm.memo&&:category title
#tags is cotegory col in category.
		if __data__.TOT.isTOT(csm):
			yield __data__.TOT.toTOT(csm)
			return
		try:
			for c in Category.read(csm.comment):
				for tot in Category.__toTOT2__(c,csm.memo):
					yield tot
		except StopIteration as e:
			print(e)
	@staticmethod
	def toTOT3(csm):
#getRec by csm.category in csm.comment yield as tot.
		if __data__.TOT.isTOT(csm):
			yield __data__.TOT.toTOT(csm)
			return
		for c in Category.read(csm.comment):
			for c__ in c.getRec():
				childs=(*c__.cols,*map(lambda child:child.title,c__.childs))
				yield __data__.TOT.make2(c__.title,childs)


class CategoryTree:
	DEFAULT_TOP="CATEGORY_TREE"
	def __init__(self,head=Category(),index={}):
		self.head=head
		self.index=index
	def __str__(self):
		return str(self.head)
	def get(self,title):
		return self.index.get(title,[])
	def searchTitle(self,s):
		regS=re.compile(s)
		return filter(lambda index:re.search(regS,index),self.index)
	def search(self,title=""):
		for title__ in self.searchTitle(title):
			for c in self.get(title__):
				yield c
	def __searchRec__(self,titles=[]):
#titles[0]=>titles[1]=>...
		if not titles:
			yield self.head
			return
			#for c in self.head.getRec():
			#	yield c
		curtitle=titles[0]
		titles=titles[1:] if len(titles)>1 else []
		for child in self.search(curtitle):
			for c in CategoryTree.make(child).__searchRec__(titles):
				yield c
	def searchRec(self,titles=[]):
		for c in self.__searchRec__(titles):
			for c__ in c.getRec():
				yield c__
	def get_cols(self,title=""):
		for c in self.search(title):
			for col in c.get_cols():
				yield col
	def append(self,category,titles=[]):
		ct=CategoryTree.make(category)
		appended=False
		for c in list(self.__searchRec__(titles)):
			c.childs.append(category)
			appended=True
		if appended:
			self.index=self.add_index(self.index,ct.index)
		return appended
	def appendRoot(self,root,titles=[]):
#root is list
		if not root:
			return False
		def make_rootHead(root_):
			if not root_:
				return None
			head=Category(root_[0])
			if len(root_) < 2:
				return head
			loop=head
			for title in root_[1:]:
				c=Category(title)
				loop.childs.append(c)
				loop=c
			return head
		root_head=Category(root[0])
		lenRoot=len(root)
		for i in range(lenRoot):
			i=lenRoot-1-i
			if list(self.searchRec(root[:i])):
				#print("appendRoot",{"titles":titles,"root":root,"make_rootHead":make_rootHead(root[i:]).title})
				return self.append(make_rootHead(root[i:]),root[:i])
	@staticmethod
	def make(head):
		index={}
		for c in head.getRec():
			if not index.get(c.title):
				index[c.title]=[]
			index[c.title].append(c)
		return CategoryTree(head,index)
	@staticmethod
	def make2(childs,top_title=None):
		if not top_title:
			top_title=CategoryTree.DEFAULT_TOP
		index={}
		for category in childs:
			for c in category.getRec():
				if not index.get(c.title):
					index[c.title]=[]
				index[c.title].append(c)
		head=Category(top_title,childs=childs)
		if not index.get(top_title):
			index[top_title]=[]
		index[top_title].append(head)
		return CategoryTree(head,index)
	@staticmethod
	def read(s):
		for head in Category.read(s):
			yield CategoryTree.make(head)
	@staticmethod
	def readAsOne(s,top_title=None):
		if not top_title:
			top_title=CategoryTree.DEFAULT_TOP
		index={}
		childs=[]
		for ct in CategoryTree.read(s):
			childs.append(ct.head)
			CategoryTree.__add_index__(index,ct.index)
		head=Category(top_title,childs=childs)
		return CategoryTree(head,index)
	@staticmethod
	def readCSM(csm):
		return CategoryTree.readAsOne(csm.comment,csm.memo)		
	@staticmethod
	def __add_index__(index1,index2):
		for key in index2:
			if not index1.get(key):
				index1[key]=index2[key]
			else:
				index1[key].extend(index2[key])
		return index1
	@staticmethod
	def add_index(index1,index2):
		index1=copy.copy(index1)
		return CategoryTree.__add_index__(index1,index2)

CT=CategoryTree

def culcSecond(s):
#d-h-m => n
#1-12-30 =>17360
	s=list(map(int,s.split("-")))
	lenS=len(s)
	res=0
	if lenS>0:
		res+=s[0]*60*60*24
	if lenS>1:
		res+=s[1]*60*60
	if lenS>2:
		res+=s[2]*60
	return res

def __to_datetime__(s):
	now=datetime.datetime.now()
	now=[now.year,now.month,now.hour]
	data=s.split(" ",1)
	s=data[0]
	data=data[1] if len(data) == 2 else ""
	n=list(map(int,s.split("-")))
	if not n or len(n)>3:
		return datetime.datetime(1,1,1)
	try:
		return (datetime.datetime(*now[:3-len(n)],*n),data)
	except:
		return (datetime.datetime(1,1,1),"")
def to_datetime(s):
	date,data=__to_datetime__(s)
	if not data:
		return date
	data=data.split(".",1)[0]
	n=list(map(int,data.split(":")))
	n=n+[1]*(3-len(n))
	return datetime.datetime(date.year,date.month,date.day,*n)


class Expander:
#expand csm as index.
	SEQ=":"
	TAG="EXPANDED"
	EXPAND_TITLE_F="*** {0} ***"
	EXPAND_HEAD="~~"
	def __init__(self,homeDB,default_dbid=""):
		self.homeDB=homeDB
		self.default_dbid=default_dbid.upper()
	def split(self,col):
		if self.SEQ in col:
			dbid,memo=col.rstrip().split(self.SEQ,1)
			dbid=dbid.upper()
		else:
			dbid=self.default_dbid
			memo=col.rstrip()
		return (dbid,memo)
	def __getCSMs__(self,dbid,memo):
		db=self.homeDB.select(dbid.upper())
		if not db:
			return None
		return __data__.CSM.make(db.text,db.search("^"+memo))
	def getCSMs(self,col):
		return self.__getCSMs__(*self.split(col))
	@staticmethod
	def getCols(csm):
		ct=util.CT.readAsOne("*"+csm.memo+"\n"+csm.comment)
		return ct.head.get_cols()
	def expand(self,csm):
		if self.TAG in csm.tags:
			return csm
		comment=""
		for line in csm.comment.split("\n"):
			if len(line)>2 and line[:2]==self.EXPAND_HEAD:
				col=line[2:]
				dbid,memo=self.split(col)
				if memo==csm.memo: #don't loop recursive
					continue
				csms=list(self.__getCSMs__(dbid,memo))
				if not csms:	#expand by default_dbid if card don't be found.
					csms=self.__getCSMs__(self.default_dbid,memo)
				for csm__ in csms:
					comment+=self.EXPAND_TITLE_F.format(csm__.memo)+"\n-\n"
					comment+=csm__.dump("CT").replace("\n\n","\n-\n")+"\n"
					comment+="-"*40+"\n"
					comment=comment.replace("\n\n","\n-\n") #for comment or tags is "".
			else:
				comment+=line+"\n"
		return __data__.CSM(csm.memo,comment.rstrip(),(*csm.tags,self.TAG),csm.date)



def isroman(c):
	return "A" <= c <= "Z" or "a" <= c <= "z"
	#n=ord(c)
	#return 65<=n<=90 or 97<=n<=122	#"AA" "<= c <= "Z"

def tolowUp(s):
	return "".join(map(lambda c:"["+c.lower()+c.upper()+"]" if isroman(c) else c,s))

def addMemo(base,s):
	return "({0})|({1})".format(base,s) if base else s

def reduce(func,data,default=None):
	data=list(data)
	if not data:
		return default
	if len(data) == 1:
		return data[0]
	return functools.reduce(func,data)

def arg_replace(args,from_="/",to="-"):
	for arg in args:
		n=re.match(f"{from_}+",arg)
		n=len(n.group()) if n else 0
		yield re.sub(from_*n,to*n,arg)

def partitionArgs(l,cutunders=[],cutunderskw=[]):
	for i,arg in enumerate(l):
		if arg in cutunders:
			if i+1 == len(l):
				return (l[:i],arg,[])
			return (l[:i],arg,l[i+1:])
		elif arg in cutunderskw:
			if i+2 >= len(l):
				return (l[:i],arg,[])
			return (l[:i],arg,l[i+2:])
	return (l,None,[])

class TMPF:
	def __init__(self,mode="w",encoding="utf8",trush=False):
		self.fname="a.txt"
		self.mode=mode
		while os.path.exists(self.fname):
			self.fname=str(random.randint(10**24,10**36))+".txt"
		self.fname=_util.realpath(self.fname)
		self.f=open(self.fname,mode=mode,encoding=encoding)
		self.removefunc=winshell.delete_file if trush else os.remove
	def __getattr__(self,attr):
		return getattr(self.f,attr)
	def __enter__(self):
		return self
	def __exit__(self,*args,**kwargs):
		self.close()
	def close(self):
		self.f.close()
		self.removefunc(self.fname)
class Docs:
	class Category:
		APPEND="""
		Usage:
			append [(-t <tags>)] [(-m <memo>)] <srcid> <dstid> 
		"""
	class CSM:
		REMOVE="""
		Usage:
			remove <dbid>
		"""
	COPY="""
	Usage:
		copy home (-d <dname>)
		copy db <dbid> (-d <dname>)
		copy <srcid> <dstid> [(-O|--override)]
	"""
	APPEND="""
	Usage:
		append tag db [(-D <dbid>)] [(-t <tags>)] <tagsToAppend>...
		append tag csm [(-D <dbid>)] [(-t <tags>)] <tagsToAppend>...
		append db data <dbid> (-d <dname>)
		append db <srcid> <dstid> [(-u <userid>)]
		append home data (-d <dname>) [(--dt <dbTags>)]
		append home [(-d <dname>)] [(-T <tagfile>)]
		append csm <srcid> <dstid> [(-t <tags>)] [(-m <memo>)] [(-O|--override)]
		append tot <srcid> <dstid> [(-t <tag>)] [(-O|--override)]
	"""
	DUMP="""
	Usage:
		dump tag <dbid> [(-f <fname>)]
		dump home [(-d <dname>)]
		dump <dbid> [(-t <tags>)] [(-m <memo>)] [(-d <dname>)]
	"""
	BACKUP="""
	Usage:
		backup home [(-d <dname>)]
		backup <dbid> [(-f <format>)]
	"""
	RENAME="""
	Usage:
		rename <srcid> <dstid>
	"""
	NUMBER="""
	Usage:
		number <dbid> [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)]
		number sum <dbid> [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)]
	"""
	REMOVE="""
	Usage:
		remove tag db [(-t <tags>)] [(-D <dbid>)] <tagsToRemove>...
		remove (f|file) <fname>
	"""
	VIM="""
	Usage:
		vim [(-m <memo>)] [(-d <dname>)] [(-r|--random)]
	"""

class Command(_util.Command):
	CATEGORY=("CA","CATEGORY")
	APPEND=("A","APPEND")
	COPY=("CP","COPY")
	DUMP=("D","DUMP")
	BACKUP=("BU","BACKUP")
	RENAME=["RENAME"]
	NUMBER=("N","NUMBER")
	VIM=["VIM"]

HELP="""
	$ category append
	$ append
	$ backup
	$ dump
	$ rename
	$ csm remove
	$ number
	$ remove
"""




class AuHSShell(__shell__.BaseShell3):
	def __init__(self,home):
		self.shell=Shell(home.home)
		super().__init__()
	def execQuery(self,query,output):
		return self.shell.execQuery(query,output)
	def start(self):
		self.shell.start()
	def close(self):
		super().close()
		self.shell.close()
class Shell(__shell__.BaseShell3):
	DNAME="_util"
	PROMPT=">>"
	VIM_MAX=50
	def __init__(self,homeDB):
		self.homeDB=homeDB
		dname=os.path.join(homeDB.dname,self.DNAME)
		super().__init__(dname=dname,prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in _util.Command.HELP:
			output.write(HELP+"\n")
		elif query.command in Command.CATEGORY:
			if not query.args:
				return
			query=__shell__.Query(query.args)
			if query.command in Command.APPEND:
				try:
					args=docopt.docopt(Docs.Category.APPEND,query.args)
				except SystemExit as e:
					print(e)
					return
				srcid=args["<srcid>"].upper()
				dstid=args["<dstid>"].upper()
				srcDB=self.homeDB.select(srcid)
				if not srcDB:
					print("Don't find {0}.".format(srcid))
					return
				dstDB=self.homeDB.select(dstid)
				if not dstDB:
					self.homeDB.append(dstid,["CATEGORY"])
					dstDB=self.homeDB.select(dstid)
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				memo=args["<memo>"] if args["-m"] else ""
				for csm in __data__.CSM.make(srcDB.text,srcDB.search(memo,tags)):
					for tot in Category.toTOT2(csm):
						dstDB.appendTOT(tot.name,tot.childs)
						print("Append {0} to {1}.".format(tot.name,dstid))
				dstDB.save()
		elif query.command in _util.Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["data"]:
				if args["db"]:
					dbid=args["<dbid>"].upper()
					db=self.homeDB.select(dbid)
					if not db:
						self.homeDB.append(dbid,["UTIL","DATA"])
						db=self.homeDB.select(dbid)
					dname=_util.realpath(args["<dname>"])
					data_db=__db__.TagDB(dname)
					db.appendDB(data_db)
					db.save()
				elif args["home"]:
					dname=_util.realpath(args["<dname>"])
					dbTags=args["<dbTags>"] if args["--dt"] else []
					homeDB=__db__.HomeTagDB(dname)
					for card in homeDB.search(tags=dbTags):
						dbid=card.getID(homeDB.text).upper()
						if self.homeDB.select(dbid):
							output.write("{0} already exists.\n".format(dbid.lower()))
							continue
						src_dname=os.path.join(homeDB.dname,dbid)
						dst_dname=os.path.join(self.homeDB.dname,dbid)
						try:
							shutil.copytree(src_dname,dst_dname)
						except:
							continue
						tags=list(map(lambda tagIdx:tagIdx.get(homeDB.text),homeDB.cardToTags.get(card.id,[])))
						tags.append("DATA")
						self.homeDB.append(dbid,tags)

			elif args["tag"]:
				tagsToAppend=list(map(lambda tag:tag.upper(),args["<tagsToAppend>"]))
				if args["db"]:
					dbid=args["<dbid>"].upper() if args["-D"] else ".*"
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					for card in list(self.homeDB.search(dbid,tags)):
						print(card.getID(self.homeDB.text))
						if self.homeDB.appendTags(card.id,tagsToAppend):
							output.write("Appended"+str(tagsToAppend)+" To "+card.getID(self.homeDB.text)+"\n")
						else:
							output.write("Append Failed.")
				elif args["csm"]:
					dbid=args["<dbid>"].upper() if args["-D"] else ".*"
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					for card in list(self.homeDB.search(dbid,tags)):
						dbid__=card.getID(self.homeDB.text)
						db=self.homeDB.select(dbid__)
						if not db:
							continue
						for card in db.cards.values():
							db.appendTags(card.id,tagsToAppend)
						output.write("Appended"+str(tagsToAppend)+" To "+dbid__+"\n")
						db.save()
				self.homeDB.save()
			elif args["db"]:
				dstid=args["<dstid>"].upper()
				dst=self.homeDB.select(dstid)
				i=0
				if not dst:
					self.homeDB.append(dstid,["UTIL"])
					dst=self.homeDB.select(dstid)
				if args["-u"]:
					host=__server__.getHost(args["<userid>"])
					if not host:
						print("Don't find host of",args["<userid>"],".")
						return
					with __server__.Client(host) as c:
						c.connect(args["<srcid>"])
						if not c.connected:
							print("Can't connect",args["<srcid>"],".")
						for csm in c.search():
							dst.appendCSM(csm)
						for tot in c.getTOTs(""):
							dst.appendTOT(tot.name,tot.childs)
					print("Append",args["<srcid>"],"to",args["<dstid>"])
				else:
					srcid=args["<srcid>"].upper()
					src=self.homeDB.select(srcid)
					if not src:
						print("Don't find",srcid)
						return
					src_tags=list(map(lambda tagIdx:tagIdx.get(self.homeDB.text),self.homeDB.cardToTags.get(self.homeDB.find(srcid),[])))
					#self.homeDB.appendTags(self.homeDB.find(dstid),src_tags)
					dst.appendDB(src)
					output.write("Append {0} to {1}.\n".format(args["<srcid>"],args["<dstid>"]))
					dst.save()
			elif args["home"]:
				try:
					dname=args["<dname>"] if args["-d"] else DEFAULT_DUMP_HOME_DIR
					srcHome=Data.Home(dname)
					tagfile=args["<tagfile>"] if args["-T"] else os.path.join(dname,Data.Home.DB_TAG_FILE)
					tagfile=_util.realpath(tagfile)
					tag_data={}
					if os.path.exists(tagfile):
						with open(tagfile,"r") as f:
							for line in f:
								dbid,tags=line.strip().split(";",1)
								tag_data[dbid.upper()]=tags.split(",")
					for src in srcHome.dumpDB():
						if self.homeDB.select(src.id):
							print(src.id,"already exists.")
						self.homeDB.append(src.id,tag_data.get(src.id,[]))
						dst=self.homeDB.select(src.id)
						for csm in src.csms:
							dst.appendCSM(csm)
						for tot in src.tots:
							dst.appendTOT(tot.name,tot.childs)
						dst.save()
				except Exception as e:
					print(e)
			elif args["csm"] or args["tot"]:
				srcid=args["<srcid>"]
				dstid=args["<dstid>"]
				override=args["-O"] or args["--override"]
				src=self.homeDB.select(srcid)
				if not src:
					output.write("Don't find "+srcid+"\n")
					return
				dst=self.homeDB.select(dstid)
				if not dst:
					self.homeDB.append(dstid,["util"])
					dst=self.homeDB.select(dstid)
				if args["csm"]:
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					memo=args["<memo>"] if args["-m"] else ""
					data=""
					for csm in __data__.CSM.make(src.text,src.search(memo,tags)):
						dst.appendCSM(csm,override)
						#data+="Append {0} to {1}.\n".format(csm.memo,dstid.lower())
					#output.write(data)
					output.write("Appended.\n")
				elif args["tot"]:
					tag=args["<tag>"].upper() if args["-t"] else ""
					data=""
					for tot in __data__.TOT.make(src.text,src.searchTOT(tag)):
						dst.appendTOT(tot.name,tot.childs,override)
						data+="Append {0} to {1}.\n".format(tot.name,dstid.lower())
					output.write(data)
				dst.save()
		elif query.command in Command.BACKUP:
			try:
				args=docopt.docopt(Docs.BACKUP,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["home"]:
				dname=args["<dname>"] or DEFAULT_BACKUP_HOME_DIR
				dname=_util.realpath(dname)
				if os.path.exists(dname):
					shutil.rmtree(dname)
				self.execQuery(__shell__.Query.read("copy home -d {0}".format(dname)),output)
			else:
				dbids=__db__.getDBIDs(self.homeDB,args["<dbid>"].upper())
				dbids=list(dbids)
				if not dbids:
					return
				format_=args["<format>"] if args["-f"] else "__{0}.BACKUP"
				buIdx=self.homeDB.find(BACKUP)
				for dbid in list(dbids):
					if buIdx in self.homeDB.cardToTags.get(self.homeDB.find(dbid),[]):
						continue
					dstid=format_.format(dbid).upper()
					if self.homeDB.select(dstid):
						try:
							self.homeDB.remove(dstid)
						except Exception as e:
							print("E",e)
					try:
						self.execQuery(__shell__.Query(("copy",dbid,dstid)),self.null)
						self.execQuery(__shell__.Query(("append","tag","db","-D",dstid,"BACKUP")),self.null)
						output.write("Backup {0} to {1}\n".format(dbid.lower(),dstid.lower()))
					except Exception as e:
						print(e)
		elif query.command in Command.DUMP:
			try:
				args=docopt.docopt(Docs.DUMP,query.args)
			except Exception as e:
				print(e)
			except SystemExit as e:
				print(e)
				return
			if args["home"]:
				dname=args["<dname>"] if args["-d"] else DEFAULT_DUMP_HOME_DIR
				dname=_util.realpath(dname)
				if Data.Home.make(self.homeDB.dname,dname):
					print("Dump to",dname)
				else:
					print(dname,"already exists.")
					return
			elif args["tag"]:
				dbid=args["<dbid>"] 
				fname=_util.realpath(args["<fname>"]) if args["-f"] else DEFAULT_DUMP_TAG_FNAME
				#if not os.path.exists(fname):
				#	output.write("Don't find {0}.\n".format(fname))
				comment=""
				for dbid in __db__.getDBIDs(self.homeDB,dbid):
					db=self.homeDB.select(dbid)
					category=Category(dbid,db.getTags(),Category.make_from_db(db))
					comment+=str(category)+"\n"
				csm=__data__.CSM("DUMPED_TAG",comment.rstrip())
				with open(fname,"w") as f:
					f.write(str(csm))
				print("write to {0}".format(fname))
			else:
				dbid=args["<dbid>"]
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				memo=args["<memo>"] if args["-m"] else ""
				dname=args["<dname>"] if args["-d"] else DEFAULT_DUMP_CSM_DIR_F
				dname=_util.realpath(dname)
				if memo or tags:
					if not os.path.exists(dname):
						os.makedirs(dname)
					for dbid in self.homeDB.getDBIDs(dbid):
						db=self.homeDB.select(dbid)
						for csm in __data__.CSM.make(db.text,db.search(memo,tags)):
							csm.write(os.path.join(dname,csm.fname))
				else:
					__shell__.CSMShell(db).execQuery(__shell__.Query(("WRITE","-d",dname)),output)
		elif query.command in Command.RENAME:
			try:
				args=docopt.docopt(Docs.RENAME,query.args)
			except SystemExit as e:
				print(e)
				return
			srcid=args["<srcid>"].upper()
			dstid=args["<dstid>"].upper()
			src_path=os.path.join(self.homeDB.dname,srcid)
			dst_path=os.path.join(self.homeDB.dname,dstid)
			tags=list(map(lambda tagIdx:tagIdx.get(self.homeDB.text),self.homeDB.cardToTags.get(self.homeDB.find(srcid),[])))
			os.rename(src_path,dst_path)
			self.homeDB.remove(srcid)
			self.homeDB.append(dstid,tags)
			output.write("Rename {0} to {1}\n".format(srcid,dstid))
		elif  query.command in Command.CSM:
			query=__shell__.Query(query.args)
			if query.command in Command.REMOVE:
				try:
					args=docopt.docopt(Docs.CSM.REMOVE,query.args)
				except SystemExit as e:
					print(e)
					return
				dbid=args["<dbid>"]
				for dbid__ in self.homeDB.getDBIDs(dbid):
					csm_dname=DEFAULT_CSM_DIR_F(os.path.join(self.homeDB.dname,dbid__))
					if os.path.exists(csm_dname):
						winshell.delete_file(csm_dname)
						output.write("Removed {0}.\n".format(csm_dname))
		elif query.command in Command.NUMBER:
			try:
				args=docopt.docopt(Docs.NUMBER,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"].upper()
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			memo=args["<memo>"] if args["-m"] else ""
			from_=args["<from>"] if args["-F"] else "1900-1-1"
			until=args["<until>"] if args["-U"] else "2200-1-1"
			from_=util.to_datetime(from_)
			until=util.to_datetime(until)
			text=""
			data=[]
			def count():
				for dbid__ in self.homeDB.getDBIDs(dbid):
					if dbid__.find("__")==0:
						continue
					db=self.homeDB.select(dbid__.upper())
					if not db:
						continue
					#output.write("Dont find {0}.\n".format(dbid.lower()))
					#return
					cards=db.search(memo,tags)
					cards=filter(lambda card:from_<=util.to_datetime(card.date)<until,cards)
					n=len(list(cards))
					yield (dbid__,n)
					#data.append((dbid__.lower(),n))
			if args["sum"]:
				n=sum(map(lambda data:data[1],count()))
				print(n,file=output)
			else:
				for dbid__,n in count():
					output.write("{0} ; {1}\n".format(dbid__.lower(),n))
				#for dbid__,n in sorted(data,key=lambda d:d[1]):
				#	text+="{0} : {1}\n".format(dbid__.lower(),n)
				#output.write(text)
		elif query.command in Command.REMOVE:
			try:
				args=docopt.docopt(Docs.REMOVE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["tag"]:
				dbid=args["<dbid>"].upper() if args["-D"] else ".*"
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				tagsToRemove=args["<tagsToRemove>"]
				cards=list(self.homeDB.search(dbid,tags))
				ids=list(map(lambda card:card.getID(self.homeDB.text),cards))
				self.homeDB.__removeTags__(map(lambda card:card.id,cards),tagsToRemove)
				for dbid__ in ids:
					output.write("Remove {0} from {1}\n".format(str(tagsToRemove),dbid__))
			elif args["f"] or args["file"]:
				fname=_util.realpath(args["<fname>"])
				if not os.path.exists(fname):
					return
				shutil.rmtree(fname)
				output.write("Removed {0}\n".format(fname))
				
		elif query.command in Command.COPY:
			try:
				args=docopt.docopt(Docs.COPY,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["db"]:
				dbid=args["<dbid>"].upper()
				if not self.homeDB.select(dbid):
					output.write("{0} doesn't exists.\n".format(dbid.lower()))
					return
				dname=_util.realpath(args["<dname>"])
				db_dname=os.path.join(self.homeDB.dname,dbid)
				try:
					shutil.copytree(db_dname,dname)
				except Exception as e:
					output.write(str(e))
					return
			elif args["home"]:
				dname=_util.realpath(args["<dname>"])
				try:
					shutil.copytree(self.homeDB.dname,dname)
				except Exception as e:
					output.write(str(e))
					return
			else:
				srcid=args["<srcid>"].upper()
				dstid=args["<dstid>"].upper()
				override=args["-O"] or args["--override"]
				if not self.homeDB.select(srcid):
					output.write("Don't find {0}\n".format(srcid.lower()))
					return
				if self.homeDB.select(dstid):
					if override:
						self.homeDB.remove(dstid)
					else:
						output.write("{0} already exists.\n".format(dstid.lower()))
						return
				src_dname=os.path.join(self.homeDB.dname,srcid)
				dst_dname=os.path.join(self.homeDB.dname,dstid)
				try:
					shutil.copytree(src_dname,dst_dname)
				except Exception as e:
					print("XXX",e)
					return
				tags=map(lambda tagIdx:tagIdx.get(self.homeDB.text),self.homeDB.cardToTags.get(self.homeDB.find(srcid),[]))
				self.homeDB.append(dstid,tags)
				output.write("Copy {0} to {1}\n".format(srcid.lower(),dstid.lower()))
		elif query.command in Command.VIM:
			try:
				args=docopt.docopt(Docs.VIM,query.args)
			except SystemExit as e:
				print(e)
				return
			dname=args["<dname>"] if args["-d"] else __shell__.DEFAULT_CSM_DIR
			dname=_util.realpath(dname)
			memo=args["<memo>"] if args["-m"] else ""
			def getfnames():
				for fname in os.listdir(dname):
					if not re.search("\.csm$",fname):
						continue
					fname=os.path.join(dname,fname)
					csm=__data__.CSM.read(fname)
					if not memo or re.search(memo,csm.memo):
						yield fname
			fnames=list(getfnames())
			if args["-r"] or args["--random"]:
				random.shuffle(fnames)
			if len(fnames) > self.VIM_MAX:
				fnames=fnames[:self.VIM_MAX]
			sp.call(["vim",*fnames])

					
		else:
			return super().execQuery(query,output)

	def start(self):
		self.stdout.write("*** welcome to shell for util! ***\n")
		return super().start()



