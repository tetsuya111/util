import time
from . import driver
import requests
import urllib.parse as up

def getVurl(driver,url,close=True):
	driver.get(url)
	time.sleep(3)
	e=driver.select_one(".mgp_playerStateIcon")
	while not e.is_enabled():pass
	e.click()
	for entry in driver.getEntries():
		url=entry.get("name")
		#print("url",url)
		if not url:
			continue
		if ".m3u8" in url:
			if close:
				driver.close()
			return url
	if close:
		driver.close()
	return None

def _dlm3u8(url,session=None):
	if not session:
		session=requests.Session()
	res=session.get(url)
	for line in res.text.split("\n"):
		if not line:
			continue
		if line[0]=="#":
			continue
		vurl=up.urljoin(url,line)
		print("vurl",vurl)
		if ".m3u8" in vurl:
			for data in _dlm3u8(vurl,session=session):
				yield data
		elif ".ts" in vurl:
			res=session.get(vurl)
			yield res.content

def dlm3u8(url,fname):
	with open(fname,"wb") as f:
		for data in _dlm3u8(url):
			f.write(data)
