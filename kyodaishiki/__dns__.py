import socket
from . import __utils__
from . import __server__
import json
import socketserver
import os

class Type:
	USER="USER"
	GROUP="GROUP"
	SUBSET="SUBSET"

HOST_DOMAIN="kyodaishiki.xxx"

HOST="127.0.0.1"
PORT=31103
SERVER_ADDR=(HOST,PORT)
DEFAULT_PORT=31103
DEFAULT_SEVER_ADDR=(HOST,DEFAULT_PORT)

class Command:
	GET="GET"
	POST="POST"
	ID="ID"
	HOST="HOST"
#GET ID <host>
#GET HOST <id>
#POST <id>
class Handler(socketserver.StreamRequestHandler):
	def handle(self):
		try:
			data=__utils__.recvForServer(self.request,self.server)
		except:
			return
		if not data:
			if not self.request._closed:
				self.wfile.write("400 $".encode())
			return
		data=data.decode("utf8","ignore")
		data=data.split(" ",1)
		#print(data)
		command=data[0]
		data=data[1] if len(data)>1 else str()
		if command == Command.GET:
			data=data.split(" ",1)
			if len(data)<=1:
				self.wfile.write("400 $".encode())
				return
			command,data=data
#data : {"host":,"id":,}
			data=json.loads(data)
			if command == Command.ID:
				host=data.get("host")
				id_=self.server.getID(host)
				if not id_:
					self.wfile.write("400 $".encode())
					return
				res={"id":id_}
			if command == Command.HOST:
				id_=data.get("id")
				host=self.server.getHost(id_)
				if not host:
					self.wfile.write("400 $".encode())
					return
				res={"host":host}
			#print("res",res,"dnsData",self.server.data)
			self.wfile.write(("200 "+json.dumps(res)).encode())
			return
			#######
		elif command==Command.POST:
			data=json.loads(data)
			id_=data.get("id")
			host=data.get("host")
			if not (id_ and host):
				self.wfile.write("401 $".encode())
				return
			self.server.append(id_,host)
			self.wfile.write("201 $".encode())
			return
				
			#########

class Server(__server__.ThreadingTCPServer2):
	PORT=DEFAULT_PORT
	DATA_SEQ=":"
	DNS_FILE="dns.txt"
	def __init__(self,host,dname):
		server_addr=(host,DEFAULT_PORT)
		__server__.ThreadingTCPServer2.__init__(self,server_addr,Handler)
		if not os.path.exists(dname) and dname:
			os.makedirs(dname)
		self.fname=os.path.join(dname,Server.DNS_FILE)
		self.__data=dict()
		self.read(self.fname)
	@property
	def data(self):
		return self.__data
	def read(self,fname):
		if not os.path.exists(fname):
			return
		with open(fname,"r") as f:
			for id_,host in map(lambda line:line.rstrip().split(Server.DATA_SEQ),f):
				self.__data[id_]=host
	def getHost(self,id_):
		return self.__data.get(id_)
	def getID(self,host):
		for id_,host__ in self.__data.items():
			if host__ == host:
				return id_
	def append(self,id_,host):
		if self.getHost(id_) or self.getID(host):
			return False
		self.__data[id_]=host
		return True
	def save(self):
		with open(self.fname,"w") as f:
			f.write("\n".join(map(lambda data:data[0]+Server.DATA_SEQ+data[1],self.__data.items())))
	def close(self):
		super().close()
		self.save()
	def __enter__(self):
		return self
	def __exit__(self,*args):
		self.save()
		self.close()

		
class Client(socket.socket):	#request to DNS Server.
	def __init__(self,host):
		self.dns_server_addr=(host,Server.PORT)
		super().__init__(socket.AF_INET,socket.SOCK_STREAM)
	def connect(self):
		return super().connect(self.dns_server_addr)

	def __enter__(self):
		self.connect()
		return self
	def __exit__(self,*args):
		self.close()
	def request(self,command,data):
		query=command+" "+data
		self.sendall(query.encode())
		res=__utils__.recvall(self,blocked=True).decode("utf8","ignore")
		if not res:
			return("400",None)
#<status> <data>
		res=res.split(" ",1)	#status,data
		if len(res)==1:
			return (res[0],None)
		return res
	def get(self,command,data):
		return self.request(Command.GET,command+" "+data)
	def getHost(self,id_):
		data={"id":id_}
		status,data=self.get(Command.HOST,json.dumps(data))
		if status[0]!="2":
			return None
		data=json.loads(data)
		return data.get("host")
	def getID(self,host):
		data={"host":host}
		status,data=self.get(Command.ID,json.dumps(data))
		if status[0]!="2":
			return None
		data=json.loads(data)
		return data.get("id")
	def post(self,id_,host):
		data={"id":id_,"host":host}
		return self.request(Command.POST,json.dumps(data))
		
def request(command,data):
	query=command+" "+data
	with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
		s.connect((HOST,PORT))
		print("request",HOST,PORT,query)
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
