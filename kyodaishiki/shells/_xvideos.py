from kyodaishiki import _util
from kyodaishiki import __data__
from kyodaishiki import __shell__
from . import _file
from . import util
from . import select2

import sys
import myutil

#XVIDEOS_PATH=r"C:\Users\tetsu\code\av\xvideos"
#myutil.importPackage(XVIDEOS_PATH)

import xvideos.manage
import xvideos.file
import xvideos.util


import os
import re
import docopt
import datetime
import _pyio
import random

class Tag(_file.Tag):
	IS_XMOVIE="IS_XMOVIE"

class Attr(_file.Attr):pass

def getTags(db,fname):
	data=xvideos.file.getDataByFname(db,fname)
	if data:
		data_tags=data["tag"]
		data_janres=data["janre"]
		words=xvideos.util.Mecab.getWords(data["title"])
		for a in (*data_tags,*data_janres,*words):
			try:
				a.encode("cp932")
				yield a
			except Exception as e:
				print(e,a)
				pass
	return []

class Docs:
	APPEND="""
	Usage:
		append (l|list) <listPath> [(-t <tags>)] [(-O|--oveerride)]
		append dir [(-d <dname>)] [(-t <tags>)] [(-f <fname>)] [(--dp <depth>)] [--full] [(-O|--oveerride)]
		append tag (x|xtags) [(-t <tags>)] [(-m <memo>)]
		append tag (s|search) <searchArgs> <tagsToAppend>...
		append tag [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)] <tagsToAppend>...
	"""
	SEARCH="""
	Usage:
		search (x|xvideos) [(--at|--astitle|--al|--aslist)] [(-r|--random)] [<searchArgs>...]
		search  [(-t <tags>)] [(--nt <noTags>)] [(-m <memo>)] [(--mm <lowUpMemo>)] [(-c <comment>)] [(-d <dname>)] [(-p <pMode>)] [(--pn|--printNot)] [(-r|--random)]
	"""
	GET="""
	Usage:
		get [(--at|--astitle|--al|--aslist)] [(-r|--random)] [<searchArgs>...]
	"""
	DOWNLOAD="""
	Usage:
		download (i|image) [(-d <dname>)] [<searchArgs>...]
		download [(-d <dname>)] [<searchArgs>...]
	"""
	MANAGE="""
	Usage:
		manage [<query>...]
	"""
	FILE="""
	Usage:
		file [<query>...]
	"""
	HELP="""
	Usage:
		search
		append 
		manage
		file
	"""

	MAIN="""
	Usage:
		_xvideos <dbid> [(-x <xdb_dname>)]
	"""

class Command(_file.Command):
	DOWNLOAD=("DW","DOWNLOAD")
	MANAGE=("MA","MANAGE")
	FILE=("F","FILE")
	GET=("G","GET")
class DBShell(_file.DBShell):
	DEF_DOWNLOAD_DIR=r"%USERPROFILE%\Desktop\xmovieDownloadedVideos"
	def __init__(self,db,dname=".",environ={},xdb_dname=xvideos.manage.DEF_DB_DIR):
		super().__init__(db,dname,environ)
		xdb_dname=_util.realpath(xdb_dname)
		if os.path.exists(xdb_dname):
			self.xdb=xvideos.util.DB(xdb_dname)
		else:
			self.xdb=None
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			print(Docs.HELP,file=output)
		elif query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["l"] or args["list"]:
				listPath=_util.realpath(args["<listPath>"])
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				dname,_=os.path.split(listPath)
				override=args["-O"] or args["--oveerride"]
				with open(listPath,"r") as f:
					for url in map(lambda line:line.rstrip(),f):
						id_=xvideos.manage.getID(url)
						data=xvideos.manage.getDataByID(self.xdb,id_)
						if not data:
							continue
						fname=str(id_)+".mp4"
						tags__=(Attr(Attr.DNAME)(dname),Tag.IS_XMOVIE,Tag.IS_FILE,*getTags(self.xdb,fname))
						self.db.append(fname,"",(*tags,*tags__),str(datetime.datetime.now()).split(".")[0])

			elif args["dir"]:
				dname=args["<dname>"] if args["-d"] else self.cur_dname
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				tags=(*tags,_file.Tag.IS_FILE)
				fname_pattern=args["<fname>"] if args["-f"] else "^.+$"
				depth=int(args["<depth>"]) if args["--dp"] else 0
				override=args["-O"] or args["--oveerride"]
				#full=(dname!=self.cur_dname) or args["--full"]
				full=args["--full"]
				text=""
				default_depth=dname.count("\\")
				for cur,ds,fs in os.walk(dname):
					if cur.count("\\") > depth+default_depth:
						continue
					cur=_util.realpath(cur)
					for fname in ds+fs:
						if not re.fullmatch(fname_pattern,fname):
							continue
						tags__=[*tags,Attr(Attr.DNAME)(cur)]
						if full:
							fname=os.path.join(cur,fname)
							tags__.append(Tag.IS_FULL)
						if os.path.isdir(os.path.join(cur,fname)):
							tags__.append(Tag.IS_DIR)
						try:
							fname.encode("cp932")
						except Exception as e:
							print("Encode error",fname,cur)
							continue
						#####
						if self.xdb:
							xtags=getTags(self.xdb,fname)
							tags__=(*tags__,Tag.IS_XMOVIE,*xtags)
						#####
						self.db.append(fname,tags=tags__,date=str(datetime.datetime.now()),override=override)
						output.write("Append {0}".format(fname)+"\n")
			elif args["tag"]:
				if args["x"] or args["xtags"]:
					memo=args["<memo>"] or ""
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					cards=self.db.search(memo,tags)
					for card in list(cards):
						fname=card.memo(self.db.text)
						tags=list(getTags(self.xdb,fname))
						self.db.appendTags(card.id,tags)
						print("Append ",tags," to ",fname,file=output)

				else:
					return super().execQuery(query,output)
			else:
				return super().execQuery(query,output)
		elif query.command in Command.GET:
			try:
				args=docopt.docopt(Docs.GET,query.args)
			except SystemExit as e:
				print(e)
				return
			searchArgs=args["<searchArgs>"]
			up,_,low=util.partitionArgs(searchArgs,("--at","--astitle","--al","--aslist"))
			searchArgs=low if low else up
			searchArgs=list(util.arg_replace(searchArgs))
			aslist=args["--al"] or args["--aslist"]
			astitle=args["--at"] or args["--astitle"]
			random_=args["-r"] or args["--random"]
			if "-t" in searchArgs:
				i=searchArgs.index("-t")+1
				searchArgs[i]=searchArgs[i]+","+Tag.IS_XMOVIE
			cards=self.search_card(searchArgs,output)
			if not cards:
				return
			if random_:
				cards=list(cards)
				random.shuffle(cards)
			else:
				cards=sorted(cards,key=lambda card:card.date)
			sio=_pyio.StringIO()
			for card in cards:
				fname=card.memo(self.db.text)
				data=xvideos.file.getDataByFname(self.xdb,fname)
				if not data:
					continue
				if aslist:
					print(data["url"],file=sio)
				elif astitle:
					print("*",data["title"],file=sio)
					print("-"*50,file=sio)
				else:
					print("\tfname:",fname,file=sio)
					print(xvideos.manage.dumpDataS(data),file=sio)
					print("-"*50,file=sio)
			sio.seek(0)
			print(sio.read(),file=output)
		elif query.command in Command.DOWNLOAD:
			try:
				args=docopt.docopt(Docs.DOWNLOAD,query.args)
			except SystemExit as e:
				print(e)
				return
#download (l|list) <listPath> [(-d <dname>)]
#download (i|image) (l|list) <listPath> [(-d <dname>)]
			dname=args["<dname>"] or self.DEF_DOWNLOAD_DIR
			dname=_util.realpath(dname)
			searchArgs=list(util.arg_replace(args["<searchArgs>"]))
			if not searchArgs:
				yn=""
				print("You try try to download all cards.OK? (y/n...) : ",end="",file=output)
				yn=input().upper()
				if yn!="Y":
					return
			if "-t" in searchArgs:
				i=searchArgs.index("-t")+1
				searchArgs[i]=searchArgs[i]+","+Tag.IS_XMOVIE
			else:
				searchArgs=("-t",Tag.IS_XMOVIE,*searchArgs)
			cards=self.execQuery(__shell__.Query(("search_card",*searchArgs)),output)
			tmp=util.TMPF("w+")
			for card in cards:
				fname=card.memo(self.db.text)
				data=xvideos.file.getDataByFname(self.xdb,fname)
				print(data["url"],file=tmp)
			tmp.seek(0)
			#print(tmp.read())
			shell=xvideos.file.Shell(self.xdb,driver=False)
			fname=tmp.fname
			if args["i"] or args["image"]:
				shell.execQuery(__shell__.Query(("download","image","list",fname,"-d",dname)),output)
			else:
				shell.execQuery(__shell__.Query(("download","list",fname,"-d",dname)),output)
			tmp.close()
		elif query.command in Command.MANAGE:
			if not self.xdb:
				raise Exception("xdb don't be setteed.")
			try:
				args=docopt.docopt(Docs.MANAGE,query.args)
			except SystemExit as e:
				print(e)
				return
			shell=xvideos.manage.Shell(self.xdb,driver=False)
			if args["<query>"]:
				query=__shell__.Query(util.arg_replace(args["<query>"]))
				shell.execQuery(query,output)
			else:
				print("***","manage","***")
				shell.start()
		elif query.command in Command.FILE:
			if not self.xdb:
				raise Exception("xdb don't be setteed.")
			try:
				args=docopt.docopt(Docs.FILE,query.args)
			except SystemExit as e:
				print(e)
				return
			shell=xvideos.file.Shell(self.xdb)
			if args["<query>"]:
				query=__shell__.Query(util.arg_replace(args["<query>"]))
				shell.execQuery(query,output)
			else:
				print("***","file","***")
				shell.start()
		else:
			return super().execQuery(query,output)
	def close(self):
		super().close()
		self.xdb.close()

class DUShell(_file.DUShell):
	DB_SHELL=DBShell
	PROMPT=">>"
	def execQuery(self,query,output):
		try:
			args=docopt.docopt(Docs.MAIN,query.data)
		except SystemExit as e:
			print(e)
			return
		dbid=args["<dbid>"].upper()
		xdb_dname=args["<xdb_dname>"] or xvideos.manage.DEF_DB_DIR
		dbids=list(self.homeDB.getDBIDs(dbid))
		if not dbids:
			output.write("Select dbid.\n")
			return
		dbid=dbids[0]
		db=self.homeDB.select(dbid)
		if not db:
			output.write("Don't find {0}.\n".format(dbid.lower()))
			return
		tags=list(map(lambda tagIdx:tagIdx.get(self.homeDB.text),self.homeDB.cardToTags[self.homeDB.find(dbid)]))
		dnames=Attr.get(tags,Attr.DNAME)
		dname=dnames[0] if dnames else ""
		alias_txt=os.path.join(self.homeDB.dname,select2.AuHSShell.ALL_ALIAS_TXT)
		try:
			shell=self.DB_SHELL(db,dname,environ=self.environ,xdb_dname=xdb_dname)
			shell.execAliasf(alias_txt,_pyio.StringIO())
			shell.start()
		except Exception as e:
			output.write(str(e)+"\n")
	def start(self):
		return self.execQuery(__shell__.Query(),self.stdout)


