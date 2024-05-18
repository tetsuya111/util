import requests
from bs4 import BeautifulSoup as bs
import time
import urllib.parse as up
from myutil import site
import json

HOST="bookmeter.com"
URL="https://"+HOST

SEARCH_URL=f"{URL}/search?keyword={{0}}"
SEARCH_USERS_URL=URL+"/users/search"

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
	res=session.get(url,headers=site.HEADERS,params=params)
	soup=bs(res.text,"html.parser")
	return __getBooks(soup)
def getBooks(url,start=1,n=5):
	session=requests.Session()
	for page in range(start,start+n):
		data=list(_getBooks(url,page,session))
		print("YYY",data)
		if not data:
			return
		for dat in data:
			dat["href"]=up.urljoin(url,dat["href"])
			yield dat
		time.sleep(1)

def search(kw="",start=1,n=5):
    url=SEARCH_URL.format(up.quote(kw))
    return getBooks(url,start=start,n=n)

def searchUsers(name):
	headers={
		**site.HEADERS,
		"refer":SEARCH_USERS_URL
	}
	params={
		"name":name
	}
	res=requests.get(SEARCH_USERS_URL,headers=site.HEADERS,params=params)
	#soup=bs(res.text,"html.parser")
	data=json.loads(res.text)
	return data["resources"]

class User:
	URL=URL+"/users/{0}"
	class Type:
		WANT="wish"
		READ="read"
		READING="reading"
	def __init__(self,userid):
		self.id=userid
	@property
	def url(self):
		return self.URL.format(self.id)
	def getBooks(self,type_,start=1,n=5):
		url=self.url+"/books/"+type_
		return getBooks(url,start,n)
	@staticmethod
	def make(name):
		users=list(searchUsers(name))
		if not users:
			return None

		for user in users:
			if user["name"] == name:
				return User(user["id"])
		return None
		



if __name__ == "__main__": 
	url="https://bookmeter.com/users/1035737/books/read"
	for book in getBooks(url,1):
		print(book)
