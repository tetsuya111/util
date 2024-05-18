from kyodaishiki import __shell__
from kyodaishiki import __data__
from . import select2
from . import util
import os
import docopt
import _pyio
import pykakasi
import re
import datetime
import sys

REFERENCE_TERM="REFERENCE_TERM"

class EnvKey:
	RB_TAGS="RBTAGS"

def __convert__(k,word):
	res={}
	for data in k.convert(word):
		for key in data:
			if not res.get(key):
				res[key]=""
			res[key]+=data[key]
	return res
def convert(word):
	return __convert__(pykakasi.kakasi(),word)


def is_kanji(converted):
	return not (converted["orig"] == converted["hira"] or converted["orig"] == converted["kana"])


CLEAN_CONVERT={"g":"k","z":"s","j":"s","d":"t","b":"h"}
def clean_as_index(word):	#word is roman
	return "".join(map(lambda c:CLEAN_CONVERT[c] if CLEAN_CONVERT.get(c) else c,word))
	

def __search__(db,word="",tags=[]):
#res card matched with word if word is kanji
#res card as romaji matched with word as romaji if word is not kanji 
	k=pykakasi.kakasi()
	converted_word=__convert__(k,word)
	if is_kanji(converted_word):
		return filter(lambda card:re.match(word,card.memo(db.text)),db.search(tags=tags))
	word_roman=converted_word["hepburn"].lower()
	word_roman=clean_as_index(word_roman)
	return filter(lambda card:re.match(word_roman,clean_as_index(__convert__(k,card.memo(db.text))["hepburn"].lower())),db.search(tags=tags))

def search(db,word="",tags=[]):
	return __search__(db,word,(*tags,REFERENCE_TERM))

def write_rb(output=sys.stdout):
	output.write("Word : ")
	word=input()
	output.write("Meaning : ")
	meaning=input()
	return __data__.CSM(word,meaning,[],str(datetime.datetime.now()))

class Docs:
	GET="""
	Usage:
		get <word> [(-t <tags>)]
		get [(-t <tags>)]
	"""
	WRITE="""
	Usage:
		write (j|jiten|rb) [(-t <tags>)]
		write tot
		write
	"""
	HELP="""
		get
		write
	"""

class Command(util.Command):
	GET=("G","GET")

class DBShell(select2.DBShell):
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		elif query.command in Command.GET:
			try:
				args=docopt.docopt(Docs.GET,query.args)
			except SystemExit as e:
				print(e)
				return
			word=args["<word>"] if args["<word>"] else ""
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			memo=word
			data=""
			kakasi=pykakasi.kakasi()
			for card in sorted(search(self.db,memo,tags),key=lambda card:kakasi.convert(card.memo(self.db.text))[0]["hira"]):
				meaning=card.comment(self.db.text).split("\n-")[0]
				data+="{0} -> {1}\n".format(card.memo(self.db.text),meaning)
			output.write(data)
		elif query.command in Command.WRITE:
			try:
				args=docopt.docopt(Docs.WRITE,query.args)
			except SystemExit as e:
				print(e)
				return
			if args["j"] or args["jiten"] or args["rb"]:
				tags=args["<tags>"].upper().split(",") if args["-t"] else []
				if self.environ.get(EnvKey.RB_TAGS):
					tags.extend(self.environ[EnvKey.RB_TAGS].upper().split(","))
				csm=write_rb()
				csm.tags=tags if tags else ["UNKNOWN"]
				csm.tags=(REFERENCE_TERM,*csm.tags)
				self.db.appendCSM(csm)
			else:
				return super().execQuery(query,output)
		else:
			return super().execQuery(query,output)

class DUShell(__shell__.BaseShell):
	PROMPT=">>"
	def __init__(self,dushell):
		super().__init__(prompt=self.PROMPT)
		self.DBShell=DBShell
		self.homeDB=dushell.homeDB
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
		alias_txt=os.path.join(self.homeDB.dname,select2.AuHSShell.ALL_ALIAS_TXT)
		try:
			shell=self.DBShell(db)
			shell.execAliasf(alias_txt,_pyio.StringIO())
			shell.start()
		except Exception as e:
			output.write(str(e)+"\n")
	def start(self):
		return self.execQuery(__shell__.Query(),self.stdout)


