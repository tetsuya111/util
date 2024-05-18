import selenium.webdriver as wd
import urllib
from myutil import site
import _pyio
import time

def getDriver(browser=wd.Chrome,headless=True):
	options=wd.ChromeOptions()
	options.headless=headless
	driver=browser(options=options)
	return driver


GET_ENTRIES="return performance.getEntries()"
def getEntries(driver):
	return driver.execute_script(GET_ENTRIES)

def getM3U8(driver):
	for entry in getEntries(driver):
		pass


def getVideoInM3U8(url,m3u8_text):
	def getTSUrl(m3u8_text):
		for line in m3u8_text.split("\n"):
			if not line or line[0] == "#":
				continue
			yield line
	data=_pyio.BytesIO()
	for tsurl in getTSUrl(m3u8_text):
		vurl=urllib.urljoin(url,tsurl)
		data+=site.__download__(vurl)
	return data


	

class Downloader(site.Driver):
	GET_VIDEO_SLEEP=2
	def getM3U8(self,url):
		return getM3U8(self.driver,url)
	def clickVideo(self):
		pass
	def getVideo(self,url):
		self.get(url)
		time.sleep(GET_VIDEO_SLEEP)
		self.clickVideo()
		m3u8=getM3U8(self.driver)
		if not m3u8:
			return None
		return getVideoInM3U8(m3u8)
	def __enter__(self):
		return self
	def __exit__(self,*args,**kwargs):
		self.quit()
	@staticmethod
	def getD(headless=True):
		options=wd.ChromeOptions()
		options.headless=headless
		return Downloader(options=options)
	def getEntries(self):
		return getEntries(self)
	def getNetWorks(self):
		script="return getConnection()"
		return self.execute_script(script)
		
