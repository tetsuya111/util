import kyodaishiki.__shell__ as ksh
from . import api
import json
import docopt

class Docs:
	SEARCH_DATA="""
	Usage:
		search_data <query> [(-n <number>)] [(--ps <pageofstart>)] [(--pf <priceFrom>)] [(--pu <priceUntil>)] [(-S|--onlystocked)]
	"""
	SEARCH="""
	Usage:
		search <query> [(-n <number>)] [(--ps <pageofstart>)] [(--pf <priceFrom>)] [(--pu <priceUntil>)] [(-S|--onlystocked)]
	"""
	HELP="""
		search
	"""

class Command:
	HELP=("H","HELP")
	SEARCH=("S","SEARCH")

class Shell(ksh.BaseShell3):
	def _execQuery(self,query,output):
		if query.command in Command.HELP:
			print(Docs.HELP,file=output)
		elif query.command in Command.SEARCH:
			for data in self.search_data(query.args,output):
				print(json.dumps(data,ensure_ascii=False,indent=4),file=output)
		else:
			return super().execQuery(query,output)
	def execQuery(self,query,output):
		try:
			return self._execQuery(query,output)
		except KeyboardInterrupt:
			pass
		except SystemExit:
			pass
	def search_data(self,args,output):
		try:
			args=docopt.docopt(Docs.SEARCH_DATA,args)
		except SystemExit:
			return
		query=args["<query>"]
		number=int(args["<number>"]) if args["-n"] else 5
		start=int(args["<pageofstart>"]) if args["--ps"] else 1
		priceFrom=int(args["<priceFrom>"]) if args["--pf"] else 0
		priceUntil=int(args["<priceUntil>"]) if args["--pu"] else 10**32
		only_stocked=args["-S"] or args["--onlystocked"]
		i=0
		for data in api.searchN(query,start,number):
			if i > number:
				break
			if priceFrom <= data["price"] < priceUntil and (not only_stocked or data["stocked"]):
				yield data
				i+=1
