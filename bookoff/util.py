from . import api
import re

ALL_LEFT_KAKKO='\xef\xbc\x88'	#"(" of all
ALL_SPACE='\xe3\x80\x80'	#" " of all
U_SPACE="\u3000"
NBSP="\xa0"	#&nbsp
GET_TITLE_F_2=("{3}"+"[\({0} {1}{2}{4}].*").format(ALL_LEFT_KAKKO,NBSP,ALL_SPACE,"{0}",U_SPACE)
def get(title,author,type_=api.SearchType.BOOK,n=3):
	title=re.escape(title)
	def matchtitle(data_title):
		if re.fullmatch(title,data_title):
			return True
		if re.fullmatch(GET_TITLE_F_2.format(title),data_title):
			return True
		return False
	for data in api.searchN(title,start=1,n=n,type_=type_):
		if matchtitle(data["title"]) and re.fullmatch(author,data["author"]):
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
	def addCard(self,title,author=".*"):
		bookid=getid(title,author)
		return super().addCard(bookid)
	def addBM(self,title,author=".*"):
		bookid=getid(title,author)
		return super().addBM(bookid)
