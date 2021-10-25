from selenium import webdriver as wd

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
			#options.use_chromium = True
			return cls(options=options)
		except Exception as e:
			print(e)
		return None
	def getEntries(self):
		return getEntries(self)

