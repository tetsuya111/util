from kyodaishiki import __shell__

class SNMShell(__shell__.BaseShell):
	def __init__(self,home,browser):
		super().__init__(prompt=self.PROMPT)
		self.browser=browser
	def execQuery(self,query,output):
		super().execQuery(query,output)
	def start(self):
		self.stdout.write("*** welcome to pcmax shell. ***\n")
		super().start()

