import sys
sys.path.append("C:\\Users\\tetsu\\code\\kyodaishiki2")

import docopt
import re
import os
from kyodaishiki import _util
from kyodaishiki import __data__
from kyodaishiki import __shell__
from kyodaishiki import __db__
from . import util
from . import augment_hs
from . import mecab
import copy
import _pyio
import subprocess as sp
import random
import shutil
import datetime
import crayons
import colorama
import winshell

class Attr(util.Attr):
	DBID="DBID"
	USERID="USERID"


NOT="__NOT__"


TMP=lambda:str(random.randint(10**25,10**35))+".tmp"


def grep(s,reg):
	reg=re.compile(reg)
	for line in s.split("\n"):
		if re.search(reg,line):
			yield line

def getMemo(dname):
	for fname in os.listdir(dname):
		if not ".csm" in fname:
			continue
		fname=os.path.join(dname,fname)
		csm=__data__.CSM.read(fname)
		if not __data__.TOT.isTOT(csm):
			yield csm.memo

def writeW(output=sys.stdout):
	csm=__shell__.Shell.write()
	def getWords(text):
		for word,data in mecab.Mecab.__analize__(text):
			if word=="EOS" or (data and "\\xe3\\x80\\x82" in str(word.encode())):
				continue
			if b'\xe5\x90\x8d\xe8\xa9\x9e'.decode() in data[0]:
				yield word
	csm.tags=(*csm.tags,*set(getWords(csm.memo)))
	return csm

def addlowUp(base,s):
	return util.addMemo(base,util.tolowUp(s))
	
def writeShell():
	memo_text="{0} : ".format(b'\xe3\x83\xa1\xe3\x83\xa2'.decode())
	memo="\n".join(_util.inputUntilSeq(memo_text))
	comment_text="{0} : ".format(b'\xe3\x82\xb3\xe3\x83\xa1\xe3\x83\xb3\xe3\x83\x88'.decode())
	comment="\n".join(_util.inputUntilSeq(comment_text))
	tags=list(_util.inputUntilSeq("{0} : ".format(b'\xe3\x82\xbf\xe3\x82\xb0'.decode())))
	date=str(datetime.datetime.now()).split(".")[0]
	return __data__.CSM(memo,comment,tags,date)

def iscrayon(f):
	return type(f) is colorama.ansitowin32.StreamWrapper


class Docs:
	class CSM:
		WRITE="""
		Usage:
			write tot [(-t <tag>)] [(-d <dname>)]
			write csm [(-t <tags>)] [(-m <memo>)] [(-d <dname>)]
			write [(-d <dname>)]
			
		"""
		APPEND="""
		Usage:
			append tot [(-e|--edit)] [(-O|--override)] [(-t <tag>)] [(-d <dname>)]
			append csm [(-e|--edit)] [(-O|--override)] [(-t <tags>)] [(-m <memo>)] [(-d <dname>)] 
			append [(-d <dname>)] [(-O|--override)] [(-r|--rec)]
		"""
		REMOVE="""
		Usage:
			remove
		"""
#"append" is for original execQuery.
	WRITE="""
	Usage:
		write tot
		write (w|word)
		write
	"""

	SEARCH="""
	Usage:
		search (n|not) [(-t <tags>)] [(--nt <noTags>)] [(-m <memo>)] [(--mm <lowUpMemo>)] [(--em <escapedMemo>)] [(-c <comment>)] [(-F <from>)] [(-U <until>)] [(-u <userid>)] [(-D <dbid>)] [(-p <pMode>)] [(-r|--random)]
		search [(-t <tags>)] [(--nt <noTags>)] [(-m <memo>)] [(--mm <lowUpMemo>)] [(--em <escapedMemo>)] [(-c <comment>)] [(-F <from>)] [(-U <until>)] [(-u <userid>)] [(-D <dbid>)] [(--pn|--printNot)] [(-p <pMode>)] [(-r|--random)]
	"""
	SEARCH_CARD="""
	Usage:
		search_card [(-t <tags>)] [(--nt <noTags>)] [(-m <memo>)] [(--mm <lowUpMemo>)] [(--em <escapedMemo>)] [(-c <comment>)] [(-F <from>)] [(-U <until>)] [(-u <userid>)] [(-D <dbid>)] [(--pn|--printNot)]
	"""
	LIST="""
	Usage:
		list tot [<tag>]  [(-a|--all)] [(-r|--random)]
		list (t|tag) (s|search) [(-r|--random)] [<searchArgs>...]
		list (t|tag) [<tag>] [(-r|--random)]
	"""
	REMOVE="""
	Usage:
		remove memo [(-d <dname>)]
		remove tag (s|search) <_searchArgs> <removedTags>...
		remove tag [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)] <removedTags>...
		remove tot [<tag>]
		remove (s|search) <searchArgs>...
		remove [(-t <tags>)] [(-m <memo>)] [(-u <userid>)] [(-D <dbid>)]
	"""
	APPEND="""
	Usage:
		append tag (s|search) <searchArgs> <tagsToAppend>...
		append tag [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)] <tagsToAppend>...
	"""
	ALTER="""
	Usage:
		alter (s|search) <searchArgs>...
		alter [(-t <tags>)] [(-m <memo>)]
	"""
	NUMBER="""
	Usage:
		number [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)]
	"""
	EXPAND="""
	Usage:
		expand [(-t <tags>)] [(-m <memo>)] [(-O|--override)]
	"""
	VIM="""
	Usage:
		vim (f|file) <fname>
		vim tot [(-t <tag>)] [(-r|--random)]
		vim (s|search) [(-n <number>)] [(-d <dname>)] [(-r|--random)] [<searchArgs>...]
		vim [(-t <tags>)] [(--nt <noTags>)] [(-m <memo>)] [(-c <comment>)] [(-F <from>)] [(-U <until>)] [(--pn|--printNot)] [(-n <number>)] [(-d <dname>)] [(-r|--random)]
	
	Options:
		searchArgs : "-" to "/". ex) vim s -t book -> vim /t book
	"""
	SET="""
	Usage:
		set [<key>]
		set <key> <value>
	"""
	HELP="""
	Usage:
		help [(-a|--all)]
	"""
HELP="""
	help [(-a|--all)]
	csm write
	csm append
	csm remove
	search
	remove
	append
	alter
	expand
	vim ...
	vlc
	alias
	set
"""

class Command(util.Command):
	ALTER=("AL","ALTER")
	VIM=["VIM"]
	ADMIT=("AD","ADMIT")
	ALIAS=("ALS","ALIAS")
	EXPAND=("EXP","EXPAND")
	SET=["SET"]
	SEARCH_CARD=["SEARCH_CARD"]

class DBShell(__shell__.DBShell,__shell__.BaseShell3):
	VIM_MAX=50
	VIM_COUNT_OF_FILE=50
	PROMPT=str(crayons.magenta(">>"))
	#PROMPT=">>"
	def __init__(self,db,expander=None,environ={},stdout=sys.stdout):
		__shell__.DBShell.__init__(self,db)
		__shell__.BaseShell3.__init__(self,db.dname,self.PROMPT)
		self.dname=db.dname
		self.expander=expander
		self.environ=environ
		self.stdout=stdout
		os.environ["KYODAISHIKI_DB_DIR"]=db.dname
		os.environ["KYODAISHIKI_DB_ID"]=db.id
	def execQuery(self,query,output=sys.stdout):
		if query.command in _util.Command.HELP:
			try:
				args=docopt.docopt(Docs.HELP,query.args)
			except SystemExit:
				return
			output.write("*** select2 ***\n")
			output.write(HELP+"\n")
			if args["-a"] or args["--all"]:
				output.write("*** select ***\n")
				return __shell__.DBShell.execQuery(self,query,output)
		elif query.command in _util.Command.WRITE:
			try:
				args=docopt.docopt(Docs.WRITE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["w"] or args["word"]:
				csm=writeW()
				self.db.appendCSM(csm)
			elif args["tot"]:
				return super().execQuery(query,output)
			else:
				csm=writeShell()
				self.db.appendCSM(csm)
			self.db.save()
		elif query.command in _util.Command.SEARCH:
			try:
				return self.search(query.args,output)
			except KeyboardInterrupt as e:
				return
			except Exception as e:
				print(e)
			except SystemExit as e:
				print(e)
		elif query.command in Command.SEARCH_CARD:
			try:
				return self.search_card(query.args,output)
			except KeyboardInterrupt as e:
				return
			except Exception as e:
				print(e)
		elif query.command in _util.Command.LIST:
			try:
				args=docopt.docopt(Docs.LIST,query.args)
			except SystemExit as e:
				print(e)
				return
			tag=args["<tag>"].upper() if args["<tag>"] else str()
			if args["tot"]:
				all_=args["-a"] or args["--all"]
				if tag:
					U=self.db.getU()
					tots=self.db.searchTOT(tag)
				else:
					tots=self.db.tots.values()
				if args["-r"] or args["--random"]:
					tots=list(tots)
					random.shuffle(tots)
				for tot in tots:
					if all_:
						c=util.Category.make_from_tot(tot,self.db.tots,self.db.text)
						data=str(c)+"\n"
					else:
						tot__=__data__.Logic.Group.makeFromIndex(tot.nameGroup,self.db.text)
						data="* "+str(tot__)
					output.write(data+"\n")
			else:
				if args["s"] or args["search"]:
					random_=args["-r"] or args["--random"]
					searchArgs=args["<searchArgs>"]
					searchArgs=util.arg_replace(searchArgs)
					cards=self.execQuery(__shell__.Query(("search_card",*searchArgs)),output)
					cards=list(cards)
					if not cards:
						return
					if len(cards) == 1:
						tags=cards[0].tags(self.db.text)
						data=map(lambda tag:(tag,1),tags)
					else:
						def ls_tag_getData(cards):
							res={}
							for card in cards:
								tags=card.tags(self.db.text)
								for tag in tags:
									if not res.get(tag):
										res[tag]=0
									res[tag]+=1
							return res
						data=ls_tag_getData(cards).items()
					if random_:
						data=list(data)
						random.shuffle(data)
					else:
						data=sorted(data,key=lambda dat:dat[1])
					sio=_pyio.StringIO()
					for tag,n in data:
						print(tag,n,file=sio)
					sio.seek(0)
					print(sio.read())
				else:
					tag=re.compile(tag)
					tags=filter(lambda tag__:re.search(tag,tag__),self.db.getTags())
					data=[]
					for tag__ in tags:
						tagobj= self.db.tag.get(self.db.find(tag__))
						if tagobj:
							data.append((tag__,len(tagobj.cardIDs)))
					if args["-r"] or args["--random"]:
						data=list(data)
						random.shuffle(data)
					else:
						data=sorted(data,key=lambda data__:data__[1])
					res=""
					for tag__,n in data:
						res+=tag__+" "+str(n)+"\n"
					output.write(res)
					data=map(lambda tag__:( tag__,len( self.db.tag.get(self.db.find(tag__)).cardIDs ) ),tags)   #[(<tag>,<n>),...]

		elif query.command in _util.Command.REMOVE:
			try:
				args=docopt.docopt(Docs.REMOVE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["memo"]:
				dname=args["<dname>"] if args["-d"] else util.DEFAULT_CSM_DIR_F(self.db.dname)
				with open(TMP(),"w+") as f:
					f.write("\n".join(map(lambda memo:'rm -m "{0}"'.format(memo),getMemo(dname))))
					f.seek(0,0)
					return super().__begin__(f,output)
			elif args["tag"]:
			#remove tag (s|search) <searchArgs> <removedTags>...
			#remove tag [(-t <tags>)] [(-m <memo>)] [(-F <from>)] [(-U <until>)] <removedTags>...
			#remove tot [<tag>]
			#remove tag (s|search) <searchArgs>...
				removedTags=args["<removedTags>"]
				if args["s"] or args["search"]:
					#searchArgs=args["<searchArgs>"]
					searchArgs=__shell__.Query.read(args["<_searchArgs>"])
					cards=self.execQuery(__shell__.Query(("search_card",*util.arg_replace(searchArgs))),output)

				else:
					memo=args["<memo>"] if args["-m"] else ""
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					from_=args["<from>"] if args["-F"] else "1900-1-1"
					until=args["<until>"] if args["-U"] else "2200-1-1"
					from_=util.to_datetime(from_)
					until=util.to_datetime(until)
					cards=filter(lambda card:from_<=util.to_datetime(card.date)<until,list(self.db.search(memo,tags)))
				cards=list(cards)
				self.db.__removeTags__(map(lambda card:card.id,cards),removedTags)
				for card in cards:
					output.write("Remove {0} from {1}\n".format(str(removedTags),card.memo(self.db.text)))
			elif args["tot"]:
				return __shell__.DBShell.execQuery(self,query,output)
			else:
				if args["s"] or args["search"]:
					searchArgs=args["<searchArgs>"]
					cards=self.execQuery(__shell__.Query(("search_card",*util.arg_replace(searchArgs))),output)
				else:
					memo=args["<memo>"] if args["-m"] else ""
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					if args["-u"]:
						tags.append(Attr.to_format(Attr.USERID).format(args["<userid>"].upper()))
					if args["-D"]:
						tags.append(Attr.to_format(Attr.DBID).format(args["<dbid>"].upper()))
					if not memo and not tags:
						output.write("You will remove all cards. Really OK??(.../n) : ")
						yn=input()
						if yn.upper()!="Y":
								return 
					cards=self.db.search(memo,tags)
				for card in list(cards):
					#csm=__data__.CSM.makeOne(self.db.text,card)
					self.db.remove(card.id)
					output.write("Removed "+card.memo(self.db.text)+"\n")
				self.db.save()

		elif query.command in _util.Command.CSM:
			query=__shell__.Query(query.args)
			if query.command in _util.Command.WRITE:
				try:
					args=docopt.docopt(Docs.CSM.WRITE,query.args)
				except SystemExit as e:
					print(e,query.args)
					return
				dname=args["<dname>"] if args["-d"] else util.DEFAULT_CSM_DIR_F(self.db.dname)
				dname=_util.realpath(dname)
				if not os.path.exists(dname):
					os.makedirs(dname)
				if args["tot"] :
					tag=args["<tag>"] if args["-t"] else ""
					for tot in list(__data__.TOT.make(self.db.text,self.db.searchTOT(tag))):
						tot.write(os.path.join(dname,tot.fname))
				elif args["csm"]:
					memo=args["<memo>"] if args["-m"] else str()
					tags=args["<tags>"].upper().split(",") if args["-t"] else list()
					regDBID_TAG=re.compile(Attr.DBID)
					for csm in list(__data__.CSM.make(self.db.text,self.db.search(memo,tags))):
						csm.write(os.path.join(dname,csm.fname))
				else:
					self.execQuery(__shell__.Query(("CSM","WRITE","tot",*query.args)),output)
					self.execQuery(__shell__.Query(("CSM","WRITE","csm",*query.args)),output)
			elif query.command in _util.Command.APPEND:
				try:
					args=docopt.docopt(Docs.CSM.APPEND,query.args)
				except SystemExit:
					return
				dname=args["<dname>"] if args["-d"] else util.DEFAULT_CSM_DIR_F(self.db.dname)
				dname=_util.realpath(dname)
				if args["tot"] :
					tag=args["<tag>"] or ""
					override=args["-O"] or args["--override"]
					regTag=re.compile(tag)
					edit=args["-e"] or args["--edit"]
					if edit:
						basetots=__data__.TOT.make(self.db.text,self.db.searchTOT(tag))
						fnames=map(lambda tot:os.path.join(dname,tot.fname),basetots)
						fnames=filter(lambda fname:os.path.exists(fname),fnames)
						csms=map(lambda fname:__data__.CSM.read(fname),fnames)
					else:
						csms=__data__.CSM.readDir(dname)
					for csm in list(csms):
						if __data__.TOT.isTOT(csm):
							tot=__data__.TOT.toTOT(csm)
							if re.search(regTag,tot.name):
								if self.db.appendTOT(tot.name,tot.childs,override):
									output.write("Appended {0}\n".format(tot.name))
				elif args["csm"]:
					memo=args["<memo>"] if args["-m"] else ""
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					override=args["-O"] or args["--override"]
					regMemo=re.compile(memo)
					text=""
					edit=args["-e"] or args["--edit"]
					if edit:
						basecsms=__data__.CSM.make(self.db.text,self.db.search(memo,tags))
						fnames=map(lambda tot:os.path.join(dname,tot.fname),basecsms)
						fnames=filter(lambda fname:os.path.exists(fname),fnames)
						csms=map(lambda fname:__data__.CSM.read(fname),fnames)
					else:
						csms=__data__.CSM.readDir(dname)
						csms=filter(lambda csm:not __data__.TOT.isTOT(csm),csms)
						csms=filter(lambda csm:(not memo or re.search(regMemo,csm.memo)) and (not tags or all([tag in csm.tags for tag in tags])),csms)
					for csm in list(csms):
						if self.db.appendCSM(csm,override):
							text+="Appended {0}\n".format(csm.memo)
					output.write(text)
				else:
					query,_,_=util.partitionArgs(query.data,("-d","-r","--rec"))
					query=__shell__.Query(query)
					dname=args["<dname>"] or util.DEFAULT_CSM_DIR_F(self.db.dname)
					dname=_util.realpath(dname)
					__shell__.DBShell.execQuery(self,__shell__.Query(("CSM",*query.data,"-d",dname)),output)
					if args["-r"] or args["--rec"]:
						for c,ds,fs in os.walk(dname):
							for dname__ in ds:
								dname__=os.path.join(c,dname__)
								__shell__.DBShell.execQuery(self,__shell__.Query(("CSM",*query.data,"-d",dname__)),output)
					#if "-d" not in query:
					#	query.extend(("-d",util.DEFAULT_CSM_DIR_F(self.db.dname)))
				self.db.save()
			elif query.command in Command.REMOVE:
				csm_dname=util.DEFAULT_CSM_DIR_F(self.db.dname)
				winshell.delete_file(csm_dname)
				output.write("Removed {0}\n".format(csm_dname))
			else:
				if "-d" not in query:
					query.extend(("-d",util.DEFAULT_CSM_DIR_F(self.db.dname)))
				__shell__.DBShell.execQuery(self,__shell__.Query(("CSM",*query.data)),output)
		elif query.command in _util.Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["tag"]:
				tagsToAppend=list(map(lambda tag:tag.upper(),args["<tagsToAppend>"]))
				if args["s"] or args["search"]:
					searchArgs=util.arg_replace(__shell__.Query.read(args["<searchArgs>"]).data)
					cards=self.execQuery(__shell__.Query(("search_card",*searchArgs)),output)
				else:
					memo=args["<memo>"] if args["-m"] else str()
					tags=args["<tags>"].upper().split(",") if args["-t"] else []
					from_=args["<from>"] if args["-F"] else "1900-1-1"
					until=args["<until>"] if args["-U"] else "2200-1-1"
					from_=util.to_datetime(from_)
					until=util.to_datetime(until)
					cards=filter(lambda card:from_<=util.to_datetime(card.date)<until,list(self.db.search(memo,tags)))
				for card in list(cards):
					self.db.appendTags(card.id,tagsToAppend)
					output.write("Append "+str(tagsToAppend)+" to "+card.memo(self.db.text)+"\n")
			self.db.save()
		elif query.command in Command.ALTER:
			try:
				args=docopt.docopt(Docs.ALTER,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["s"] or args["search"]:
				searchArgs=args["<searchArgs>"]
				searchArgs=util.arg_replace(searchArgs)
				cards=self.execQuery(__shell__.Query(("search_card",*searchArgs)),output)
			else:
				memo=args["<memo>"] if args["-m"] else str()
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				cards=self.db.search(memo,tags)
			s=""
			for card in list(cards):
				if NOT in card.tags(self.db.text):
					self.db.removeTags(card.id,[NOT])
				else:
					self.db.appendTags(card.id,[NOT])
				s+="Altered "+card.memo(self.db.text)+"\n"
			output.write(s)
			self.db.save()
		elif query.command in Command.EXPAND:
			if not self.expander:
				output.write("Don't find expander.\n")
				return
			try:
				args=docopt.docopt(Docs.EXPAND,query.args)
			except SystemExit as e:
				print(e)
				return
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			memo=args["<memo>"] if args["-m"] else ""
			override=args["-O"] or args["--override"]
			data=""
			for csm in list(__data__.CSM.make(self.db.text,self.db.search(memo,tags))):
				if util.Expander.TAG in csm.tags: #maybe expanded
					continue
				csm__=self.expander.expand(csm)
				csm__.memo="__"+csm__.memo
				self.db.appendCSM(csm__,override)
				data+="Append {0} \n".format(csm__.memo)
			output.write(data)
		elif query.command in Command.VIM:	#-Z for can't use shell query.command in vim.
			try:
				args=docopt.docopt(Docs.VIM,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["f"] or args["file"]:
				fnames=[_util.realpath(args["<fname>"])]
			elif args["tot"]:
				dname=args["<dname>"] if args["-d"] else util.DEFAULT_CSM_DIR_F(self.db.dname)
				dname=_util.realpath(dname)
				tag=args["<tag>"].upper() if args["-t"] else ""
				tots=__data__.TOT.make(self.db.text,self.db.searchTOT(tag))
				fnames=map(lambda tot:os.path.join(dname,tot.fname),tots)
			elif args["s"] or args["search"]:
				dname=args["<dname>"] if args["-d"] else util.DEFAULT_CSM_DIR_F(self.db.dname)
				dname=_util.realpath(dname)
				random_=args["-r"] or args["--random"]
				searchArgs=util.arg_replace(args["<searchArgs>"])
				sio=_pyio.StringIO()
				self.execQuery(__shell__.Query(("search",*searchArgs,"-p","f")),sio)
				sio.seek(0)
				def get_fnames():
					for line in sio.read().split("\n"):
						if line.find("*") != 0 and ".csm" in line:
							yield line
				fnames=map(lambda fname:os.path.join(dname,fname),get_fnames())
				fnames=filter(lambda fname:os.path.exists(fname),fnames)
				if random_:
					fnames=list(fnames)
					random.shuffle(fnames)
			else:
				memo=args["<memo>"] if args["-m"] else ""
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				noTags=args["<noTags>"].upper().split(",") if args["--nt"] else []
				comment=args["<comment>"] if args["-c"] else ""
				from_=util.to_datetime(args["<from>"]) if args["-F"] else util.to_datetime("1900-1-1")
				until=util.to_datetime(args["<until>"]) if args["-U"] else util.to_datetime("2200-1-1")
				dname=args["<dname>"] if args["-d"] else util.DEFAULT_CSM_DIR_F(self.db.dname)
				dname=_util.realpath(dname)
				random_=args["-r"] or args["--random"]
				cards=filter(lambda card:from_<=util.to_datetime(card.date)<until,self.db.search(memo,tags))
				if comment:
					cards=filter(lambda card:re.search(comment,card.comment(self.db.text)),cards)
				if not (args["--pn"] or args["--printNot"]):
					noTags.append(NOT)
				if noTags:
					def filter_nt(cards):
						noTagIdxes=list(filter(lambda tag:tag,map(lambda tag:self.db.find(tag),noTags)))
						for card in cards:
							tagIdxes=self.db.cardToTags.get(card.id,[])
							if not any(map(lambda noTagIdx:noTagIdx in tagIdxes,noTagIdxes)):
								yield card
					cards=filter_nt(cards)
				if not random_:
					cards=sorted(cards,key=lambda card:card.date)
				fnames=map(lambda csm:os.path.join(dname,csm.fname),__data__.CSM.make(self.db.text,cards))
				fnames=filter(lambda fname:os.path.exists(fname),fnames)
				if random_:
					fnames=list(fnames)
					random.shuffle(fnames)
			fnames=list(fnames)
			if not fnames:
				return
			n=len(fnames)//self.VIM_COUNT_OF_FILE + 1
			for i in range(n):
				if i!=0:
					output.write("You open next files... (.../n)")
					y_n=input().upper()
					if y_n == "N":
						break
				#sp.call(["vim","-Z",*fnames[i*self.VIM_COUNT_OF_FILE:i*self.VIM_COUNT_OF_FILE+self.VIM_COUNT_OF_FILE]])
				sp.call(["vim",*fnames[i*self.VIM_COUNT_OF_FILE:i*self.VIM_COUNT_OF_FILE+self.VIM_COUNT_OF_FILE]])
			#sp.call(["vim",*fnames])
		elif query.command in Command.ALIAS:
			return self.alias(query.args,output)
		elif query.command in self.aliasCommands:
			#query__=copy.copy(self.aliasCommands[query.command])
			#query__.extend(query.args)
			query__=self.aliasCommands[query.command]
			query__=__shell__.Query((*query__.data,*query.args))
			return self.execQuery(query__,output)
		elif query.command in Command.SET:
			try:
				args=docopt.docopt(Docs.SET,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["<value>"]:
				self.environ[args["<key>"].upper()]=args["<value>"]
			else:
				key=args["<key>"] if args["<key>"] else ""
				for envkey in self.environ:
					if re.match(key,envkey):
						output.write("{0} : {1}\n".format(envkey,self.environ[envkey]))
		elif query.command in Command.NUMBER:
			pass
		else:
			return __shell__.DBShell.execQuery(self,query,output)
	def search_card(self,args,output):
		try:
			args=docopt.docopt(Docs.SEARCH_CARD,args)
		except SystemExit as e:
			print(e)
			return
		memo=args["<memo>"] if args["-m"] else ""
		if args["--mm"]:
			memo=addlowUp(memo,args["<lowUpMemo>"])
		if args["--em"]:
			memo=util.addMemo(memo,re.escape(args["<escapedMemo>"]))
		tags=args["<tags>"].upper().split(",") if args["-t"] else []
		comment=args["<comment>"] if args["-c"] else ""
		from_=args["<from>"] if args["-F"] else "1900-01-01"
		from_=util.to_datetime(from_)
		until=args["<until>"] if args["-U"] else "3000-01-01"
		until=util.to_datetime(until)
		noTags=args["<noTags>"].upper().split(",") if args["--nt"] else []
		U=self.db.getU()
		#if not (args["--pn"] or args["--printNot"]) and noTags:
		printNot=args["--pn"] or args["--printNot"]
		if not printNot:
			noTags.append(NOT)
			#noTags[-1]=noTags[-1]+"||"+NOT
		#noTags=self.db.getTagsRec(noTags,U)
		if args["-u"]:
			userid=args["<userid>"]
			tags.append(Attr(Attr.USERID)(userid))
		if args["-D"]:
			dbid=args["<dbid>"].upper()
			tags.append(Attr(Attr.DBID)(dbid))
		try:
			cards=filter(lambda card:from_<=util.to_datetime(card.date)<until,self.db.search(memo,tags))
		except Exception as e:
			print(e)
			return []
		regComment=re.compile(comment)
		data=""
		def getCards():
			for card in cards:
				tags=card.tags(self.db.text)
				if any(map(lambda tag:tag in tags,noTags)):
					continue
				if not comment or re.search(regComment,card.comment(self.db.text)):
					yield card
		return getCards()
	def search(self,args,output):
		try:
			args_=docopt.docopt(Docs.SEARCH,args)
		except SystemExit as e:
			print(e)
			return
		if args_["n"] or args_["not"]:
			#search (n|not) [(-t <tags>)] [(--nt <noTags>)] [(-m <memo>)] [(--mm <lowUpMemo>)] [(--em <escapedMemo>)] [(-c <comment>)] [(-F <from>)] [(-U <until>)] [(-u <userid>)] [(-D <dbid>)] [(-p <pMode>)] [(-r|--random)]
			args.pop(0)
			args__,_,_=util.partitionArgs(args,("-p","-r","--random"))
			if "-t" in args__:
				i=args__.index("-t")+1
				args__[i]+=","+NOT
			else:
				args__=("-t",NOT,*args__)
			cards=self.execQuery(__shell__.Query(("search_card",*args__,"--printNot")),output)
		else:
			args__,_,_=util.partitionArgs(args,("-p","-r","--random"))
			cards=self.execQuery(__shell__.Query(("search_card",*args__)),output)
		pMode=args_["<pMode>"].upper()+"M" if args_["-p"] else "M"
		if args_["-r"] or args_["--random"]:
			cards=list(cards)
			random.shuffle(cards)
		else:
			cards=sorted(cards,key=lambda card:card.date)
		data=""
		is_stdout=output is sys.stdout
		for csm in __data__.CSM.make(self.db.text,cards):
			if is_stdout:
				#data+=crayons.magenta("* ")+csm.dump(pMode)+"\n"
				data+="* "+csm.dump(pMode)+"\n"
				#data+=crayons.blue("-"*50)+"\n"
				data+="-"*50+"\n"
			else:
				data+="* "+csm.dump(pMode)+"\n"
				data+="-"*50+"\n"
		output.write(data)
	def start(self):
		if iscrayon(self.stdout):
			self.stdout.write(crayons.magenta("*** ")+crayons.blue(self.db.id)+crayons.magenta(" ***\n"))
		else:
			self.stdout.write("*** "+self.db.id+" ***\n")
		__shell__.BaseShell3.start(self)
		self.close()
	def close(self):
		__shell__.DBShell.close(self)
		__shell__.BaseShell3.close(self)
		#csm_dname=DEFAULT_CSM_DIR_F.format(self.db.id)
		#if os.path.exists(csm_dname):
		#	shutil.rmtree(csm_dname)

class AuHSShell(__shell__.BaseShell3):
	PROMPT=">>"
	ALL_ENTER_BAT="se2_enter.bat"
	ALL_EXIT_BAT="se2_exit.bat"
	ALL_ALIAS_TXT="se2_alias.txt"
	def __init__(self,homeShell):
		super().__init__(prompt=self.PROMPT)
		self.homeDB=homeShell.home
		self.environ={}
	def execQuery(self,query,output):
		dbids=list(self.homeDB.getDBIDs(query.command))
		if not dbids:
			return False
		dbid=dbids[0].upper()
		db=self.homeDB.select(dbid)
		if not db:
			output.write(dbid.lower()+" doesn't exist.\n")
			return False
		expander=util.Expander(self.homeDB,dbid)
		shell=DBShell(db,expander,environ=self.environ)
		all_enter_bat=os.path.join(self.homeDB.dname,self.ALL_ENTER_BAT)
		all_exit_bat=os.path.join(self.homeDB.dname,self.ALL_EXIT_BAT)
		all_alias=os.path.join(self.homeDB.dname,self.ALL_ALIAS_TXT)
		_util.touch(all_enter_bat)
		_util.touch(all_exit_bat)
		_util.touch(all_alias)
		shell.execAliasf(all_alias,self.null)
		if query.args:
			shell.execQuery(__shell__.Query(query.args),output)
		else:
			shell.beginf(all_enter_bat)
			shell.start()
			shell.beginf(all_exit_bat)
	def start(self):
		self.stdout.write("Don't find dbid.\n")
