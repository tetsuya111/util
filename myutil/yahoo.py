import selenium.webdriver as wd
from bs4 import BeautifulSoup as bs
import urllib.parse
from . import site

#ex) http://search.yahoo.co.jp/search?ei=UTF-8&fr=mcafeess1&p=kkk

HOST="yahoo.co.jp"
URL="https://"+HOST
SEARCH_URL="https://search.{0}/search".format(HOST)


def toData(a):
	return {
		"href":a.get("href"),
		"title":a.text
	}

def _search(driver,query="",page=1):
	params={
		"q":query,
		"page":page
	}
	url=SEARCH_URL+"?"+site.joinParams(params)
	driver.get(url)
	for a in driver.find_elements_by_css_selector("a"):
		try:
			a=bs(a.text,"html.parser")
		except Exception as e:
			print(e)
			continue
		yield a

def search(driver,query="",page=1):
	return map(lambda a:toData(a),_search(driver,query,page))

def searchN(driver,start=1,n=1):
	for page in range(start,start+n):
		for data in search(driver,page):
			yield data

