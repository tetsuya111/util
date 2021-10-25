from . import api
from . import util
import sqlite3
import myutil
import sys

#def makeDB(db,table_name,columns,cols,init_column_type=DEF_INIT_COLUMN_TYPE):
def makeDB(db,table_name,type_,log=sys.stdout):
	def getData():
		for data in util.search("",type_=type_,n=10**32):
			data["stocked"]=1 if data["stocked"] else 0
			if log:
				print(data,file=log)
			yield list(data.values())+[type_]
	columns={"title":"text","url":"text","author":"text","price":"int","stocked":"int","bg":"int"}
	myutil.makeDB(db,table_name,columns,getData())

bookTypes=list(range(1201,1229))

def makeDBOfBook(db,table_name,log=sys.stdout):
	for type_ in  bookTypes:
		makeDB(db,table_name,type_,log=log)
