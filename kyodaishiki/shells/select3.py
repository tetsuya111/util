import sys
sys.path.append("C:\\Users\\tetsu\\code\\kyodaishiki2")

import docopt
import re
import os
from kyodaishiki import _util
from kyodaishiki import __data__
from kyodaishiki import __shell__
from kyodaishiki import __db__
from . import select2
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

#select2 for augment_hs3

def isAuHS3Card(card):
	return hasattr(card,"type") and hasattr(card,"ishome")

class AuHSShell(select2.AuHSShell):
	PROMPT=">>"
	ALL_ENTER_BAT="se2_enter.bat"
	ALL_EXIT_BAT="se2_exit.bat"
	ALL_ALIAS_TXT="se2_alias.txt"
	def execQuery(self,query,output):
		dbids=list(self.homeDB.getDBIDs(query.command))
		if not dbids:
			return False
		dbid=dbids[0].upper()
		card=self.homeDB.get(self.homeDB.find(dbid))
		if not card:
			output.write(dbid.lower()+" doesn't exist.\n")
			return False
		elif not isAuHS3Card(card):
			print("db is illegal! this card is not auhs3 card.",file=output)
			return
		if card.type == augment_hs3.Index.DB.Type.DB:
			return super().execQuery(query,output)
		home=self.homeDB.select(dbid)
		shell=augment_hs3.HomeShell(home)
		shell.start()
	def start(self):
		self.stdout.write("Don't find dbid.\n")
