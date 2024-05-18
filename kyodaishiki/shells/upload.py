from kyodaishiki import __shell__

class Shell(__shell__.BaseShell):
	PROMPT=":>"
	def __init__(self,homeDB):
		self.homeDB=homeDB
		super().__init__(prompt=self.PROMPT)
	def execQuery(self,query,output):
		if query.command in []:
			pass
		else:
			return super().execQuery(query,output)

class AuHSShell(__shell__.BaseShell):
	PROMPT=">>"
	def __init__(self,homeDB,*args):
		super().__init__(prompt=self.PROMPT)
		self.homeDB=homeDB
	def execQuery(self,query,output):
		if query:
			return Shell(self.homeDB).execQuery(query,output)
		return Shell(self.homeDB).start()
	def start(self):
		self.execQuery(__shell__.Query([]),self.stdout)
