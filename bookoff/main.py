import api
import getpass
import requests

session=requests.Session()
mail="tetsuya1729@icloud.com"
pw=getpass.getpass()
logined=api.login(session,mail,pw)
print(logined)
