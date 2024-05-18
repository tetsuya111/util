from kyodaishiki import __shell__
from kyodaishiki import __data__
from kyodaishiki import _util
from . import select2
from . import util
import os
import docopt
import _pyio
import pykakasi
import re
import datetime
import sys
import subprocess as sp
import random
import shutil


class Attr(util.Attr):
	DNAME="DNAME"

class Tag:
	IS_DIR="ISDIR"
	IS_FILE="IS_FILE"
	IS_FULL="IS_FULL"

def write_shell(output=sys.stdout):
	output.write("Fname:")
	fname=input()
	tags=_util.inputUntilSeq(text="Tags:",output=output)
	return __data__.CSM(fname,tags=tags,date=str(datetime.datetime.now()))

class Docs:
	WRITE="""
	Usage:
		write (f|file)
		write tot
		write
	"""
	SEARCH="""
	Usage:
		search  [(-t <tags>)] [(--nt <noTags>)] [(-m <memo>)] [(--mm <lowUpMemo>)] [(-c <comment>)] [(-d <dname>)] [(-p <pMode>)] [(--pn|--printNot)] [(-r|--random)]
	"""
	APPEND="""
	Usage:
		append dir [(-d <dname>)] [(-t <tags>)] [(-f <fname>)] [(--dp <depth>)] [--full] [(-O|--oveerride)]
		append tag (s|search) <searchArgs> <tagsToAppend>...
		append tag [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)] <tagsToAppend>...
	"""
	REMOVE="""
	Usage:
		remove memo [(-d <dname>)]
		remove tag [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)] <removedTags>...
		remove tot [<tag>]
		remove (f|file) [(-t <tags>)] [(-m <memo>)] [(-d <dname>)]
		remove clean [(-t <tags>)] [(-m <memo>)] [(-d <dname>)]
		remove [(-t <tags>)] [(-m <memo>)] [(-u <userid>)] [(-D <dbid>)]
	"""
	VIM="""
	Usage:
		vim (af|asfile) [(-t <tags>)] [(-m <memo>)] [(-d <dname>)] [(-n <number>)] [(-r|--random)]
		vim (f|file) <fname>
		vim tot [(-t <tag>)] [(-r|--random)]
		vim [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)] [(-n <number>)] [(-d <dname>)] [(-r|--random)]
	"""
	VLC="""
	Usage:
		vlc <fname> [(-d <dname>)]
		vlc (s|search) <searchArgs>... 
		vlc [(-t <tags>)] [(-m <memo>)] [(--mm <lowUpMemo>)] [(-d <dname>)] [(-n <number>)] [(-r|--random)]
	"""
	MOVE="""
	Usage:
		move [(-t <tags>)] [(-m <memo>)] [(-d <dname>)] <dnameToMoveTo>
	"""
	HELP="""
		write
		append 
		vlc
		vim
	"""

class Command(select2.Command):
	VLC=["VLC"]
	CURDIR=("CD","CUR","CURDUR")
	MOVE=("MV","MOVE")

class DBShell(select2.DBShell):
	VLC_MAX=20
	def __init__(self,db,dname=".",environ={}):
		self.cur_dname=_util.realpath(dname) if dname else ""
		super().__init__(db,environ=environ)
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
			if query.args and query.args[0] in ("-a","--all"):
				return super().execQuery(query,output)
		elif query.command in Command.CURDIR:
			output.write(self.cur_dname+"\n")
		elif query.command in Command.WRITE:
			try:
				args=docopt.docopt(Docs.WRITE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["f"] or args["file"]:
				csm=write_shell()
				self.db.appendCSM(csm)
				self.db.save()
			else:
				return super().execQuery(query,output)
		elif query.command in Command.SEARCH:
			try:
				args=docopt.docopt(Docs.SEARCH,query.args)
			except SystemExit as e:
				print(e)
				return
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			if args["-d"]:
				dname=args["<dname>"]
				dname=re.escape(dname)+".*"
				tags.append(Attr(Attr.DNAME)(dname))
			noTags=args["<noTags>"] if args["--nt"] else []
			if args["--pn"] or args["--printNot"]:
				noTags.append(select2.NOT)
			memo=args["<memo>"] if args["-m"] else ""
			if args["--mm"]:
				memo=select2.addlowUp(memo,args["<lowUpMemo>"])
			comment=args["<comment>"] if args["-c"] else ""
			pMode=args["<pMode>"].upper()+"M" if args["-p"] else "M"
			random_=args["-r"] or args["--random"]
			cards=self.db.search(memo,tags)
			if random_:
				cards=list(cards)
				random.shuffle(cards)
			else:
				cards=sorted(cards,key=lambda card:card.date)
			text=""
			for csm in __data__.CSM.make(self.db.text,cards):
				if not comment or re.search(comment,csm.comment):
					text+=csm.dump(pMode)+"\n"
					text+="-"*50+"\n"
			output.write(text)
		elif query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["dir"]:
				dname=args["<dname>"] if args["-d"] else self.cur_dname
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				tags=(*tags,Tag.IS_FILE)
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
						self.db.append(fname,tags=tags__,date=str(datetime.datetime.now()))
						output.write("Append {0}".format(fname)+"\n")
				self.db.save()
			else:
				return super().execQuery(query,output)
		elif query.command in Command.REMOVE:
			try:
				args=docopt.docopt(Docs.REMOVE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["f"] or args["file"]:
				memo=args["<memo>"] if args["-m"] else ""
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				if args["-d"]:
					dname=args["<dname>"]
					dname=Attr(Attr.DNAME)(re.escape(dname))+".*"
					tags.append(dname)
				else:
					dname=""
				if not (memo and tags):
					output.write("Yout try to remove all cards.OK ? (y/n) : ")
					y_n=input().upper()
					if y_n != "Y":
						return
				tags.append(Tag.IS_FILE)
				for card in list(self.db.search(memo,tags)):
					fname=card.memo(self.db.text)
					dname__=Attr.get(card.tags(self.db.text),Attr.DNAME)
					if dname__:
						fname=os.path.join(dname__[0],fname)
					elif dname:
						fname=os.path.join(dname,fname)
					try:
						if os.path.isdir(fname):
							shutil.rmtree(fname)
						else:
							os.remove(fname)
					except Exception as e:
						output.write(str(e)+"\n")
					self.db.remove(card.id)
					output.write("Remove {0}\n".format(fname))
			elif args["clean"]:
				memo=args["<memo>"] if args["-m"] else ""
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				tags.append(Tag.IS_FILE)
				if args["-d"]:
					dname=args["<dname>"]
					dname=Attr(Attr.DNAME)(re.escape(dname))+".*"
					tags.append(dname)
				else:
					dname=""
				for card in list(self.db.search(memo,tags)):
					fname=card.memo(self.db.text)
					dname__=Attr.get(card.tags(self.db.text),Attr.DNAME)
					if dname__:
						fname=os.path.join(dname__[0],fname)
					elif dname:
						fname=os.path.join(dname,fname)
					if not os.path.exists(fname):
						self.db.remove(card.id)
						output.write("Remove card of {0}\n".format(fname))
			else:
				return super().execQuery(query,output)
		elif query.command in Command.VIM:
			try:
				args=docopt.docopt(Docs.VIM,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["af"] or args["asfile"]:
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				tags=(*tags,Tag.IS_FILE)
				memo=args["<memo>"] if args["-m"] else ""
				dname=args["<dname>"] if args["-d"] else self.cur_dname
				max_=int(args["<number>"]) if args["-n"] else self.VIM_MAX
				cards=self.db.search(memo,tags)
				fnames=[]
				for card in cards:
					dname=Attr.get(card.tags(self.db.text),Attr.DNAME,[dname])[0]
					fnames.append(os.path.join(dname,card.memo(self.db.text)))
				random_=args["-r"] or args["--random"]
				if len(fnames) > max_:
					fnames=fnames[:max_]
				if random_:
					random.shuffle(fnames)
				sp.call(["vim","-Z",*fnames])
			else:
				return super().execQuery(query,output)
		elif query.command in Command.VLC:
			try:
				args=docopt.docopt(Docs.VLC,query.args)
			except SystemExit as e:
				print(e)
				return
			dname=args["<dname>"] if args["-d"] else self.cur_dname
			if args["<fname>"]:
				fnames=[args["<fname>"]]
			elif args["s"] or args["search"]:
				searchArgs=util.arg_replace(args["<searchArgs>"])
				searchArgs=list(searchArgs)
				cards=self.execQuery(__shell__.Query(("search_card",*searchArgs)),output)
				def s_getfnames(cards):
					for card in cards:
						fname=os.path.join(Attr.get(card.tags(self.db.text),Attr.DNAME,[dname])[0],card.memo(self.db.text))
						yield fname
				fnames=s_getfnames(cards) if cards else []
			else:
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				tags=(*tags,Tag.IS_FILE)
				memo=args["<memo>"] if args["-m"] else ""
				if args["--mm"]:
					memo=select2.addlowUp(memo,args["<lowUpMemo>"])
				random_=args["-r"] or args["--random"]
				max_=int(args["<number>"]) if args["-n"] else self.VLC_MAX
				cards=list(self.db.search(memo,tags=tags))
				if len(cards) > max_:
					cards=cards[:max_]
				if random_:
					random.shuffle(cards)
				fnames=[]
				for card in cards:
					fname=os.path.join(Attr.get(card.tags(self.db.text),Attr.DNAME,[dname])[0],card.memo(self.db.text))
					fnames.append(fname)

			fnames=list(map(lambda fname:os.path.join(dname,fname),fnames))
			if fnames:
				sp.Popen(("vlc",*fnames))
		elif query.command in Command.MOVE:
#move [(-t <tags>)] [(-m <memo>)] <dnameToMoveTo>
			try:
				args=docopt.docopt(Docs.MOVE,query.args)
			except SystemExit as e:
				print(e)
				return
			memo=args["<memo>"] if args["-m"] else ""
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			tags.append(Tag.IS_FILE)
			if args["-d"]:
				dname=_util.realpath(args["<dname>"]).upper()
				dname=re.escape(dname)+".*"
				tags.append(Attr(Attr.DNAME)(dname))
			print(tags)
			dst=_util.realpath(args["<dnameToMoveTo>"])
			if not os.path.exists(dst):
				os.makedirs(dst)
			dstTag=Attr(Attr.DNAME)(dst)
			for card in list(self.db.search(memo,tags)):
				fname=card.memo(self.db.text)
				src=Attr.get(card.tags(self.db.text),Attr.DNAME)[0]
				self.db.removeTags(card.id,map(lambda dname:Attr(Attr.DNAME)(src),src))
				self.db.appendTags(card.id,[dstTag])
				shutil.move(os.path.join(src,fname),os.path.join(dst,fname))
				output.write("Move  {0} from {1} to {2}\n".format(fname,src,dst))

		else:
			return super().execQuery(query,output)

class DUShell(__shell__.BaseShell):
	PROMPT=">>"
	DB_SHELL=DBShell
	def __init__(self,dushell):
		super().__init__(prompt=self.PROMPT)
		self.DBShell=DBShell
		self.homeDB=dushell.homeDB
		self.environ={}
	def execQuery(self,query,output):
		dbid=query.command.upper()
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
			shell=self.DB_SHELL(db,dname,environ=self.environ)
			shell.execAliasf(alias_txt,_pyio.StringIO())
			shell.start()
		except Exception as e:
			output.write(str(e)+"\n")
	def start(self):
		return self.execQuery(__shell__.Query(),self.stdout)


