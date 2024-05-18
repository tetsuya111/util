from . import util
from kyodaishiki import __utils__
from kyodaishiki import __shell__

class SiteShell(__shell__.BaseShell):
	def __init__(self,homeDB):
		self.homeDB=homeDB
		super().__init__()
