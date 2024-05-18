import sys
sys.path.append(r"C:\Users\tetsu\kyodaishiki2\code")

from . import select2
from kyodaishiki import __db__
from kyodaishiki import __data__
from kyodaishiki import __utils__
from kyodaishiki import __shell__
from . import util
from . import augment_hs
import os
import PySimpleGUI as sg
import datetime

class Event:
	CLOSE="Close"
	SEARCH="Search"
	WRITE="Write"
	OPEN="Open"
	REWRITE="ReWrite"


class BaseWindow:
	DEFAULT_SIZE=(1000,600)
	def __init__(self,text,layout,size=(1000,600)):
		sg.theme("DarkAmber")
		self.window=sg.Window(text,layout,size=size)
	@staticmethod
	def is_end(event):
		return event==sg.WIN_CLOSED or event==Event.CLOSE
	def __iter__(self):
		return self
	def __next__(self):
		event,values=self.window.read()
		if self.is_end(event):
			raise StopIteration
		return (event,values)
	def start(self):
		for event,values in self:
			event=event.lower()
			if hasattr(self,event):
				try:
					getattr(self,event)(values)
				except StopIteration:
					break

	def __enter__(self):
		self.start()
		return self
	def __exit__(self,*args,**kwargs):
		self.window.close()
	


class Search(BaseWindow):
	class Output(BaseWindow):
		class CSM(BaseWindow):
			def __init__(self,csm,parent):
				self.csm=csm
				self.parent=parent
				self.db=self.parent.parent.db
				layout=[
					#[sg.Text(csm.memo)],
					[sg.InputText(csm.memo)],
					[sg.Text("")],
					#[sg.Text(csm.comment)],
					[sg.InputText(csm.comment)],
					[sg.Text("")],
					#[sg.Text(",".join(csm.tags))],
					[sg.InputText(",".join(csm.tags))],
					[sg.Text("")],
					[sg.Text(csm.date)],
					[sg.Button(Event.REWRITE),sg.Button(Event.CLOSE)]
				]
				super().__init__("CSM Data",layout)
			def rewrite(self,values):
				memo=values[0]
				comment=values[1]
				tags=values[2].upper().split(",")
				self.db.append(memo,comment,tags,self.csm.date,True)
				self.db.save()
		def __init__(self,csms,parent):
			self.csms=list(csms)
			self.parent=parent
			layout=[[sg.Text("*** Output ***")]]
			for csm in self.csms:
				layout.append([sg.Button(Event.OPEN),sg.Text("* {0}".format(csm.memo))])
			layout.append([sg.Button("Close")])
			super().__init__("Search Output",layout)
		@staticmethod
		def is_end(event):
			return event==sg.WIN_CLOSED or event==Event.CLOSE
		def start(self):
			for event,values in self:
				if Event.OPEN in event:
					n=event.replace(Event.OPEN,"")
					n=0 if not n else int(n)+1
					with Search.Output.CSM(self.csms[n],self):
						pass

	def __init__(self,db):
		self.db=db
		sg.theme("DarkAmber")
		layout=[
			[sg.Text("Memo:"),sg.InputText()],
			[sg.Text("Tags:"),sg.InputText()],
			[sg.Button(Event.SEARCH),sg.Button(Event.CLOSE)]
		]
		self.window=sg.Window("Search",layout)
	@staticmethod
	def is_end(event):
		return event==sg.WIN_CLOSED or event==Event.CLOSE
	def search(self,values):
		memo=values[0] if values[0] else ""
		tags=values[1].upper().split(",") if values[1] else []
		cards=self.db.search(memo,tags)
		csms=__data__.CSM.make(self.db.text,cards)
		with Search.Output(csms,self):
			pass
	def __exit__(self,*args,**kwargs):
		super().__exit__(*args,**kwargs)
		self.db.save()

class Write(BaseWindow):
	def __init__(self,db):
		self.db=db
		layout=[
			[sg.Text("Memo:"),sg.InputText()],
			[sg.Text("Comment:"),sg.InputText()],
			[sg.Text("Tags:"),sg.InputText()],
			[sg.Button(Event.WRITE),sg.Button(Event.CLOSE)]
		]
		super().__init__("Write Card",layout)
	def write(self,values):
		memo=values[0]
		comment=values[1]
		tags=values[2].upper().split(",")
		date=str(datetime.datetime.now()).split(".")[0]
		self.db.append(memo,comment,tags,date)
		raise StopIteration

class Home(BaseWindow):
	def __init__(self,db):
		layout=[
		[sg.Button(Event.SEARCH,size=(15,3)),sg.Button(Event.WRITE,size=(15,3))],
		[sg.Button(Event.CLOSE,size=(15,3))]
		]
		super().__init__("GUI Home",layout)
		self.db=db
	def start(self):
		for event,values in self:
			if event == Event.SEARCH:
				with Search(self.db):
					pass
			elif event == Event.WRITE:
				with Write(self.db):
					pass

class AuHSShell(__shell__.BaseShell3):
	PROMPT=">>"
	ALL_ENTER_BAT="se2_enter.bat"
	ALL_EXIT_BAT="se2_exit.bat"
	ALL_ALIAS_TXT="se2_alias.txt"
	def __init__(self,homeShell):
		super().__init__(prompt=self.PROMPT)
		self.homeDB=homeShell.home
	def execQuery(self,query,output):
		dbids=list(self.homeDB.getDBIDs(query.command))
		if not dbids:
			return False
		dbid=dbids[0].upper()
		db=self.homeDB.select(dbid)
		if not db:
			output.write(dbid.lower()+" doesn't exist.\n")
			return False
		with Home(db):
			pass
	def start(self):
		self.stdout.write("Don't find dbid.\n")

if __name__ == "__main__":
	db_dname=r"C:\Users\tetsu\kyodaishiki2\default_loader_home\main\xxx"
	db=__db__.TagDB(db_dname)
	s=Home(db)
	s.start()
