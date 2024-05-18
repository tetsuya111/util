from kyodaishiki import __shell__
from . import util
from kyodaishiki import __utils__
from kyodaishiki import __data__
import docopt
import base64
import os
import re

TAG="IS_BINALY"
DUMPED_TAG="DUMPED_BINALY"

DEFAULT_DUMP_DIR=__utils__.realpath(r"%USERPROFILE%\desktop\dumpedBinalliFiles")

class Docs:
	APPEND="""
	Usage:
		append url <dbid> <url> [(-t <appendtags>)]
		append dir <dbid> <dname> [(-t <appendtags>)] [(-f <fname>)]
		append <dbid> <fname> [(-t <appendtags>)]
	"""
	DUMP="""
	Usage:
		dump [(-t <tags>)] <dbid> [(-d <dname>)]
	"""

class Command(__utils__.Command):
	DUMP=("D","DUMP")

class Shell(__shell__.BaseShell):
	PROMPT=":>>"
	def __init__(self,homeDB):
		self.homeDB=homeDB
		super().__init__(prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"].upper()
			db=self.homeDB.select(dbid)
			if not db:
				self.homeDB.append(dbid,[TAG])
				db=self.homeDB.select(dbid)
			tags=args["<appendtags>"].upper().split(",") if args["-t"] else []
			if args["url"]:
				url=args["<url>"]
				res=requests.get(url)
				data=base64.b64encode(res.content)
				db.append(fname,data,tags+[TAG])
				return
			if args["dir"]:
				dname=__utils__.realpath(args["<dname>"])
				fname_pattern=args["<fname>"] if args["-f"] else ""
				fnames=list(map(lambda fname:os.path.join(dname,fname),filter(lambda fname:re.search(fname_pattern,fname),os.listdir(dname))))
			else:
				fnames=[__utils__.realpath(args["<fname>"])]
			for fname in fnames:
				with open(fname,"rb") as f:
					data=base64.b64encode(f.read()).decode()
				db.append(os.path.split(fname)[1],data,tags+[TAG])
				output.write("Append {0} to {1}.\n".format(fname,dbid))
			db.save()
		elif query.command in Command.DUMP:
			try:
				args=docopt.docopt(Docs.DUMP,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"].upper()
			db=self.homeDB.select(dbid)
			if not db:
				output.write("Don't find {0}.\n".format(dbid))
				return
			tags=args["<tags>"].upper().split(",") if args["-t"] else []
			dname=__utils__.realpath(args["<dname>"]) if args["-d"] else DEFAULT_DUMP_DIR
			if not os.path.exists(dname):
				os.makedirs(dname)
			for csm in __data__.CSM.make(db.text,db.search(tags=tags)):
				fname=os.path.join(dname,csm.memo)
				data=csm.comment
				data=base64.b64decode(data.encode())
				with open(fname,"wb") as f:
					f.write(data)
			output.write("Dump to {0}.\n".format(dname))
		else:
			return super().execQuery(query,output)



