import requests
from bs4 import BeautifulSoup as bs
import urllib.parse as up
import sys
import re
import time


HOST="www.bookoffonline.co.jp"
URL="https://"+HOST
SEARCH_URL=URL+"/disp/CSfSearch.jsp"
LOGIN_URL=URL+"/common/CSfLogin.jsp"
ADD_CARD_URL=URL+"/disp/CSfAddSession_001.jsp"
ADD_BM_URL=URL+"/member/BPmAddBookMark.jsp"

HEADERS={ "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36"}

ENCODING="sjis"


class SearchType:
	ALL=""
	BOOK=12
	PRATICAL_BOOK=1201
	MAGAZINE="13"
	CD=31
	DVD=71
	GAME=51
	ELSE=81
	SET="set"

def _search(query,page=1,type_=SearchType.BOOK,session=requests):
	query=query
	query=query.encode(ENCODING)
	params={
		"name":"search_form",
		"q":query,
		"st":"",
		"p":page,
		"bg":type_
	}
	res=session.get(SEARCH_URL,headers=HEADERS,params=params)
	res.encoding=ENCODING
	return res.text

def toData(l):
	ttl=l.select_one(".itemttl")
	title=ttl.text.strip()
	a=ttl.find("a")
	url=a.get("href")
	stocked=not l.select_one(".nostockbtn")
	mainprice=l.select_one(".mainprice")
	price=mainprice.text
	price=re.search("[\d,]+",price)
	price=price.group()
	price=int(price.replace(",",""))
	author=l.select_one(".author")
	author=author.text.strip()
	return {
		"title":title,
		"url":url,
		"author":author,
		"price":price,
		"stocked":stocked
	}


def getData(soup):
	for l in soup.select(".list_group"):
		yield toData(l)
def search(query,page=1,type_=SearchType.BOOK,session=requests):
	text=_search(query,page,type_,session)
	soup=bs(text,"html.parser")
	for data in getData(soup):
		data["url"]=up.urljoin(SEARCH_URL,data["url"])
		yield data

def searchN(query,start=1,n=1,type_=SearchType.BOOK):
	session=requests.Session()
	for page in range(start,start+n):
		dataa=list(search(query,page,type_,session))
		if not dataa:
			return
		for data in dataa:
			yield data
		time.sleep(1)

def isloginurl(text):
	return "MemberForm" in text

def login(session,mail,pw):
	params={
		"name":"MemberForm",
		"ID":mail,
		"PWD":pw
	}
	res=session.get(LOGIN_URL,headers=HEADERS,params=params)
	return not isloginurl(res.text)


def addCard(session,bookid):
	params={
		"iscd":bookid,
		"st":1
	}
	return session.get(ADD_CARD_URL,params=params)

def addBM(session,bookid):
	params={
		"iscd":bookid,
		"st":1
	}
	return session.get(ADD_BM_URL,params=params)

class Client:
	def __init__(self,mail="",pw=""):
		self.session=requests.Session()
		self.__logined=False
		if mail and pw:
			self.login(mail,pw)
	def __getattr__(self,attr):
		return getattr(self.session,attr)
	@property
	def logined(self):
		return self.__logined
	def login(self,mail,pw):
		self.__logined=login(self.session,mail,pw)
		return self.logined
	def addCard(self,bookid):
		if not self.logined:
			return False
		addCard(self.session,bookid)
	def addBM(self,bookid):
		if not self.logined:
			return False
		addBM(self.session,bookid)

