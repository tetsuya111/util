import subprocess as sp
import re
import os
from hashlib import *
import selectors
import threading
from socketserver import *
import socket
import queue
import time
import sys
import base64
import zlib
import _pyio

RECV_MAX_BYTES=1024*1024	#1MB

HASH_N=128

def hash(s):
	#s=base64.b64encode(s.encode()).decode().replace("/","_")
	return zlib.adler32(s.encode())

def inputUntilSeq(text="",seq="",output=sys.stdout):
	while True:
		output.write(text)
		s=input()
		if s == seq:
			break
		yield s

def _realpath(fname):
	return os.path.abspath( os.path.expanduser(os.path.expandvars(fname)))
def realpath(fname):	#expand vars of environ that you set may include vars of envrion.then you should expand twice.
	return _realpath(os.path.expandvars(fname))
	

def find(l,n,start,end):
	i=start
	while i<end and l[i]!=n:
		i+=1
	if i==end:
		return -1
	return i

def subQuote(s):
	if len(s)<2:
		return s
	if s[0]==s[-1] and s[0] in ("\"","\'"):
		return s[1:-1]
	return s

def subQuotes(data):
	return list(map(lambda s:subQuote(s),data))

def __recv2(res,socket,endEvent,maxBytes=RECV_MAX_BYTES):	
#recv for threading.
#res is queue.
#if endEvent is setted before recv data,return none.
	data=bytes()
	poll_interval=0.5
	with selectors.SelectSelector() as selector:
		selector.register(socket,selectors.EVENT_READ)
		while True:
			if endEvent.is_set():
				return
			ready = selector.select(poll_interval)
			if ready:
				res.put(recvall(socket,maxBytes))
				return

def recv2(socket,maxBytes=RECV_MAX_BYTES):
	res=queue.Queue()
	endEvent=threading.Event()
	t=threading.Thread(target=__recv2,args=(res,socket,endEvent,maxBytes))
	t.start()
	return (res,endEvent)

def recv3(socket,maxBytes=RECV_MAX_BYTES):	#res data if recved ,res None if socket is closed
	res,endRecv=recv2(socket)
	while True:
		if socket._closed:
			endRecv.set()
			return bytes()
		if not res.empty():
			endRecv.set()
			return res.get()

def recvForServer(socket,server,tv=0.5,maxBytes=RECV_MAX_BYTES):	#return if socket is closed or server is closed,else recv data.
	res,endRecv=recv2(socket,maxBytes)
	data=None
	while True:
		time.sleep(tv)
		if socket._closed or not server.opened:
			endRecv.set()
			return bytes()
		if not res.empty():
			endRecv.set()
			data=res.get()
			return data

def recvall(socket,blocked=False,timeout=10,maxBytes=RECV_MAX_BYTES):	
#if blocked is True,blocking once
#timeout : block time
	data=bytes()
	poll_interval=0.5
	with selectors.SelectSelector() as selector:
		selector.register(socket,selectors.EVENT_READ)
		while True:
			if blocked:
				limitTime=time.time()+timeout
				while not selector.select(poll_interval):
					if time.time()>=limitTime:
						blocked=False
						break
				blocked=False
			ready = selector.select(poll_interval)
			if not ready:
				    return data
			newData=socket.recv(4096)
			data+=newData
			if not newData:	#recved data is None
				return data
			if len(data)>maxBytes:
				return data
	return data

def is_rechar(c):
	return c != re.escape(c)


class Docs:
	class DB:
		HELP="""
# help
# ls
#
# select <dbid> [(-u <userid>)]
# server start <dbid>
# server stop <dbid>
#
# append <dbid> <tags>...
# remove <dbid>
# search [(-t <tags>)] [(-u <userid>)]
# tag tot
# tag <tag>
#
# csm write [(-d <dname>)]
# csm append [(-d <dname>)] [(-O|--override)]
# dns (on|off)
		"""
		HELP_COMMAND="""
		Usage:
			help [(-a|--all)] [(-c <command>)]
		"""
		LS="""
		Usage:
			ls
		"""
		SERVER="""
		Usage:
			server start <dbid>
			server stop <dbid>
			server
		"""
		SELECT="""
		Usage:
			select <dbid> [(-u <userid>)]
		"""
		SEARCH="""
		Usage:
			search [(-t <tags>)] [(-D <dbid>)] [(-u <userid>)] [(-a|--all)] [(-p <pMode>)]
		"""
	class Home:
		REMOVE="""
		Usage:
			remove [(-t <tags>)] [(-D <dbid>)]
			remove tot [(-t <tag>)]
		"""
	class CSM:
		WRITE="""
		Usage:
			write [(-d <dname>)]
			
		"""
		SEARCH="""
		Usage:
			search tot [(-t <tag>)] [(-d <dname>)]
			search  [(-t <tags>)] [(-m <memo>)] [(-d <dname>)]
		"""
		APPEND="""
		Usage:
			append [(-d <dname>)]  [(-O|--override)]
		"""
	class Wikipedia:
		APPEND="""
		Usage:
			append <dbid> <title>
	"""
	SEARCH="""
	Usage:
		search  [(-t <tags>)] [(-m <memo>)] [(-p <pMode>)] [-r|--random] [-o <output>]
	"""
	REMOVE="""
	Usage:
		remove tot [<tag>]
		remove [(-t <tags>)] [(-m <memo>)] 
	"""
	#tag (-T|--tot) [<tag>]
	LIST="""
	Usage:
		list tot [<tag>]
		list (t|tag) [<tag>]
	"""
	WRITE="""
	Usage:
		write tot
		write
	"""
	EXEC="""
	Usage:
		exec file <fname>
	"""
	MAP="""
	Usage:
		map stdin <query_f>
		map <query_f> <args>...
	"""
	XARGS="""
	Usage:
		xargs <args>...
	"""
	ALIAS="""
	Usage:
		alias <command> <query>...
		alias (rm|remove) <command>
	"""
	HELP="""
		id
		csm search [(-t <tags>)] [(-m <memo>)]  [(-d <dname>)]
		csm write [(-d <dname>)]
		csm append [(-d <dname>)]  [-O|--override]
		clean
		search  [(-t <tags>)] [(-m <memo>)] [(-p <pMode>)]
		list tot [<tag>]
		list (t|tag) [<tag>]
		write tot
		write
		remove tot [<tag>]
		remove [(-t <tags>)] [(-m <memo>)] 
	"""

class Command:
	class DB:
		SELECT=("SE","SELECT")
		LS=("L","LS")
		CONNECT=("CO","CONNECT")
		SERVER=("SER","SERVER")
		STOP=("STOP",)
		LOCK=("LO","LOCK")
	CREATE=["CREATE"]
	CSM=["CSM"]
	QUIT=("Q","QUIT","EXIT")
	HELP=("H","HELP")
	CLEAN=("CL","CLEAN")
	SEARCH=("S","SEARCH")
	SEARCH2=("SEARCH2",)
	REMOVE=("RM","REMOVE")
	LIST=("L","LS","LIST")
	TAG=("T","TAG")
	WRITE=("W","WRITE")
	APPEND=("A","APPEND")
	APPEND_TAG=("AT","APPENDTAG")
	TOT=("TOT",)
	CRAWL=("CR","CRAWL")
	DNS=["DNS"]
	COPY=("COPY","CP")
	ID=["ID"]
	EXEC=("EX","EXEC")
	MAP=["MAP"]
	XARGS=["XARGS"]
	SHELL=("SH","SHELL")
	ALIAS=("ALS","ALIAS")


class PMode:
	MEMO="M"
	COMMENT="C"
	TAG="T"
	DATE="D"


def subSpace(s):
	return re.sub("^[ \t]+|[\t ]+$","",s)
def touch(fname):
	with open(fname,"a") as f:
		pass

class Query:
	STR_SEQ=" "
	def __init__(self,data=[]):
		data=list(data)
		self.command=data[0].upper() if data else ""
		self.args=data[1:] if len(data)>1 else []
	def append(self,data):
		return self.args.append(data)
	def extend(self,data):
		return self.args.extend(data)
	@property
	def data(self):
		return (self.command.lower(),*self.args)
	def __bool__(self):
		return bool(self.command)
	def __str__(self):
		return self.STR_SEQ.join(map(lambda dat:f'"{dat}"',self.data))
	def __iter__(self):
		return iter(self.data)
	def __getitem__(self,key):
		if type(key) is slice:
			return Query(self.data[key])
		return self.data[key]
	def __copy__(self):
		return Query(self.data)
	def readable(self):
		return True
	def readline(self):
		return str(self)
	@staticmethod
	def read(line,seq=re.compile(" +")):
		data=Query.split(line.rstrip(),seq)
		return Query(subQuotes(data))
	@staticmethod
	def input(prompt=">>",seq=re.compile(" +")):
		line=input(prompt)
		return Query.read(line,seq)
	@staticmethod
	def __split__(line,seq=re.compile(" +")):
		lenLine=len(line)
		i=0
		data=""
		inQuote=False
		while i<lenLine:
			nowline=line[i:]
			match=re.match(seq,nowline)
			if match and not inQuote:
				if data:
					yield data
				data=""
				i+=match.end()
			elif nowline[0] == '"':
				if inQuote:
					yield data
					data=""
					i+=1
					inQuote=False
				else:
					if len(nowline) == 1:
						raise Exception("Nothing is left of \"\n")
					i+=1
					inQuote=True
			else:
				data+=line[i]
				i+=1
		if data:
			yield data
	@staticmethod
	def split(line,seq=re.compile(" +")):
		#data=list(Query.__split__(line,seq))
		#return data
		return list(Query.__split__(line,seq))

class BaseQueryStream:
	def __init__(self,shell,data=[],output=None):
		self.query=Query(data)
		self.shell=shell
		self.output=output or sys.stdout
	def write(self,s=None):
			self.shell._begin_one_liner(self.query,self.output)

class QueryStream(BaseQueryStream):
	def write(self,s):
		sio=_pyio.StringIO()
		sio.write(s)
		sio.seek(0,0)
		origin_stdin=sys.stdin
		sys.stdin=sio
		super().write(s)
		sys.stdin=origin_stdin
		
class QueryArgsStream(QueryStream):
#ex) shell echo -t how || s {0} {1}
	def write_oneliner(self,line):
		line=line.strip()
		if not line:
			return False
		input_q=Query.split(line)
		query_s=str(self.query).format(*input_q)
		myquery=self.query
		self.query=Query.read(query_s)
		BaseQueryStream.write(self)
		self.query=myquery
	def write(self,s):
		for line in s.strip().split("\n"):
			self.write_oneliner(line)
