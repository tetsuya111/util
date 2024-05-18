from socketserver import *
import socket
import selectors
import queue
import threading
import shutil
import os
import time
from functools import *
import datetime
import re
from . import __data__
from . import __index__
from . import _util
from . import __utils__
from . import __db__
import json
import random

def randomPort():
	return random.randint(1000,50000)

MAX_HANDLING=10

class BaseServer2(BaseServer):	#if have surve_forever2
	MAX_HANDLING=MAX_HANDLING
	def __init__(self, server_address, RequestHandlerClass):
		super().__init__(server_address,RequestHandlerClass)
		self.endServer=threading.Event()
		self.t=None
		self.handling=queue.Queue()
	@property
	def host(self):
		return self.server_address[0]
	@property
	def port(self):
		return self.server_address[1]
	def serve_forever2(self,event,timeout=1,max_=MAX_HANDLING):
		"""
		like serve_forever
		It end,If you set event gived args.
		If this get request,begin new thread and append to self.handling.

		max_ is max number of thread.
		"""
		with selectors.SelectSelector() as selector:
			selector.register(self.socket, selectors.EVENT_READ)
			while True:
				if event.is_set():
					return
				ready = selector.select(timeout)
				if ready:
					#for t in list(filter(lambda t:t.is_alive(),self.handling)):
					#	handling
					self.cleanHandling()
					if self.handling.qsize()<max_:
						t=threading.Thread(target=self._handle_request_noblock)
						t.start()
						self.handling.put(t)
	@property
	def opened(self):
		return self.t and self.t.is_alive()
	def __call__(self):
		return self.open()
	def open(self,max_=MAX_HANDLING):
#Open if self is closed.
		if not self.opened:
			try:
				self.endServer.clear()
				self.t=threading.Thread(target=self.serve_forever2,args=[self.endServer,max_])
				self.t.start()
			except Exception as e:
				print(e)
				return None
		return self.endServer
	def stop(self):
		if self.opened:
			self.endServer.set()
	def close(self):
		if self.opened:
			self.endServer.set()
		self.socket.close()
	def cleanHandling(self):
		cleanedHandling=queue.Queue()
		while not self.handling.empty():
			t=self.handling.get()
			if t.is_alive():
				cleanedHandling.put(t)
		self.handling=cleanedHandling
	def __enter__(self):
		return self
	def __exit__(self,*args):
		self.close()
		return self

class TCPServer2(BaseServer2):
#Diffrence between TCPServer and this is Base Class only.

	address_family = socket.AF_INET
	socket_type = socket.SOCK_STREAM
	request_queue_size = 5
	allow_reuse_address = False

	def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
		"""Constructor.  May be extended, do not override."""
		super().__init__(server_address, RequestHandlerClass)
		self.socket = socket.socket(self.address_family,self.socket_type)
		if bind_and_activate:
			try:
				self.server_bind()
				self.server_activate()
			except:
				self.server_close()
				raise

	def server_bind(self):
		if self.allow_reuse_address:
			self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.socket.bind(self.server_address)
		self.server_address = self.socket.getsockname()

	def server_activate(self):
		self.socket.listen(self.request_queue_size)

	def server_close(self):
		self.socket.close()

	def fileno(self):
		return self.socket.fileno()

	def get_request(self):
		return self.socket.accept()

	def shutdown_request(self, request):
		try:
#explicitly shutdown.  socket.close() merely releases
#the socket and waits for GC to perform the actual close.
			request.shutdown(socket.SHUT_WR)
		except OSError:
			pass #some platforms may raise ENOTCONN here
		self.close_request(request)

	def close_request(self, request):
		request.close()

class ThreadingTCPServer2(ThreadingMixIn,TCPServer2): pass


class BaseDBServer(ThreadingTCPServer2):
#BaseDBServer has users this server accept.
	USER_FILE="user.txt"
	SERVER_CONF="server.conf"
	LOG_FILE="server.log"
	DEFAULT_CONNECTION_LIMIT=5
	def __init__(self,dname,server_addr,HandlerClass):
		try:
			super().__init__(server_addr,HandlerClass)
			self.worked=True
		except:
			self.worked=False
		self.server_addr=server_addr
		self.__dname=dname
		confFile=os.path.join(dname,self.SERVER_CONF)
		__utils__.touch(confFile)
		conf=self.readConf(confFile)
		self.__users=self.readUsers(conf)
		self.limit=conf["limit"] if conf.get("limit",-1)!=-1 else self.DEFAULT_CONNECTION_LIMIT
		self.logFile=os.path.join(dname,self.LOG_FILE)
		__utils__.touch(self.logFile)
		self.log_data=self.Log.read(self.logFile)
	def serve_forever2(self,event,timeout=1):
		if not self.worked:
			event.set()
			return False
		return super().serve_forever2(event,timeout,max_=self.limit)
	def log(self,text):
		with self.mutex:
			with open(self.logFile,"a") as f:
				f.write(text+"\n")
	def log_connection(self,host,data):	#data is dict.
		data["host"]=host
		data["date"]=str(datetime.datetime.now())
		self.log(json.dumps(data))
		self.log_data.append(host,data)
	@property
	def READ(self):
		return self.Users.READ
	@property
	def WRITE(self):
		return self.Users.WRITE
	@property
	def users(self):
		return self.__users
	@property
	def host(self):
		return self.server_addr[0]
	@property
	def port(self):
		return self.server_addr[1]
	def verify_request(self,request,client_address):
		client_host=client_address[0]
		userid=getID(client_host)
		return userid and (self.checkUser(self.READ,userid) or self.checkUser(self.WRITE,userid)) and not self.blocked(userid)
	def blocked(self,userid):
		return False

	class Users(__data__.Logic.Data):
		READ="R"
		WRITE="W"
		DENY="-"
		def __init__(self,data=[],not_=False,mode="r"):
			super().__init__(data,not_)
			self.mode=mode.lower()
		def contain(self,data):
			if self.not_:
				return data not in self.data
			return data in self.data
		@property
		def readable(self):
			self.READ in self.mode
		@property
		def writable(self):
			self.WRITE in self.mode
		@staticmethod
		def ALL():
			return BaseDBServer.Users(not_=True)

	def checkUser(self,mode,userid):	
		mode=mode.upper()
		if not self.users.get(mode):
			return False
		return self.users[mode].contain(userid)
	@staticmethod
	def readIDFile(dname,fname):
		return readIDFile(dname,fname)
	def readUsers(self,conf,userdir=None):
#ALL : ALL Users
		if not userdir:
			userdir=self.dname
		READ=self.READ
		WRITE=self.WRITE
		if not conf.get("users"):	#conf don't have "users" or conf["users"] is Empty.
			return {READ:self.Users.ALL(),WRITE:self.Users()}	#default is all users have read auth but don't have read.
		applies={READ:self.Users(),WRITE:self.Users()}
		denies={READ:self.Users(),WRITE:self.Users()}
		for user in conf["users"]:
			if len(user["files"])==1 and user["files"][0].upper()=="ALL":
				users=self.Users.ALL()
			else:
				users=self.Users(reduce( lambda a,b:a+b,map(lambda fname:list(self.readIDFile(userdir,fname)),user["files"]) ))
			#print(users.data,user["mode"])
			if not user["mode"]:
				continue
			if "-" in user["mode"][0]:
				if READ in user["mode"]:
					denies[READ]+=users
				if WRITE in user["mode"]:
					denies[WRITE]+=users
			else:
				if READ in user["mode"]:
					applies[READ]+=users
				if WRITE in user["mode"]:
					applies[WRITE]+=users
		return {READ:applies[READ].else_(denies[READ]),WRITE:applies[WRITE].else_(denies[WRITE])}
		
	def readConf(self,fname):
		res={"users":[]}
		if not os.path.exists(fname):
			return res
		with open(fname,"r") as f:
			for line in f:
				key,value=line.rstrip().split(" ",1)
				key=key.upper()
				if key=="CHMOD":
#Chmod <mode> <files>...
#mode : "-" => deny . "w" => write . "r" => read
					mode,files=value.upper().split(" ",1)
					res["users"].append({"mode":mode,"files":files.split()})
				elif key=="LIMIT":
					res["limit"]=int(value)
		return res
	class Log:
		def __init__(self,data):
			self.data=data
		def search(self,host,from_="1900-1-1",until="4545-4-5"):
			for data in self[host]:
				if from_ <= data["date"] < until:
					yield data
		def __getitem__(self,key):
			return self.data[key]
		def __setitem__(self,key,value):
			self.data[key]=value
		def __getattr__(self,attr):
			return getattr(self.data,attr)
		def append(self,host,data):
			if not self.get(host):
				self[host]=[]
			self[host].append(data)
		@staticmethod
		def read(fname):
#res : {<host>:[<data>,...],...}
			res={}
			with open(fname,"r") as f:
				for line in f:
					try:	#read written by log_connection
						data=json.loads(line.rstrip())
						host=data["host"]
						if host not in res:
							res[host]=[]
						res[host].append(data)
					except:
						pass
			return BaseDBServer.Log(res)

class CardHandler(StreamRequestHandler):
#Handle request that client send to ServerDB.
	class Command:
		SEARCH="SEARCH"
		SEARCH2="SEARCH2"
		TAG="TAG"
		TOT="TOT"
		WRITE="WRITE"
		CSM="CSM"
		APPEND="APPEND"
#SEARCH <csmText>
#SEARCH2 <csmText>
#TAG <tag>
#TOT <tag>
#WRITE <csmText>
#APPEND <csms>...  #csms is json.
	def __init__(self,request,client_address,server):
		super().__init__(request,client_address,server)
	def handle(self):
		userid=getID(self.client_address[0])
		if not userid:
			self.wfile.write("400 don't know userid.".encode())
			return
		while True:
			#data=__utils__.recv3(self.request).decode("utf8","ignore")
			try:
				data=__utils__.recvForServer(self.request,self.server)
			except:
				return
			#print("Data",data)
			if not data:
				if not self.request._closed:
					self.wfile.write("400 $".encode())
				return
			data=data.decode("utf8","ignore")
			data=data.split(" ",1)
			self.server.log_connection(self.client_address[0],{"data":data,"client_address":self.client_address})
			command=data[0].upper()
			data=data[1] if len(data)>1 else str()
			#print("Data",data)
			if command == CardHandler.Command.SEARCH:
				self.search(userid,data,self.wfile)
			elif command == CardHandler.Command.TAG:
				self.printtag(userid,data,self.wfile)
			elif command == CardHandler.Command.TOT:
				self.getTOTs(userid,data,self.wfile)
			elif command == CardHandler.Command.WRITE:
				self.write(userid,data,self.wfile)
#WRITE <csm>
			elif command == CardHandler.Command.CSM:
				if not data:
					continue
				data=data.split(" ",1)
				command=data[0].upper()
				data=data[1] if len(data)>1 else list()
				if command == CardHandler.Command.APPEND:
					self.csm_append(userid,data,self.wfile)
	def blocked(self,userid,mode,output):
#mode is "R" or "W"
		if not self.server.checkUser(mode.upper(),userid):
			output.write("400 don't allow to read or write from this server.".encode())
			return True
		return False
	def search(self,userid,data,output):
#write res to output as encoded.
		if self.blocked(userid,"R",output):
			return
		if not data:
			memo=str()
			tags=list()
		else:
			csm=__data__.CSM.readText(data)
			memo=csm.memo
			tags=csm.tags
		cards=self.server.search(memo,tags)
		res=list(map(str,__data__.CSM.make(self.server.text,cards)))
		res=json.dumps(res)
		output.write(("200 "+res).encode())
	def printtag(self,userid,data,output):
		if self.blocked(userid,"R",output):
			return
		regTag=re.compile(data)
		tags=filter(lambda tag:re.search(regTag,tag),self.server.getTags())
		res="\n".join(tags)
		output.write(("200 "+res).encode())
	def getTOTs(self,userid,data,output):
		if self.blocked(userid,"R",output):
			return
		tag=data
		if tag:
			totIdxes=self.server.searchTOT(tag)
			if totIdxes:
				tots=__data__.TOT.make(self.server.text,totIdxes)
			else:
				tots=list()
		else:
			tots=__data__.TOT.make(self.server.text,self.server.tots.values())
		res=list(map(str,tots))
		res=json.dumps(res)
		output.write(("200 "+res).encode())
	def write(self,userid,data,output):
		if self.blocked(userid,"W",output):
			return
		if not data:
			return
		csm=__data__.CSM.readText(data)
		if __data__.TOT.isTOT(csm):
			tot=__data__.TOT.toTOT(csm)
			self.server.appendTOT(tot.name,tot.childs)
		else:
			self.server.append(csm.memo,csm.comment,(*csm.tags,"USERID:"+userid.upper()),csm.date)
		output.write("200 $".encode())
		self.server.save()
	def csm_append(self,userid,data,output):
		if self.blocked(userid,"W",output):
			return
		if not data:
			return
		#print(data)
		data=json.loads(data)
		for csm in map(lambda text:__data__.CSM.readText(text),data):
			if __data__.TOT.isTOT(csm):
				tot=__data__.TOT.toTOT(csm)
				self.server.appendTOT(tot.name,tot.childs)
			else:
				self.server.append(csm.memo,csm.comment,(*csm.tags,"USERID:"+userid),csm.date)
		self.server.save()
		output.write("200 $".encode())


class ServerDB(__db__.CardDB,BaseDBServer):
	class Allow:	#Imagine GitHub
		WRITE=1
		WRITE_TOT=2
		SEARCH=4	
		SEARCH_BY_CARD=8	#  If search don't be allowed and 
		PUSH_DATA=16
		CSM_PULL=32	
	USER_FILE="user.txt"
	SERVER_CONF="server.conf"
	USER_SEQ=":"
	def __init__(self,dname,server_addr):
		__db__.CardDB.__init__(self,dname)
		BaseDBServer.__init__(self,dname,server_addr,CardHandler)
	def close(self):
		__db__.CardDB.save(self)
		BaseDBServer.close(self)


class ServerTagDB(__db__.TagDB,BaseDBServer):
	def __init__(self,dname,server_addr):
		__db__.TagDB.__init__(self,dname)
		BaseDBServer.__init__(self,dname,server_addr,CardHandler)
	def close(self):
		__db__.TagDB.save(self)
		BaseDBServer.close(self)




class Command:
	GET="GET"
	POST="POST"
	ID="ID"
	HOST="HOST"




class HomeHandler(StreamRequestHandler):
#Handle request client send to HomeServer
	class Command:
		SELECT="SELECT"
		SEARCH="SEARCH"
#SELECT <dbid>
#SEARCH <tags>
	def __init__(self,request,client_address,server):
		super().__init__(request,client_address,server)
	def handle(self):
		"""
		SELECT : Res port of ServerDB specified by dbid
		SEARCH : Res data of DB searched by tags.
		"""
		userid=getID(self.client_address[0])
		if not userid:
			self.wfile.write("400 don't know userid.".encode())
			return
		data=__utils__.recvForServer(self.request,self.server).decode("utf8","ignore")
		#data=__utils__.recvall(self.request).decode("utf8","ignore")
		if not data:
			self.wfile.write("400 main".encode())
			return
		self.server.log_connection(self.client_address[0],{"data":data,"client_address":self.client_address})
		data=data.split(" ",1)
		command=data[0].upper()
		data=data[1] if len(data)>1 else str()
		#print("sdbs",*self.server.sdbs)
		if command == self.Command.SELECT:
#res port of dbid if found
			self.select(userid,data,self.wfile)
		elif command == self.Command.SEARCH:
			self.search(userid,data,self.wfile)
#SEARCH <tags>
	def select(self,userid,data,output):
		if not data:
			self.wfile.write("400 main".encode())
			return
		dbid=data.upper()
		sdb=self.server.getServer(dbid)
		if not sdb or not sdb.opened:
			self.wfile.write("400 main".encode())
			return
		port=sdb.port
		#print("PORT",port)
		output.write("200 {0}".format(port).encode())
	def search(self,userid,data,output):
		if not self.server.checkUser("R",userid):
			self.wfile.write("400 Don't allow read data from thid server.".encode())
			return 
		tags=list(map(lambda tag:tag.upper(),data.split(","))) if data else list()
		data=list(map(lambda data:{"id":data[0].id.get(self.server.text),"tags":data[1],\
		"served":self.server.served(data[0].id.get(self.server.text))},self.server.searchForTagWithTags(tags)))
		res="200 "+json.dumps(data)
		output.write(res.encode())




class BaseServerHome(__db__.BaseHomeDB,BaseDBServer):	#home for client.res port of ServerDB.
	"""
	HomeDB and Server.
	"""
	PORT=10000
	def __init__(self,dname,host,CardDBClass=__index__.DB,DBClass=ServerTagDB,cardAsBytes=False):
		self.handler=HomeHandler
		self.server_addr=(host,self.PORT)
		__db__.BaseHomeDB.__init__(self,dname,CardDBClass=CardDBClass,DBClass=DBClass,cardAsBytes=False)
		BaseDBServer.__init__(self,dname,self.server_addr,self.handler)
	def serve_forever2(self,event,timeout=1):
		return BaseDBServer.serve_forever2(self,event,timeout)
	@property
	def host(self):
		return self.server_addr[0]
	@property
	def port(self):
		return self.server_addr[1]
	def __select(self,dbid,port,*args,**kwargs):	#return DB of DataBase
		dbid=dbid.upper()
		sdb=self.getServer(dbid)
		if sdb:	#sbd and sdb isn't locked.
			return sdb
		return __db__.BaseHomeDB.select(self,dbid,*args,server_addr=(self.host,port),**kwargs)
	def select(self,dbid,*args,**kwargs):	#return DB of DataBase
		return self.__select(dbid,randomPort(),*args,**kwargs)
	def __serve(self,dbid,port):
#ServerDB that id is <dbid> start to serve.
#port : port of server
		dbid=dbid.upper()
		if not self.get(self.find(dbid)):	#dbid of dname doesn't exists.
			return False
		sdb=self.getServer(dbid)
		if sdb:
			if sdb.opened:
				return True
			else:
				if sdb.open():
					return True
				return False
		dname=os.path.join(self.dname,dbid)
		sdb=self.select(dbid)
		if sdb:
			if sdb.open():
				return True
		return False
	def serve(self,dbid):
		return self.__serve(dbid,randomPort())
	def served(self,dbid):	#return if dbid is served
		dbid=dbid.upper()
		sdb=self.getServer(dbid)
		if not sdb:
			return False
		return sdb.opened
	def stop(self,dbid):	#stop server if server is alive.
		dbid=dbid.upper()
		sdb=self.getServer(dbid)
		if sdb:
			sdb.stop()
		#sdb.close()
	def getServer(self,dbid):	#get server opened and closed
		dbid=dbid.upper()
		sdb=self.selectedDBs.get(dbid)
		if sdb and sdb.opened:
			return sdb
		return None
	def close(self):
		for key in self.selectedDBs:
			self.selectedDBs[key].close()
		BaseDBServer.close(self)
		__db__.BaseHomeDB.close(self)
		"""
		"""
		time.sleep(1)
		#for sdb in self.selectedDBs.values():
		#	print(sdb,sdb.opened,sdb.handling.queue,*map(lambda t:t.is_alive(),sdb.handling.queue))
		#print(self.opened,self.handling.queue,*map(lambda t:t.is_alive(),self.handling.queue))

class ServerHome(BaseServerHome):
	PORT=14546

class BaseClient:
#client for BaseServerHome
	def __init__(self,home_server_addr):
		self.home_server_addr=home_server_addr
		self.port=None
		self.dbid=None
		self.socket=None
	@property
	def host(self):
		return self.home_server_addr[0]
	def __getattr__(self,attr):
		return getattr(self.socket,attr)
	@property
	def connected(self):
		return bool(self.dbid) and (self.socket and not self.socket._closed)
	def socketForHome(self):
		__socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		try:
			__socket.connect(self.home_server_addr)
		except Exception as e:
			print(e)
			pass
		return __socket
		
	def getPort(self,dbid):
		with self.socketForHome() as __socket:
			query="{0} {1}".format(HomeHandler.Command.SELECT,dbid)
			__socket.sendall(query.encode())
			data=__utils__.recvall(__socket,blocked=True).decode("utf8","ignore")
			#print("Data",data)
		if not data:
			raise Exception("Can't connect "+str(dbid))
		else:
			status,port=data.split(" ",1)
			if status[0]=="4":
				raise Exception("Can't connect "+str(dbid))
			return int(port)
	def connect(self,dbid):
		try:
			port=self.getPort(dbid)
		except Exception as e:
			print(e)
			return False
		if not port:
			return False
		if self.connected:
			self.close()
		self.socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		try:
			self.socket.connect((self.host,port))
		except:
			return False
		if self.socket._closed:
			return False
		#print("Connect...")
		self.dbid=dbid
		self.port=port
		return True
	def searchDB(self,tags):
		with self.socketForHome() as __socket:
			query=HomeHandler.Command.SEARCH+" "+",".join(tags)
			__socket.sendall(query.encode())
			time.sleep(1)
			data=__utils__.recvall(__socket,blocked=True).decode("utf8","ignore")
			if not data:
				raise Exception("Error!!!")
			status,data=data.split(" ",1)
			if status[0]=="4":
				raise Exception("Error!!!")
			return json.loads(data)
#<id> <tag1> <tag2> ...
	def __enter__(self):
		return self
	def __exit__(self,*args):
		self.close()
		return self
	def close(self):
		if self.socket:
			self.socket.close()
		self.dbid=None
		self.port=None
	def recvall(self,blocked=False):
		return __utils__.recvall(self.socket,blocked)
	def request(self,command,data):
		if not self.connected:
			return str()
		query=command+" "+data
		self.socket.sendall(query.encode())
		return self.recvall(blocked=True).decode("utf8","ignore")

class BaseClientU(BaseClient):
	def __init__(self,userid,port):
		self.userid=userid
		host=getHost(userid)
		super().__init__((host,port))

class Client(BaseClient):
#client for CardHandler
	def __init__(self,host):
		super().__init__((host,ServerHome.PORT))
	def requestCSM(self,command,data):
		return self.request(CardHandler.Command.CSM+" "+command,data)
	def search(self,memo=str(),tags=list()):
		data=self.request(CardHandler.Command.SEARCH,str(__data__.CSM(memo=memo,tags=tags)))
		if not data:
			return
		data=data.split(" ",1)
		if data[0][0]!="2":
			return
		data=json.loads(data[1])
		for text in data:
			csm=__data__.CSM.readText(text)
			if csm:
				yield csm
	def dumpCSM(self):
		return self.search()
	def getTags(self,tag=str()):
		data=self.request(CardHandler.Command.TAG,tag)
		if not data or data[0]!="2":
			return []
		return data.split(" ",1)[1].split("\n")
	def getTOTs(self,tag=str()):
		data=self.request(CardHandler.Command.TOT,tag)
		if not data or data[0]!="2":
			return []
		data=data.split(" ",1)[1]
		if data:
			data=json.loads(data)
			return filter(lambda tot:bool(tot),map(lambda text:__data__.TOT.readText(text),data))
		return []
	def dumpTOT(self):
		return self.getTOTs()
	def write(self,memo,comment=str(),tags=list(),date=str()):
		if not date:
			date=datetime.datetime.now()
		data=self.request(CardHandler.Command.WRITE,str(__data__.CSM(memo,comment,tags,date)))
		if not data:
			return False
		data=data.split(" ")
		if data[0][0]=="2":
			return True
		return False
	def writeTOT(self,name,tags):
		tot=__data__.TOT.make2(name,tags)
		return self.write(tot.memo,tot.comment,tot.tags,tot.date)
	def appendCSMs(self,csms,override=False):
		data=list(map(str,csms))
		return self.requestCSM(CardHandler.Command.APPEND,json.dumps(data))
	def appendTOT(self,dname,override=False):
		data=list(map(str,__data__.TOT.readDir(dname)))
		return self.requestCSM(CardHandler.Command.APPEND,json.dumps(data))
	def searchByCard(self,card):
		pass
	def pushData(self,text):	#If you want to push data and you don't have authority to write.
		pass
	def make(self,memo,comment,tags,date):
		pass
	def save(self):		#for treated as CSM_DB
		pass

class ClientU(Client):
	def __init__(self,userid):
		self.userid=userid
		host=getHost(userid)
		super().__init__(host)



HOST="127.0.0.1"
PORT=31103
def request(command,data):
	query=command+" "+data
	with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
		s.connect((HOST,PORT))
		#print("request",HOST,PORT,query)
		s.sendall(query.encode())
		res=__utils__.recvall(s,blocked=True).decode("utf8","ignore")
	if not res:
		return("400",None)
#<status> <data>
	res=res.split(" ",1)	#status,data
	if len(res)==1:
		return (res[0],None)
	return res
def get(command,data):
	return request(Command.GET,command+" "+data)
def getHost(id_):
	data={"id":id_}
	status,data=get(Command.HOST,json.dumps(data))
	if status[0]!="2":
		return None
	data=json.loads(data)
	return data.get("host")
def getID(host):
	data={"host":host}
	status,data=get(Command.ID,json.dumps(data))
	if status[0]!="2":
		return None
	data=json.loads(data)
	return data.get("id")




def __readIDFile(fname):
#get recursive file by "File:"
#*** example ***
#satoXXX
#kimuraXXX
#File:XXXfriend.txt
#	:
#	:
	fname=__utils__.realpath(fname)
	frontiers=[fname]
	explored=[]
	curdir=__utils__.realpath(".")
	while frontiers:
		fname=frontiers.pop()
		if hash(fname) in explored:
			continue
		home,_=os.path.split(fname)
		os.chdir(home)	#cd dname that contain fname
		with open(fname,"r") as f:
			for line in f:
				line=line.rstrip()
				if line.find("File:")==0:
					_,fname__=line.split(":",1)
					fname__=__utils__.realpath(fname__)
					frontiers.append(fname__)
				else:
					yield line
		explored.append(hash(fname))
		os.chdir(curdir)

def readIDFile(home,fname):
	curdir=__utils__.realpath(".")
	home=_util.realpath(home)
	os.chdir(home)
	for id_ in __readIDFile(fname):
		yield id_
	os.chdir(curdir)

