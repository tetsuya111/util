from bs4 import BeautifulSoup as bs
import requests
from kyodaishiki import __data__
from kyodaishiki import __shell__
from . import mecab
import docopt

class Docs:
	APPEND="""
	Usage:
		append <dbid> <url>
	"""
	HELP="""
		append <dbid> <url>
	"""

class Command:
	APPEND=("A","APPEND")
	HELP=("H","HELP")
	QUIT=("Q","QUIT")



class SiteShell(__shell__.BaseShell):
	def __init__(self,homeDB):
		self.homeDB=homeDB
		super().__init__()
	def execQuery(self,query,output):
		if query.command in Command.HELP:
			output.write(Docs.HELP+"\n")
		elif query.command in Command.APPEND:
			try:
				args=docopt.docopt(Docs.APPEND,query.args)
			except SystemExit as e:
				print(e)
				return
			dbid=args["<dbid>"].upper()
			url=args["<url>"]
			db=self.homeDB.select(dbid)
			if not db:
				self.homeDB.append(dbid,["2CH"])
				db=self.homeDB.select(dbid)
			try:
				for csm in Article(url).dumpCSM():
					db.appendCSM(csm)
					output.write("Append {0} to {1}.\n".format(csm.memo,dbid))
			except Exception as e:
				print(e)
				return
		else:
			return super().execQuery(query,output)
	def start(self):
		self.stdout.write("*** welcome to nichan ***\n")
		return super().start()


class Article:
	def __init__(self,url):
		data=requests.get(url)
		self.soup=bs(data.text,"html.parser")
	@property
	def title(self):
		title=self.soup.select_one("title")
		if not title:
			return ""
		return title.text
	def getRes(self):
		#{"ID":,"Number":,"Comment":}
		for post in self.soup.select(".post"):
			yield {
				"date":post.get("data-date"),
				"userid":post.get("data-userid"),
				"id":post.get("data-id"),
				"name":post.select_one(".name").text,
				"message":post.select_one(".message").text
			}
	def dumpCSM(self):
		for res in self.getRes():
			yield __data__.CSM(memo=next(mecab.Mecab(data["message"]).getDataAsSentence()),comment=data["message"],tags=(data["userid"],data["id"]))
