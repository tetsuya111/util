import requests
from bs4 import BeautifulSoup as bs
import time
import urllib.parse as up
import json
import sqlite3
import myutil as mu
import sys
import re

HOST="bookmeter.com"
URL="https://"+HOST

WANT_URL=URL+"/users/{0}/books/wish"
READ_URL=URL+"/users/{0}/books/read"

SEARCH_USERS_URL=URL+"/users/search"

DB_NAME_F="bm_user_{0}"
TABLE_NAME_OF_READ="user_read"
TABLE_NAME_OF_WANT="user_want"

HEADERS={
	"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
}

class Selector:
	BOOK="li.group__book"
	THUMB=".book__thumbnail"
	TITLE=".detail__title"
	DATE=".detail__date"
	AUTHOR=".detail__authors"
	PAGE=".detail__page"


def toData(book):
	thumb=book.select_one(Selector.THUMB)
	if thumb:
		img=thumb.find("img")
		imgUrl=img.get("src") if img else ""
	else:
		imgUrl=""
	title_e=book.select_one(Selector.TITLE)
	title=title_e.text if title_e else ""
	href=title_e.find("a").get("href") if title_e else ""
	date=book.select_one(Selector.DATE)
	date=date.text if date else ""
	author=book.select_one(Selector.AUTHOR)
	author=author.text if author else ""
	page=book.select_one(Selector.PAGE)
	page=page.text if page else ""
	return {
		"imgUrl":imgUrl,
		"title":title,
		"href":href,
		"date":date,
		"author":author,
		"page":page
	}
	

def ___getBooks(soup):
	return soup.select(Selector.BOOK)
def __getBooks(soup):
	return map(toData,___getBooks(soup))

def _getBooks(url,page=1,session=requests):
	params={
		"page":page
	}
	res=session.get(url,headers=HEADERS,params=params)
	soup=bs(res.text,"html.parser")
	return __getBooks(soup)
def getBooks(url,start=1,n=5):
	session=requests.Session()
	for page in range(start,start+n):
		data=list(_getBooks(url,page,session))
		if not data:
			return
		for dat in data:
			dat["href"]=up.urljoin(url,dat["href"])
			yield dat
		time.sleep(1)

def searchUsers(name):
	headers={
		**HEADERS,
		"refer":SEARCH_USERS_URL
	}
	params={
		"name":name
	}
	res=requests.get(SEARCH_USERS_URL,headers=HEADERS,params=params)
	#soup=bs(res.text,"html.parser")
	data=json.loads(res.text)
	return data["resources"]

def getUser(name):
	users=list(searchUsers(name))
	if not users:
		return None

	for user in users:
		if re.fullmatch(name,user["name"]):
			return user
	return None
class _User:
	URL=URL+"/users/{0}"
	class Type:
		WANT="wish"
		READ="read"
		READING="reading"
	def __init__(self,name):
		self.name=name
		self.id=self.getid(name)
		if not self.id:
			raise Exception("Don't find id of {0}.".format(self.name))
	@staticmethod
	def getid(name):
		user=getUser(name)
		return user["id"] if user else None
	@property
	def wanturl(self):
		return self.url+"/books/wish"
	@property
	def readurl(self):
		return self.url+"/books/read"
	@property
	def url(self):
		return self.URL.format(self.id)
		

DB_COLUMNS={
	"imgUrl":"text",
	"title":"text",
	"href":"text unique",
	"date":"text",
	"author":"text",
	"page":"text"
}

def _makeDBOfWant(db,user):
	data=getBooks(user.wanturl,n=10**32)
	mu.makeDB(db,TABLE_NAME_OF_WANT,DB_COLUMNS,map(lambda dat:list(dat.values()),data))
def _makeDBOfRead(db,user):
	data=getBooks(user.readurl,n=10**32)
	mu.makeDB(db,TABLE_NAME_OF_READ,DB_COLUMNS,map(lambda dat:list(dat.values()),data))

def makeDB(name,override=False):
	user=User(name)
	if not user:
		return False
	db_name=DB_NAME_F.format(name)
	if os.path.exists(db_name) and not override:
		return False
	db=sqlite3.connect(db_name)
	_makeDBOfWant(db,user)
	_makeDBOfRead(db,user)
	db.close()
	return True

class User(_User):	#User have db.
	def __init__(self,name):
		super().__init__(name)
		self.db=sqlite3.connect(DB_NAME_F.format(name))
	def makeDB(self):
		return makeDB(self.name,True)
	def _search(self,table_name,title="",author=""):
		cur=self.db.cursor()
		LIKE_F="%{0}%"
		sql='select * from {0} where title like "{1}" and author like "{2}"'.format(table_name,LIKE_F.format(title),LIKE_F.format(author))
		keys=DB_COLUMNS.keys()
		for row in cur.execute(sql):
			yield dict(zip(keys,row))
	def _searchWant(self,title="",author=""):
		return self._search(TABLE_NAME_OF_WANT,title,author)
	def _searchRead(self,title="",author=""):
		return self._search(TABLE_NAME_OF_READ,title,author)
	def search(self,title="",author=""):
		for data in self._searchWant(title,author):
			data["type"]=self.Type.WANT
			yield data
		for data in self._searchRead(title,author):
			data["type"]=self.Type.READ
			yield data
	def __enter__(self):
		return self
	def __exit__(self,*args,**kwargs):
		pass
	def close(self):
		self.db.close()


if __name__ == "__main__": 
	url="https://bookmeter.com/users/1035737/books/read"
	name="vectorcc"
	title=sys.argv[1]
	with User(name) as user:
		for book in user.search(title,""):
			print(book)
