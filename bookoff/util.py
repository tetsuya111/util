from . import api
import re
import time

ALL_LEFT_KAKKO='\xef\xbc\x88'	#"(" of all
ALL_SPACE='\xe3\x80\x80'	#" " of all
U_SPACE="\u3000"
NBSP="\xa0"	#&nbsp
GET_TITLE_F_2=("{3}"+"[\({0} {1}{2}{4}].*").format(ALL_LEFT_KAKKO,NBSP,ALL_SPACE,"{0}",U_SPACE)

def search(query,title="",author="",priceFrom=0,priceUntil=10**32,onlyStocked=True,n=5,type_=api.SearchType.BOOK,timeout=30):
	i=0
	startTime=time.time()
	for data in api.searchN(query,n=10**32,type_=type_):
		if i >= n:
			break
		if time.time() - startTime > timeout:
			break
		if (not title or re.search(title,data["title"])) and \
			(not author or re.search(author,data["author"])) and \
			priceFrom <= data["price"] < priceUntil and \
			(not onlyStocked or data["stocked"]):
			yield data
			i+=1


def get(title,author,type_=api.SearchType.BOOK,n=10):
	title=re.escape(title)
	def matchtitle(data_title):
		if re.fullmatch(title,data_title):
			return True
		if re.fullmatch(GET_TITLE_F_2.format(title),data_title):
			return True
		return False
	for data in search(title,author="^"+author+"$",n=n,type_=type_):
		if matchtitle(data["title"]):
			return data
	return None

def getidInUrl(url):
	id_=re.search("/(?P<id>[0-9]+)$",url)
	return id_.group("id") if id_ else None

def getid(title,author=".*"):
	data=get(title,author)
	if not data:
		return None
	return getidInUrl(data["url"])

class Client(api.Client):
	def addCart(self,title,author=".*"):
		bookid=getid(title,author)
		if not bookid:
			return False
		return super().addCart(bookid)
	def addBM(self,title,author=".*"):
		bookid=getid(title,author)
		if not bookid:
			return False
		return super().addBM(bookid)

