import requests
import time
import os
import sys
import ffmpeg
import colorama
import threading
import queue
import _pyio
import zlib
import imghdr
import selenium.webdriver as wd
import urllib.parse as up
from selenium.webdriver.remote.file_detector import FileDetector
import random
import re

colorama.init()

DOWNLOAD_TV=1

HEADERS={
	"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
}

def __requests_get__(res,*args,**kwargs):
	kwargs["stream"]=True
	print("args ",args,kwargs)
	for chunk in requests.get(*args,**kwargs):
		res.put(chunk)
def requests_get(*args,**kwargs):
	res=queue.Queue()
	t=threading.Thread(target=__requests_get__,args=[res,*args],kwargs=kwargs)
	t.start()
	while t.is_alive() or not res.empty():
		if not res.empty():
			yield res.get()


def __download__(url,cookies={},output=sys.stdout):
	if not url:
		return bytes()
	resV=_pyio.BytesIO()
	output.write("url "+url+"\n")
	data=requests.head(url)
	size=int(data.headers.get("Content-Length",-1))
	if not size:
            size=0.1
	output.write("{0} MB\n".format(size/1024/1024))
	chunked=0
	now=time.time()
	res=queue.Queue()
	headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"}
	ext=None
	for i,chunk in enumerate(requests_get(url,headers=headers,cookies=cookies)):
		if i == 0:
			ext=imghdr.what(None,h=chunk)
		resV.write(chunk)
		chunked+=128
		if time.time()-now > DOWNLOAD_TV:
			print("Downloaded %.1f %%\n\x1b[1A"%(chunked/size*100),end="")
			now=time.time()
	output.write("\nEnd donwloading!!\n")
	resV.seek(0)
	return {
		"data":resV.read(),
		"ext":ext
	}
	"""

	for chunk in requests.get(url,stream=True):
		chunked+=128
		f.write(chunk)
		if time.time()-now > DOWNLOAD_TV:
			#output.write("Downloaded {0} / {1}\n".format(chunked,size))
			#print("Downloaded {0} / {1}\n\x1b[1A".format(chunked,size),end="")
			print("Downloaded %.1f %%\n\x1b[1A"%(chunked/size*100),end="")
			now=time.time()
	"""

def download(url,fname,cookies={},output=sys.stdout,override=False,add_ext=False):
	if not override and os.path.exists(fname):
		return False
	output.write("Start donwloading to "+fname+" !!\n")
	res=__download__(url,output=output,cookies=cookies)
	if add_ext:
		ext=res["ext"] or "jpg"
		fname=f"{fname}.{ext}"
	with open(fname,"wb") as f:
		f.write(res["data"])
	return fname
class Video:
	host="google.com"
	MAIN=0
	def __init__(self,url):
		self.url=url
		self.__vurl=None
		self.__id=None
	@property
	def id(self):
		if not self.__id:
			self.__id="0"+str(zlib.adler32(self.url))
		return self.__id
	@property
	def vurl(self):
		return self.__vurl
	@property
	def fname(self):
		return self.id+".mp4"
	def download(self,dname="",output=sys.stdout,override=False):
		if not self.vurl:
			return False
		fname=os.path.join(dname,self.fname)
		return download(self.vurl,fname,output,override)


def getProperty(soup,name="",attr=""):
	data=soup.find(property=name+":"+attr)
	return data.get("content") if data else ""
def _getPropertyData(soup,name):
	for e in soup.find_all(property=re.compile(name+":.+")):
		yield (e.get("property"),e.get("content"))

def getPropertyData(soup,name):
	return dict(_getPropertyData(soup,name))

def getOGData(soup):
	return dict(_getPropertyData(soup,"og"))

GET_ENTRIES="return performance.getEntries()"
def getEntries(driver):
	return driver.execute_script(GET_ENTRIES)

class Driver(wd.Chrome):
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.__logined=False
	def select(self,css_selector):
		return self.find_elements_by_css_selector(css_selector)
	def select_one(self,css_selector):
		return self.find_element_by_css_selector(css_selector)
	def getheadhtml(self):
		head=self.select_one("head")
		return head.get_attribute("innerHTML")
	def getbodyhtml(self):
		body=self.select_one("body")
		return body.get_attribute("innerHTML")
	def gethtml(self):
		return self.getheadhtml()+self.getbodyhtml()
	@staticmethod
	def getD(headless=True,download_dir=None,cls=None):
		if not cls:
			cls=Driver
		try:
			options=wd.ChromeOptions()
			options.headless=headless
			if download_dir:
				prefs={"download.default_directory":download_dir}
			else:
				prefs={}
			options.add_experimental_option("prefs",prefs)
			options.add_experimental_option("excludeSwitches", ["enable-logging"])
			options.add_argument("--user-agent={0}".format(HEADERS["User-Agent"]))
			#options.use_chromium = True
			return cls(options=options)
		except Exception as e:
			print(e)
		return None
	def getEntries(self):
		return getEntries(self)

def joinParams(params):
	return "&".join(map(lambda k,v:k+"="+str(v),params.items()))

def upgetfname(url):
	fname=up.urlparse(url).path
	return os.path.basename(fname)

class TMP_F:
	def __init__(self,mode="w",encoding="utf8",name_format="{0}"):
		self.fname=self.getfname(name_format)
		if "b" in mode:
			self.f=open(self.fname,mode=mode)
		else:
			self.f=open(self.fname,mode=mode,encoding=encoding)
	def __getattr__(self,attr):
		return getattr(self.f,attr)
	@staticmethod
	def getfname(name_format="{0}"):
		fname=name_format.format("__xxx")
		while os.path.exists(fname):
			fname=name_format.format(str(random.randint(10**24,10**32)))
		return fname
	def close(self):
		self.f.close()
		os.remove(self.fname)
	def __iter__(self):
		return iter(self.f)
	def __enter__(self):
		return self
	def __exit__(self,*args,**kwargs):
		self.close()

