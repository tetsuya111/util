from . import __db__
from . import __data__
from . import __dns__
from . import __index__
from . import _util
from . import __server__
from . import __path__
from ._util import *
import sys
import docopt
import random
import subprocess as sp
from functools import *
import re
import shutil
import os
import threading
import datetime
import io
import json
import copy
import _pyio
import colorama

DEFAULT_HOME_DIR=realpath("%USERPROFILE%\\kyodaishiki")
DEFAULT_CSM_DIR=realpath("%USERPROFILE%\\Desktop\\csmFiles")

sys.path.append(_util.realpath("%USERPROFILE%\\code/kyodaishiki2"))

Query=_util.Query

class ExitShell(BaseException):pass

class EnvKey:
	LOADER_HOME="KYODAISHIKI_LOADER_HOME"
	WRITE_TAGS="WRITETAGS"

class BaseShell:
	ENTER_BAT="enter.bat"
	EXIT_BAT="exit.bat"
	PROMPT=">>"
#property:
#	dname : dname
#	enterBat : execute each line in this when you enter shell.specified by dname.
#	exitBat : execute each line in this when you exit shell.specified by dname.
#	prompt : prompt used for input to shell.
#	stdin : standard input.
#	stdout : standard output.
#function
#	override:
#		execQuery(query,output) : execute query.called in some functions.(begin,shell,...)
#	else:
#		__begin(input_,output) : begin process.
#		beginf(fname) : override of __begin.input from fname.output is self.stdout.
#		begin() : override of __begin.input is self.stdin.output is self.stdout.
#		shell() : like begin.print prompt before readline.
#		start() : override of begin().process enterBat and exitBat.
	def __init__(self,dname=None,prompt=">>",stdin=sys.stdin,stdout=sys.stdout):
		if dname:
			self.dname=_util.realpath(dname)
			if not os.path.exists(self.dname):
				os.makedirs(self.dname)
			self.enterBat=os.path.join(self.dname,self.ENTER_BAT)
			self.exitBat=os.path.join(self.dname,self.EXIT_BAT)
			_util.touch(self.enterBat)
			_util.touch(self.exitBat)
		else:
			self.dname=None
			self.enterBat=""
			self.exitBat=""
		self.prompt=prompt
		self.stdin=stdin
		self.stdout=stdout
	def execQuery(self,query,output):
		if not query:
			return
		if query.command in Command.QUIT:
			raise ExitShell
		elif query.command in Command.HELP:
			output.write("""\n$ exec file <fname>\n\n""")
		elif query.command in Command.EXEC:
			try:
				args=docopt.docopt(Docs.EXEC,query.args)
			except SystemExit as e:
				print(e)
				return 
			if args["file"]:
				fname=_util.realpath(args["<fname>"])
				return self.beginf(fname,stdout=output)
		elif query.command in Command.MAP:
			try:
				args=docopt.docopt(Docs.MAP,query.args)
			except SystemExit as e:
				print(e)
				return 
			if args["stdin"]:
				query_f=args["<query_f>"]
				for line in sys.stdin.readlines():
					line=line.strip()
					if not line:
						continue
					args=re.split("[ \t]+",line)
					self.execQuery(Query(("map",query_f,*args)),output)
			else:
				query_f=args["<query_f>"]
				args=list(map(lambda arg:arg.split(","),args["<args>"]))
				lenArgs=list(map(len,args))
				#print(args,lenArgs)
				for i in range(max(lenArgs)):
					args__=map(lambda arg,length:arg[i]if i<length else arg[length-1],args,lenArgs)
					query__=query_f.format(*args__)
					query__=Query.read(query__)
					self.execQuery(query__,output)
		elif query.command in Command.XARGS:
			try:
				line=sys.stdin.readline().strip()
			except KeyboardInterrupt:
				return
			except Exception as e:
				print(e)
				return
			query__=Query.read(line)
			query=Query((*query.args,*query__))
			return self.execQuery(query,output)
		elif query.command in Command.SHELL:
			try:
				res=sp.check_output(" ".join(query.args),shell=True)
				res=res.decode()
				print(res,file=output)
			except Exception as e:
				print(e)
		else:
			#output.write("Quit is \"q\" or \"quit\".\n")
			return None
	def _begin_one_liner(self,input_,output,precmd=None,postcmd=None):
		try:
			if precmd:
				precmd()
			output.flush()
			if not input_.readable():
				return 1
			line=input_.readline()
			if not line:	#reach EOF
				return 0
			query=Query.read(line)
			res=self.execQuery(query,output)
			if postcmd:
				postcmd(query)
		except ExitShell:
			#0
			return -2
		except SystemExit:
			#-1
			return -1
		except ValueError:
			
			return -1
		except KeyboardInterrupt:
			pass
		except UnicodeEncodeError:
			pass
		except Exception as e:
			print(e,type(e))
		return 1
	def __begin__(self,input_,output,precmd=None,postcmd=None):
		while True:
			res=self._begin_one_liner(input_,output,precmd=precmd,postcmd=postcmd)
			if res <= 0:
				return res
		return None
	def begin(self):
		return self.__begin__(self.stdin,self.stdout)
	def beginf(self,fname,stdout=None):
		if not os.path.exists(fname):
			return 0
		if not stdout:
			stdout=self.stdout
		with open(fname,"r") as f:
			return self.__begin__(f,output=stdout)
	def shell(self):
		return self.__begin__(self.stdin,self.stdout,lambda:print(self.prompt,file=self.stdout,end=""))
	def start(self):
		if self.enterBat:
			res=self.beginf(self.enterBat)
			if res == -2:
				return
		self.shell()
		if self.exitBat:
			self.beginf(self.exitBat)
	def close(self):
		pass
	def __enter__(self):
		return self
	def __exit__(self,*args,**kwargs):
		self.close()

class BaseShell2(BaseShell):
#this have childs of shell.
#child of shell in <module_name> is called command that name is <module_name>
#command can admit <commandConf> that is <dname>/<COMMAND_CONF>.
#name of child of shell is self.CHILD_SHELL
	CHILD_SHELL="ChildShell"
	CONF_SEQ=":"
	COMMAND_SEQ=","
	def __init__(self,dname=None,prompt=BaseShell.PROMPT):
		super().__init__(dname,prompt)
		self.shells={}
		self.aliasCommands={}

	@property
	def childNames(self):
		return list(filter(lambda module_name:hasattr(sys.modules[module_name],self.CHILD_SHELL),sys.modules))
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write("""
# help [(-a|--all)]
# ls
# clean
			\n""")
			if query.args and query.args[0] in ("-a","--all"):
				for childName in self.childNames:
					output.write("# "+childName+"\n")
		elif query.command in Command.ALIAS:
			return self.alias(query.args,output)
		elif query.command in self.aliasCommands:
			query__=self.aliasCommands[query.command]
			query__=Query((*query__.data,*query.args))
			return self.execQuery(query__,output)
		elif query.command.lower() in self.childNames:
			return self.do_shell(query.command.lower(),query.args,output)
		elif query.command in Command.DB.LS:
			output.write("\n".join(self.childNames)+"\n")
		elif query.command in Command.CLEAN:
			return self.clean(output)
		else:
			return super().execQuery(query,output)
	def listChilds(self):
		return map(lambda childName:getattr(childName,self.CHILD_SHELL),self.childNames)
	def getShell(self,module_name,*args,**kwargs):
		if module_name not in self.childNames:
			return None
		if not self.shells.get(module_name):
			try:
				self.shells[module_name]=eval("sys.modules[\"{0}\"].{1}(*args,**kwargs)".format(module_name,self.CHILD_SHELL))
			except Exception as e:
				print(e,file=sys.stderr)
		return self.shells[module_name]
	def do_shell(self,module_name,args,output,*args__,**kwargs):
		shell=self.getShell(module_name,*args__,**kwargs)
		if not shell:
			return False
		if args:
			shell.execQuery(Query(args),output)
		else:
			shell.start()
	def clean(self,output=None):
		for module_name,shell in self.shells.items():
			shell.close()
			if output:
				output.write("closed {0}.\n".format(module_name))
	def alias(self,args,output):
		if len(args)<2:
			output.write(Docs.ALIAS+"\n")
			for command in self.aliasCommands:
				output.write("{0} -> {1}\n".format(command.lower(),self.aliasCommands[command]))
			return
		command=args[0]
		if command in ("rm","remove"):
			command=args[1].upper()
			query=self.aliasCommands.get(command)
			if not query:
				output.write("Don't find {0}\n".format(command.lower()))
				return
			self.aliasCommands.pop(command)
			output.write("Removed {0} -> {1}\n".format(command.lower(),query))
		else:
			command=command.upper()
			#query=Query(args[1:])
			args=" ".join(args[1:])
			query=Query.read(args)
			self.aliasCommands[command]=query
			output.write("Append {0} -> {1}.\n".format(command.lower(),query))
	def close(self):
		super().close()
		self.clean()
	def start(self):
		super().start()
		self.clean()
	@staticmethod
	def readCommandConf(fname):
#in conf => <module_name>:<commands>...
#res => {<command>:<module_name>,...}
		res={}
		if not os.path.exists(fname):
			return {}
		with open(fname,"r") as f:
			for line in f:
				module_name,commands=line.rstrip().split(BaseShell2.CONF_SEQ,1)
				for command in commands.split(BaseShell2.COMMAND_SEQ):
					res[command.upper()]=module_name
				if not sys.modules.get(module_name):
					exec("import {0}".format(module_name))
		return res


class Shell:
	@staticmethod
	def writeTOT():
		name=input("Name:")
		tags=list(inputUntilSeq("Tag:"))
		return __data__.TOT.make2(name,tags)
	@staticmethod
	def write():
		memo="\n".join(inputUntilSeq("Memo : "))
		comment="\n".join(inputUntilSeq("Comment : "))
		tags=list(inputUntilSeq("Tag : "))
		date=str(datetime.datetime.now()).split(".")[0]
		return __data__.CSM(memo,comment,tags,date)



class PMode:
	MEMO="M"
	COMMENT="C"
	TAG="T"
	DATE="D"


class CSMShell(BaseShell):	
#shell for CSM_DB or TOT_DB
	PROMPT=">>"
	@staticmethod
	def is_CSM_DB(db):
		return hasattr(db,"dumpCSM")
	@staticmethod
	def is_TOT_DB(db):
		return hasattr(db,"dumpTOT")
	def __init__(self,db,input_=sys.stdin):
		super().__init__(prompt=self.PROMPT,stdin=input_)
		self.db=db
	def execQuery(self,query,output):
		if query.command in Command.WRITE:
			return self.write(query.args,output)
		elif query.command in Command.SEARCH:
			return self.search(query.args,output)
		elif query.command in Command.APPEND:
			return self.append(query.args,output)
	def write(self,args,output):
		try:
			args=docopt.docopt(Docs.CSM.WRITE,args)
		except SystemExit as e:
			print(e)
			return
		dname=args["<dname>"] if args["-d"] else DEFAULT_CSM_DIR
		dname=_util.realpath(dname)
		if not os.path.exists(dname):
			os.makedirs(dname)
		if self.is_CSM_DB(self.db):
			for csm in self.db.dumpCSM():
				csm.write(os.path.join(dname,csm.fname))
		if self.is_TOT_DB(self.db):
			for tot in self.db.dumpTOT():
				tot.write(os.path.join(dname,tot.fname))
	def append(self,args,output):
		if not args:
			output.write("csm append <csms> <tots> [(-O|--override)]\n")
			return
		csms=list(map(__data__.CSM.readText,json.loads(args[0])))
		tots=list(map(__data__.TOT.readText,json.loads(args[1])))
		override=len(args)>2 and args[2] in ("-O","--override")
		if self.is_CSM_DB(self.db):
			self.db.appendCSMs(csms,override)
		if self.is_TOT_DB(self.db):
			for tot in tots:
				self.db.appendTOT(tot.name,tot.childs)
	def search(self,args,output):
		try:
			args=docopt.docopt(Docs.CSM.SEARCH,args)
		except SystemExit as e:
			print(e)
			return
		dname=args["<dname>"] if args["-d"] else DEFAULT_CSM_DIR
		if not os.path.exists(dname):
			output.write("Don't exist {0} \n".format(dname))
			return
		if args["tot"]:
			tag=args["<tag>"].upper() if args["-t"] else ""
			regTag=re.compile(tag)
			data=""
			for tot in __data__.TOT.make(self.db.text,self.db.searchTOT(tag)):
				fname=realpath(os.path.join(dname,tot.fname))
				if os.path.exists(fname):
					data+="NAME:"+tot.name+"\n"
					data+=fname+"\n"
			output.write(data)
				
		else:
			memo=args["<memo>"] if args["-m"] else str()
			tags=args["<tags>"].upper().split(",") if args["-t"] else list()
			if not self.is_CSM_DB(self.db):
				return
			regMemo=re.compile(memo)
			data=""
			for csm in filter(lambda csm:re.search(regMemo,csm.memo) and (not tags or all(map(lambda tag:tag in csm.tags,tags))),self.db.dumpCSM()):
				fname=os.path.join(dname,csm.fname)
				if os.path.exists(fname):
					data+="* "+csm.memo+"\n"
					data+="-> "+realpath(os.path.join(dname,csm.fname))+"\n"
			output.write(data)
class CSMShell2(CSMShell):
#"append <csms> <tots>" -> "append [(-d <dname>)]"
	def append(self,args,output):
		try:
			args=docopt.docopt(Docs.CSM.APPEND,args)
		except SystemExit as e:
			print(e,args)
			return
		dname=args["<dname>"] if args["-d"] else DEFAULT_CSM_DIR
		tots=[]
		csms=[]
		for fname in map(lambda fname:os.path.join(dname,fname),os.listdir(dname)):
			if "."+__data__.CSM.EXT not in fname:
				continue
			try:
				csm=__data__.CSM.read(fname)
				if __data__.TOT.isTOT(csm):
					tots.append(__data__.TOT.toTOT(csm))
				else:
					csms.append(csm)
			except Exception as e:
				print(e,fname)
		args__=[json.dumps(list(map(str,csms))),json.dumps(list(map(str,tots)))]
		if args["-O"] or args["--override"]:
			args__.append("--override")
		return super().append(args__,output)
					
class DBShell(BaseShell):
	PROMPT=">>"
	ELSE_SEARCH_HEAD="@"
	def __init__(self,db,input_=sys.stdin):
		BaseShell.__init__(self,dname=db.dname,prompt=self.PROMPT,stdin=input_)
		self.db=db
	def execQuery(self,query,output):
		if query.command in Command.SEARCH:
			try:
				return self.search(query.args,output)
			except KeyboardInterrupt as e:
				output.write(str(e)+"\n")
				return
		elif query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		elif query.command in Command.ID:
			output.write(self.db.id.lower()+"\n")
		elif query.command in Command.CSM:
			return CSMShell2(self.db).execQuery(Query(query.args),output)
		elif query.command in Command.CLEAN:
			return self.db.clean()	#remove tmp
		elif query.command in Command.REMOVE:
			return self.remove(query.args,output)
		elif query.command in Command.LIST:
			return self.list(query.args,output)
		elif query.command in Command.WRITE:
			try:
				return self.write(query.args,output)
			except Exception as e:
				print(e)
		elif query.command in Command.QUIT:
			raise ExitShell
		elif query.command in Command.EXEC:
			return super().execQuery(query,output)
		elif query.command and query.command[0] == self.ELSE_SEARCH_HEAD:
			tag=query.command[1:]
			return self.execQuery(Query(("search","-t",tag,*query.args)),output)
		else:
			return super().execQuery(query,output)
				
	def start(self):
		self.stdout.write("*** "+self.db.id+" ***\n")
		super().start()
	def close(self):
		super().close()
		self.db.save()
	def search(self,args,output):
		try:
			args=docopt.docopt(Docs.SEARCH,args)
		except SystemExit as e:
			print(e)
			return
		memo=args["<memo>"] if args["-m"] else str()
		tags=args["<tags>"].upper().split(",") if args["-t"] else str()
		pMode=args["<pMode>"].upper()+"M" if args["-p"] else "M"
		random_=args["-r"] or args["--random"]
		cards=list(self.db.search(memo,tags))
		if random_:
			random.shuffle(cards)
		else:
			cards=sorted(cards,key=lambda card:card.date)
		data=""
		for csm in __data__.CSM.make(self.db.text,cards):
			data+="* "+csm.dump(pMode)+"\n"
			data+="------------------------------------------------------------------------\n"
		output.write(data)
	def list(self,args,output):
		try:
			args=docopt.docopt(Docs.LIST,args)
		except SystemExit as e:
			print(e)
			return
		tag=args["<tag>"].upper() if args["<tag>"] else ""
		if args["tot"]:
			if tag:
				U=self.db.getU()
				tots=__data__.TOT.make(self.db.text,self.db.searchTOT(tag))
			else:
				tots=__data__.TOT.make(self.db.text,self.db.tots.values())
			data=""
			for tot in tots:
				data+="NAME:"+tot.name+"\n"
				data+="TAGS:"+" ".join(tot.childs)+"\n"
			output.write(data)
		else:
			tag=re.compile(tag)
			tags=filter(lambda tag__:re.search(tag,tag__),self.db.getTags())
			data=[]
			for tag__ in tags:
				tagobj= self.db.tag.get(self.db.find(tag__))
				if tagobj:
					data.append((tag__,len(tagobj.cardIDs)))
			res=""
			for tag__,n in sorted(data,key=lambda data__:data__[1]):
				res+=tag__+" "+str(n)+"\n"
			output.write(res)
	def write(self,args,output):
		try:
			args=docopt.docopt(Docs.WRITE,args)
		except SystemExit as e:
			print(e)
			return
		if args["tot"]: 
			tot=Shell.writeTOT()
			self.db.appendTOT(tot.name,tot.childs)
		else:
			tags=self.environ.get(EnvKey.WRITE_TAGS)
			tags=tags.upper().split(",") if tags else []
			csm=Shell.write()
			csm.tags=(*csm.tags,*tags)
			self.db.appendCSM(csm)
		self.db.save()
	def remove(self,args,output):
		try:
			args=docopt.docopt(Docs.REMOVE,args)
		except SystemExit as e:
			print(e)
			return
		if args["tot"]:
#if tag is "A". remove "A" and "A&&B&&..." etc...
			tag=args["<tag>"]
			res=str()
			if not tag:
				output.write("You will remove all TOTs. Really OK??(y/n) : ")
				yn=input()
				if yn.upper()!="Y":
					return res
				tag=".*"
			tag="^\(*"+tag.upper()+"\)*$"
			for tot in list(self.db.searchTOT(tag)):
				name=__data__.TOT.makeOne(self.db.text,tot).name
				self.db.removeTOT(tot.id)
				output.write("Removed "+name+"\n")
			self.db.save()
		else:
			memo=args["<memo>"] if args["-m"] else str()
			tags=args["<tags>"].split(",") if args["-t"] else str()
			if not memo and not tags:
				output.write("You will remove all cards. Really OK??(y/n) : ")
				yn=input()
				if yn.upper()!="Y":
					return 
			for card in list(self.db.search(memo,tags)):
				self.db.remove(card.id)
				output.write("Removed "+card.memo(self.db.text)+"\n")
			self.db.save()


class ClientShell(BaseShell):
	PROMPT=">>>"
	def __init__(self,client):
		self.client=client
		super().__init__(prompt=self.PROMPT)
	def execQuery(self,query,output):
		if not query:
			return
		elif query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		elif query.command in Command.CSM:
			return CSMShell2(self.client).execQuery(Query(query.args),output)
		elif query.command in Command.SEARCH:
			return self.search(query.args,output)
		elif query.command in Command.LIST:
			return self.printtag(query.args,output)
		elif query.command in Command.WRITE:
			return self.write(query.args,output)
		else:
			return super().execQuery(query,output)
	def start(self):
		self.stdout.write("*** client {0} {1} ***\n".format(self.client.host,self.client.dbid))
		super().start()
	def search(self,args,output):
		try:
			args=docopt.docopt(Docs.SEARCH,args)
		except SystemExit:
			return
		memo=args["<memo>"] if args["-m"] else str()
		tags=args["<tags>"].split(",") if args["-t"] else str()
		pMode=args["<pMode>"].upper()+"M" if args["-p"] else "M"
		random_=args["-r"] or args["--random"]
		#print(memo,tags)
		res=str()
		csms=self.client.search(memo,tags)
		if random_:
			csms=list(csms)
			random.shuffle(csms)
		else:
			csms=sorted(csms,key=lambda csm:csm.date)
		data=""
		for csm in csms:
			data+="* "+csm.dump(pMode)+"\n"
			data+="-----------------------------------------------------------------------------\n"
		output.write(data)
	def printtag(self,args,output):
		try:
			args=docopt.docopt(Docs.LIST,args)
		except Exception as e:
			print(e)
			return
		try:
			res=str()
			tag=args["<tag>"].upper() if args["<tag>"] else str()
			data=""
			if args["tot"]:
				for tot in self.client.getTOTs(tag):
					data+="NAME:"+tot.name+" \nTAGS:"+str(tot.childs)+"\n"
			else:
				for tag in self.client.getTags(tag):
					data+=tag+"\n"
			output.write(data)
		except Exception as e:
			print(e)
	def write(self,args,output):
		try:
			args=docopt.docopt(Docs.WRITE,args)
		except SystemExit:
			return
		if args["tot"]:
			tot=Shell.writeTOT()
			self.client.writeTOT(tot.name,tot.childs)
		else:
			csm=Shell.write()
			self.client.write(csm.memo,csm.comment,csm.tags,csm.date)


def is_server(db):
	return hasattr(db,"serve_forever")



class BaseHomeShell(BaseShell):
#shell for BaseHome
	PROMPT="%"
	def __init__(self,home,DBShell_,prompt=None):
		self.home=home
		if not prompt:
			prompt=self.PROMPT
		self.DBShell=DBShell_
		self.HomeClass=type(home)
		super().__init__(home.dname,prompt)
	def execQuery(self,query,output):
		if query.command in Command.QUIT:
			raise ExitShell
		elif query.command in Command.HELP:
			try:
				args=docopt.docopt(Docs.DB.HELP_COMMAND,query.args)
			except SystemExit as e:
				print(e)
				return
			output.write(Docs.DB.HELP.strip()+"\n")
			return
		elif query.command in Command.DB.LS:
			try:
				args=docopt.docopt(Docs.DB.LS,query.args)
			except SystemExit as e:
				print(e)
				return
			#cardToTags=self.home.cardToTags
			for db in self.home.listDB():
				dbid=db.getID(self.home.text)
				#tags=list(map(lambda tagIdx:tagIdx.get(self.home.text),cardToTags.get(db.id)))
				#output.write("ID:"+dbid.lower()+" -> {1}".format(",".join(tags))+"\n")
				output.write("ID:"+dbid.lower()+"\n")
				#print("tags:",*db.tags(self.home.text))
		elif query.command in Command.SEARCH:
			try:
				args=docopt.docopt(Docs.DB.SEARCH,query.args)
			except SystemExit as e:
				print(e)
				return
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			dbid=args["<dbid>"] if args["-D"] else ".*"
			pMode=args["<pMode>"].upper() if args["-p"] else ""
			all_=args["-a"] or args["--all"]
			text=""
			for card in self.home.search(dbid,tags):
				dbid_=card.getID(self.home.text).lower()
				if dbid_.find("__")==0 and not all_:
					continue
				tags=map(lambda tagIdx:tagIdx.get(self.home.text),self.home.cardToTags.get(card.id,[]))
				text+=dbid_
				if "T" in pMode:
					text+=" -> "+",".join(tags)
				text+="\n"
			output.write(text)
		elif query.command in Command.REMOVE:
			try:
				args=docopt.docopt(Docs.Home.REMOVE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["tot"]:
				tag=args["<tag>"].upper() if args["-t"] else ""
				for tot in list(self.home.searchTOT(tag)):
					if self.home.removeTOT(tot.id):
						output.write("Removed "+str(__data__.Logic.Group.makeFromIndex(tot.nameGroup,self.home.text))+"\n")
			else:
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				dbid=args["<dbid>"].upper() if args["-D"] else ".*"
				if not tags and not args["-D"]:
					output.write("Don't find tags or dbid.\n")
					return
				for dbIdx in list(self.home.searchForTagOnlyCard(tags)):
					now_dbid=dbIdx.getID(self.home.text)
					if re.fullmatch(dbid,now_dbid):
						if self.home.remove(now_dbid):
							output.write("Removed "+now_dbid+"\n")
						else:
							output.write("Can't remove "+now_dbid+"\n")
			self.home.save()
		elif query.command in Command.APPEND:
			return self.append(query.args,output)
		elif query.command in Command.DB.SELECT:
			return self.select(query.args,output)
		elif query.command in Command.LIST:
			try:
				args=docopt.docopt(Docs.LIST,query.args)
			except SystemExit as e:
				print(e)
				return
			res=str()
			tag=args["<tag>"].upper() if args["<tag>"] else str()
			if args["tot"]:
				if tag:
					tots=__data__.TOT.make(self.home.text,[self.home.searchTOT(tag)])
				else:
					tots=__data__.TOT.make(self.home.text,self.home.tots.values())

				for tot in tots:
					output.write("Name : {0} \nTags : {1}\n".format(tot.name,str(tot.childs)))
			elif args["t"] or args["tag"]:
				tag=re.compile(tag)
				tags=filter(lambda tag__:re.search(tag,tag__),self.home.getTags())
				data=map(lambda tag__:(tag__,len(self.home.tag[self.home.find(tag__)])),tags)
				data=sorted(data,key=lambda data:data[1])
				for tag__,n in data:
					output.write("{0} {1}\n".format(tag__,n))
		elif query.command in Command.CSM:
			return CSMShell2(self.home).execQuery(Query(query.args),output)
		else:
			return self.execQuery(Query(("SELECT",*query.data)),output)
			#return super().execQuery(query,output)
	def select(self,args,output,*args__,**kwargs):
		try:
			args=docopt.docopt(Docs.DB.SELECT,args)
		except SystemExit as e:
			print(e)
			return
		#search DB by regex.
		dbid=args["<dbid>"]
		dbids=list(self.home.getDBIDs(args["<dbid>"]))
		if not dbids:
			return
		dbid=dbids[0]
		db=self.home.select(dbid,*args__,**kwargs)
		print("XXX")
		db=self.home.select(dbid,*args__,**kwargs)
		if not db:
			print("DB doesn't exist.")
			return
		try:
			self.DBShell(db).start()
		except Exception as e:
			print(e)
		db.save()
		db.close()
		print("***",self.home.id,"***")
	def append(self,args,output):
		if not args:
			output.write("Don't find dbid.\n")
			return
		if len(args)==1:
			output.write("Don't find tags.\n")
			return
		dbid=args[0].upper()
		tags=list(map(lambda tag:tag.upper(),args[1:])) if len(args)>1 else []
		if self.home.get(self.home.find(dbid)):
			output.write(dbid+" exists.\n")
			return
		#Append Tags to db.
		self.home.append(dbid,tags)
		output.write("Created {0} {1}\n".format(dbid,tags))
		self.home.save()
	def start(self):
		print("***",self.home.id,"***")
		super().start()
		self.home.close()
	#self.home=openHome()

class BaseShell3(BaseShell2):
	"""
BaseShell3 has input pipe (<) ouptut pipe (>), output add pipe (>>).
and it has alias.txt.this is execed before enter shell,as alias <line>...
	"""
	INPUT_PIPE="<"
	OUTPUT_PIPE=">"
	OUTPUT_ADD_PIPE=">>"
	OUTPUT_SH_PIPE="|"
	OUTPUT_ARGS_PIPE="||"
	INIT_ALIAS="alias.txt"
	def __init__(self,dname=None,prompt=BaseShell.PROMPT):
		super().__init__(dname,prompt)
		self.null=_pyio.StringIO()
		if self.dname:
			_util.touch(self.alias_txt)
			self.execAliasf(self.alias_txt,self.null)
	@property
	def alias_txt(self):
		if self.dname:
			return os.path.join(self.dname,self.INIT_ALIAS)
		return None
	def _begin_one_liner(self,input_,output,precmd=None,postcmd=None):
		try:
			output.flush()
			if not input_.readable():
				return 1
			line=input_.readline()
			if not line:	#reach EOF
				return 0
			query=Query.read(line)
			query,output__,close_output=self.parse_query(query)
			if not output__:
				output__=output
			res=self.execQuery(query,output__)
			if close_output:
				output__.close()
		except ExitShell:
			#0
			return 0
		except SystemExit:
			#-1
			return -1
		except ValueError:
			
			return -1
		except KeyboardInterrupt:
			pass
		except UnicodeEncodeError:
			pass
		except Exception as e:
			print(e,type(e))
		return 1
	def shell(self):
		while True:
			try:
				if not self.stdin.readable():
					return
				self.stdout.write(self.prompt)
				self.stdout.flush()
				line=self.stdin.readline()
				if not line:	#reach EOF
					return
				query=Query.read(line)
				query,output__,close_output=self.parse_query(query)
				if not output__:
					output__=self.stdout
				res=self.execQuery(query,output__)
				if close_output:
					output__.close()
			except ExitShell:
				return 0
			except SystemExit:
				return
			except ValueError:
				return 
			except Exception as e:
				print(e,type(e))
	def __parse_query__(self,query):
#res (query,output)
#output is str.
		input_=None
		output=None
		mode=""
		PIPES=(
			self.OUTPUT_PIPE,
			self.OUTPUT_ADD_PIPE,
			self.OUTPUT_SH_PIPE,
			self.OUTPUT_ARGS_PIPE
		)
		for data in query:
			if data in PIPES :
				pipe=data
				index_of_pipe=list(query).index(data)
				new_query=query[:index_of_pipe]
				if pipe == self.OUTPUT_SH_PIPE:
					output_query=query[index_of_pipe+1:]
					output=_util.QueryStream(self,output_query)
					mode=None
				elif pipe == self.OUTPUT_ARGS_PIPE:
					output_query=query[index_of_pipe+1:]
					output=_util.QueryArgsStream(self,output_query)
					mode=None
				else:
					output=query[index_of_pipe+1]
					if pipe==self.OUTPUT_PIPE:
						mode="w"
					elif pipe==self.OUTPUT_ADD_PIPE:
						mode="a"
				return (new_query,output,mode)
		return (query,output,mode)
	def parse_query(self,query,encoding="utf8"):
		query,output,mode=self.__parse_query__(query)
		close_output=False
		if output:
			if issubclass(type(output),_util.QueryStream):
				pass
			elif output.upper() == "NULL":
				output=self.null
			else:
				output=_util.realpath(output)
				output=open(output,mode,encoding=encoding)
				close_output=True
		return (query,output,close_output)
	def execAliasf(self,fname,output,encoding="sjis"):
		if not os.path.exists(fname):
			return
		with open(fname,"r",encoding=encoding) as f:
			for line in f:
				query=Query(("alias",*line.rstrip().split()))
				try:
					self.alias(query.args,output)
				except:
					pass


class BaseServerHomeShell(BaseHomeShell):
#shell for BaseServerHome
#manage db and client
	def execQuery(self,query,output):
		if query.command in Command.DB.SERVER:
			try:
				args=docopt.docopt(Docs.DB.SERVER,query.args)
			except SystemExit as e:
				print(e,query)
				return
			if args["start"]:
				for dbid in __db__.getDBIDs(self.home,args["<dbid>"]):
					if self.home.served(dbid):
						output.write("Server {0} is started.\n".format(dbid))
					else:
						if self.home.serve(dbid):
							output.write("** "+dbid+" **\n")
							output.write("Listing...\n")
						else:
							output.write("Start "+dbid+" is failed.\n")
						#sdb.serve_forever()
			elif args["stop"]:
				for dbid in __db__.getDBIDs(self.home,args["<dbid>"]):
					if self.home.served(dbid):
						self.home.stop(dbid)
						output.write("Stopped {0}\n".format(dbid))
			else:
				output.write("*** read ***\n")
				user=self.home.users["R"]
				if user.not_:
					output.write("[else]\n")
				for userid in user.data:
					output.write("-"+userid+"\n")

				output.write("*** write ***\n")
				user=self.home.users["W"]
				if user.not_:
					output.write("[else]\n")
				for userid in user.data:
					output.write("-"+userid+"\n")
		elif query.command in Command.SEARCH:
			try:
				args=docopt.docopt(Docs.DB.SEARCH,query.args)
			except SystemExit as e:
				print(e)
				return
			tags=args["<tags>"].split(",") if args["-t"] else list()
			pMode=args["<pMode>"].upper() if args["-p"] else ""
			all_=args["-a"] or args["--all"]
			if args["-u"]:
				userid=args["<userid>"] 
				host=__server__.getHost(userid)
			else:
				return super().execQuery(query,output)
			if not host:
				output.write("Can't find host.\n")
				return
			with __server__.BaseClient((host,self.HomeClass.PORT)) as c:
				text=""
				for data in c.searchDB(tags):
					dbid_=data["id"].lower()
					if dbid_.find("__")==0 and not all_:
						continue
					tags=map(lambda tag:tag.lower(),data["tags"])
					served="Served" if data["served"] else ""
					output.write("{0} => {1} {2}\n".format(dbid_,",".join(tags),served))
		else:
			return super().execQuery(query,output)
	def open_server(self):
		return self.home.open()


class HomeShell(BaseServerHomeShell):
#shell for home
	PROMPT="$"
	
	#def __init__(self,dname,HomeClass=__server__.ServerHome):
	def __init__(self,home):
		#super().__init__(dname,self.PROMPT)
		host="127.0.0.1"
		super().__init__(home,DBShell,self.PROMPT)
		try:
			self.dnsServer=__dns__.Server("127.0.0.1",self.dname)
			self.dnsServer.stop()
		except:
			self.dnsServer=None
	@property
	def id(self):
		return self.home.id
	@property
	def dns_runned(self):
		return self.dnsServer# and self.dnsServer.opened
	def execQuery(self,query,output):
		if not query:
			return
		if query.command in Command.DNS:
			if not self.dns_runned:
				print("DNS Server don't work.")
				return
			if not query.args:
				if self.dnsServer.opened:
					print(" Opened")
				else:
					print(" Closed")
				return
			query=Query(query.args)
			if query.command == "ON":
				self.dnsServer.open()
				print("DNS Server start...")
			if query.command=="OFF":
				self.dnsServer.stop()
				print("DNS Server stop.")
		elif query.command in Command.DB.SELECT:
			try:
				args=docopt.docopt(Docs.DB.SELECT,query.args)
			except SystemExit as e:
				print(e,query)
				return
			#search DB by regex.
			dbid=args["<dbid>"]
			if args["-u"]:	#connect to dbid of userid
				userid=args["<userid>"]
				with __server__.ClientU(userid) as c:
					try:
						c.connect(dbid)
						if not c.connected:
							output.write("Ca't connect "+dbid+"\n")
							return
						ClientShell(c).start()
					except Exception as e:
						print(e)
			else:
				super().execQuery(query,output)
		elif query.command in Command.DB.CONNECT:
			if len(query.args)<2:
				return
			host=query.args[0]
			dbid=query.args[1]
			with __server__.Client(host) as c:
				c.connect(dbid)
				if not c.connected:
					print("Ca't connect",dbid)
					return
				for res in clientShell(c):
					if res:
						print(res)
			print("***",self.home.id,"***")
		elif query.command in Command.QUIT:
			raise ExitShell
		else:
			return super().execQuery(query,output)
	def start(self):
		res=super().start()
		self.close()
		return res
	def close(self):
		try:
			self.home.close()
		except Exception as e:
			self.stdout.write(str(e)+"\n")
			self.home.save()
		if self.dnsServer:
			self.dnsServer.close()
		
def loadHome(dname,host="127.0.0.1"):
	homeDB=__server__.ServerHome(dname,host)
	return HomeShell(homeDB)

class HomeLoader(BaseShell):	#select you use whitch home.
#like bootloader
	KEY_SEQ=":"
	DEFAULT_HOME_ID="MAIN"
	DEFAULT_HOME_SHELL=HomeShell
	DEFAULT_LOADER=loadHome
	PROMPT="="
	class Command:
		LOAD=("LO","LOAD")
	def __init__(self,dname):
		super().__init__(dname,self.PROMPT)
		self.conf=self.Conf(self.dname)
		if not self.get(self.DEFAULT_HOME_ID):
			self.conf[self.Conf.Key.HOME][self.DEFAULT_HOME_ID]=self.default_home()
		os.environ[EnvKey.LOADER_HOME]=self.dname
	def default_home(self):
		return HomeLoader.DEFAULT_LOADER(os.path.join(self.dname,self.DEFAULT_HOME_ID))
	def get(self,homeid):
		return self.conf[self.Conf.Key.HOME].get(homeid)
	def listHome(self):
		return self.conf[self.Conf.Key.HOME].keys()
	def load(self,homeid):
		home=self.get(homeid)
		if home:
			home.start()
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			print("""
	ls
	load <homeid>
			""")
		elif query.command in self.Command.LOAD:
			if not query.args:
				print("Don't find homeid.")
				return
			homeid=query.args[0].upper()
			self.load(homeid)
		elif query.command in Command.DB.LS:
			for homeid in self.listHome():
				print(homeid)
		else:
			return super().execQuery(query,output)
			

	def start(self):
		super().start()
		self.close()
	def close(self):
		for home in self.conf[self.Conf.Key.HOME].values():
			home.close()

	class Conf:
		CONF_FILE="loader.conf"
		class Key:
			PATH="PATH"
			SET="SET"
			HOME="home"
		def __init__(self,dname):
			self.dname=_util.realpath(dname)
			self.confFile=os.path.join(self.dname,self.CONF_FILE)
			_util.touch(self.confFile)
			self.data=self.read(self.confFile)
		def __getattr__(self,attr):
			return getattr(self.data,attr)
		def __iter__(self):
			return iter(self.data)
		def __getitem__(self,key):
			return self.data[key]
		def __setitem__(self,key,value):
			self.data[key]=value
		def __str__(self):
			return str(self.data)
		def read(self,fname):
			Key=HomeLoader.Conf.Key
			conf={Key.HOME:{}}
			sys.path.append(self.dname)
			with open(fname,"r") as f:
				for line in f:
					line=line.rstrip().split(HomeLoader.KEY_SEQ,1)
					key=line[0].upper()
					value=line[1] if len(line)>1 else ""
					if key==Key.PATH:
						if value:
							sys.path.append(_util.realpath(value))
							#dname,fname=os.path.split(value)
							#sys.path.append(dname)
					elif key==Key.SET:
						if value.find(" ") == -1:
							continue
						key,value=value.split(" ",1)
						os.environ[key]=os.path.expandvars(value)
					else:
						homeid=key
						data=value.split(",")
						module_name=data[0]
						args=data[1:] if len(data)>1 else []
						if not module_name:
							home=HomeLoader.DEFAULT_LOADER(os.path.join(self.dname,homeid),*args)
						else:
							if " " in module_name:
								from_,module_name=module_name.split(" ",1)
								if not sys.modules.get(module_name):
									exec("from {0} import {1}".format(from_,module_name))
								module_name=from_+"."+module_name
							elif not sys.modules.get(module_name):
								print("XXX",key,value)
								exec("import "+module_name)
							home=sys.modules[module_name].loadHome(os.path.join(self.dname,homeid),*args)
						if hasattr(home,"open_server"):
							home.open_server()
						conf[Key.HOME][home.id]=home
			return conf
						

