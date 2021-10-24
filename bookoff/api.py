import requests
from bs4 import BeautifulSoup as bs
import urllib.parse as up
import sys
import re
import time

SEARCH_URL="https://www.bookoffonline.co.jp/disp/CSfSearch.jsp"

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
	encoding="sjis"
	query=query.encode(encoding)
	params={
		"name":"search_form",
		"q":query,
		"st":"",
		"p":page,
		"bg":type_
	}
	headers={ "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36"}
	res=session.get(SEARCH_URL,headers=headers,params=params)
	res.encoding=encoding
	return res.text

def toData(l):
	ttl=l.select_one(".itemttl")
	title=ttl.text
	a=ttl.find("a")
	url=a.get("href")
	stocked=not l.select_one(".nostockbtn")
	mainprice=l.select_one(".mainprice")
	price=mainprice.text
	price=re.search("[\d,]+",price)
	price=price.group()
	price=int(price.replace(",",""))
	author=l.select_one(".author")
	author=author.text
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

