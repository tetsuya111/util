from kyodaishiki import __data__
from kyodaishiki import _util
from kyodaishiki import __server__
from kyodaishiki import __shell__
from kyodaishiki import __db__
from . import augment_hs
from . import augment_hs3
from . import util
import docopt
import os
import subprocess as sp
import shutil
import re
import copy
import random
import sys
import datetime

DEFAULT_DUMP_HOME_DIR=_util.realpath("%USERPROFILE%\\desktop\\dumpedHome")
DEF_BACKUP_DIR=_util.realpath("%USERPROFILE%\\desktop\\buckeupedHome2")
DEFAULT_DUMP_TAG_FNAME=_util.realpath("%USERPROFILE%\\desktop\\dumpedtag.csm")
DEFAULT_CSM_DIR_F=lambda db_dname:r"{0}\csmFiles".format(_util.realpath(db_dname))
DEFAULT_DUMP_CSM_DIR_F=_util.realpath(r"%USERPROFILE%\desktop\util_dumped_db")
BACKUP="BACKUP"

TMP=lambda:random.randint(10**24,10**36)

def ishome(db):
	return issubclass(type(db),augment_hs3.ServerHome)

class Data(util.Data):
	class Home(util.Data.Home):
		DB_TAG_FILE="db_tag.txt"
		IS_HOME_F="is_home.xxx"
		#data directory instead of db.
		def __init__(self,dname):
			self.dname=dname
		def dumpDB(self):
			for fname in os.listdir(self.dname):
				fullname=os.path.join(self.dname,fname)	#DB dname
				if os.path.isdir(fullname):
					if Data.Home.ishome(fullname):
						yield Data.Home(fullname)
					else:
						yield Data.DB(fullname)
		@staticmethod
		def ishome(dname):
			return os.path.exists(os.path.join(dname,Data.Home.IS_HOME_F))
		@staticmethod
		def tohome(dname):
			with open(os.path.join(dname,Data.Home.IS_HOME_F),"w") as f:
				pass
							
		@staticmethod
		def make(homeDB,dstDname):
			dstDname=_util.realpath(dstDname)
			if os.path.exists(dstDname):
				return None
			os.makedirs(dstDname)
			for db in homeDB.dumpDB():
				db_dname=os.path.join(dstDname,db.id)
				if ishome(db):
					Data.Home.make(db,db_dname)
				else:
					os.makedirs(db_dname)
					for csm in db.dumpCSM():
						csm.write(os.path.join(db_dname,csm.fname))
					for tot in db.dumpTOT():
						tot.write(os.path.join(db_dname,tot.fname))
			with open(os.path.join(dstDname,Data.Home.DB_TAG_FILE),"w") as f:
				text=Data.Home.makeDBTagText(homeDB)
				f.write(text)
			Data.Home.tohome(dstDname)
			return Data.Home(dstDname)


def getTreeData(home):
	res=util.Category(home.id)
	for dbcard in home.listDB():
		dbid=dbcard.getID(home.text)
		if dbcard.ishome:
			db=home.select(dbid)
			data=getTreeData(db)
			res.childs.append(data)
		else:
			res.cols.append(dbid)
	return res


class Docs:
	APPEND="""
	Usage:
		append home data (-d <dname>) [(--dt <dbTags>)]
		append home [(-d <dname>)] 
	"""
	DUMP="""
	Usage:
		dump tag <dbid> [(-f <fname>)]
		dump home [(-d <dname>)]
		dump <dbid> [(-d <dname>)]
	"""
	RENAME="""
	Usage:
		rename <srcid> <dstid>
	"""
	COPY="""
	Usage:
		copy home (-d <dname>)
		copy db <dbid> (-d <dname>)
		copy <srcid> <dstid> [(-O|--override)]
	"""
	TREE="""
	Usage:
		tree
	"""

class Command(util.Command):
	APPEND=("A","APPEND")
	DUMP=("D","DUMP")
	TREE=["TREE"]

HELP="""
	$ append
	$ dump
	$ rename
	$ copy
	$ backup
	$ tree
"""




class AuHSShell(__shell__.BaseShell3):
	PROMPT=">>"
	DNAME="_util"
	def __init__(self,home):
		self.homeDB=home.home
		dname=os.path.join(home.dname,self.DNAME)
		super().__init__(dname=dname,prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in _util.Command.HELP:
			output.write(HELP+"\n")
		elif query.command in _util.Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["data"]:
				if args["home"]:
					dname=_util.realpath(args["<dname>"])
					dbid=os.path.split(dname)[1]
					shutil.copytree(dname,os.path.join(self.homeDB.dname,dbid))
					self.homeDB.append(dbid,["HOME","_UTIL"],True)
			elif args["home"]:
				try:
					dname=args["<dname>"] if args["-d"] else DEFAULT_DUMP_HOME_DIR
					dname=_util.realpath(dname)
					srcHome=Data.Home(dname)
					self.homeDB.append(srcHome.id,["UTIL","HOME"],True)
					dstHome=self.homeDB.select(srcHome.id)
					for src in srcHome.dumpDB():
						try:
							if dstHome.select(src.id):
								print(src.id,"already exists.")
							dstHome.append(src.id,[],ishome(src))
							dst=dstHome.select(src.id)
							if ishome(src):
								for db_dname in src.listDB():
									return AuHSShell(dst).execQuery(_util.Query(["append","home","-d",db_dname]),output)
							else:
								for csm in src.csms:
									dst.appendCSM(csm)
								for tot in src.tots:
									dst.appendTOT(tot.name,tot.childs)
							dst.save()
						except Exception as e:
							print(e,src.id)
					dstHome.save()
					self.homeDB.save()
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
				if Data.Home.make(self.homeDB,dname):
					print("Dump to",dname)
				else:
					print(dname,"already exists.")
					return
		elif query.command in Command.RENAME:
			try:
				args=docopt.docopt(Docs.RENAME,query.args)
			except SystemExit as e:
				print(e)
				return
			srcid=args["<srcid>"].upper()
			dstid=args["<dstid>"].upper()
			srcid=self.homeDB.getDBID(srcid)
			if not srcid:
				print("srcid does'nt be found.",file=output)
				return
			src_path=os.path.join(self.homeDB.dname,srcid)
			dst_path=os.path.join(self.homeDB.dname,dstid)
			src_card=self.homeDB.get(self.homeDB.find(srcid))
			ishome=src_card.type == augment_hs3.Index.DB.Type.HOME
			tags=list(map(lambda tagIdx:tagIdx.get(self.homeDB.text),self.homeDB.cardToTags.get(src_card.id,[])))
			os.rename(src_path,dst_path)
			self.homeDB.remove(srcid)
			self.homeDB.append(dstid,tags,ishome)
			output.write("Rename {0} to {1}\n".format(srcid,dstid))
		elif query.command in Command.COPY:
			return util.Shell(self.homeDB).execQuery(query,output)
		elif query.command in Command.BACKUP:
			if "home" in query and "-d" not in query:
				query.extend(("-d",DEF_BACKUP_DIR))
			return util.Shell(self.homeDB).execQuery(query,output)
		elif query.command in Command.TREE:
			data=getTreeData(self.homeDB)
			print(data,file=output)
		else:
			return super().execQuery(query,output)

	def start(self):
		self.stdout.write("*** welcome to shell for util! ***\n")
		return super().start()



