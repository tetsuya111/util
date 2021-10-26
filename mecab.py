import subprocess as sp
import os
import sys
import random
import sys

ENCODING="sjis" if "nt" in sys.builtin_module_names else "utf8"

def tmpf():
	fname="__mecab_tmp{0}.txt".format(random.randint(4545,46494))
	return fname if not os.path.exists(fname) else tmpf()

class Mecab:
	def __init__(self,text):
		self.text=text
	def __call__(self):
		return Mecab.__analize__(self.text)
	@staticmethod
	def __analize__(text):
		tmp=tmpf()
		with open(tmp,"wb") as f:
			f.write(text.encode(ENCODING,"ignore"))
		try:
			for line in sp.check_output("type {0} | mecab".format(tmp),shell=True).decode(ENCODING,"ignore").split("\n"):
				data=line.split("\t",1)
				if not data[0]:
					pass
				elif data[0]=="EOS\r":
					yield ("EOS",None)
				else:
					data__=data[1].split(",")
					yield (data[0],data__)
		except:
			pass
		os.remove(tmp)

	@staticmethod
	def __getDataAsSentence__(text):	#res list include data
		sentence=list()
		for word,data in Mecab.__analize__(text):
			if word=="EOS" or (data and "\\xe3\\x80\\x82" in str(word.encode())):#str(data[1].encode())=="b\'\\xe5\\x8f\\xa5\\xe7\\x82\\xb9\'"):	#KUTEN
				yield sentence
				sentence=list()
			else:
				sentence.append((word,data))
	@staticmethod
	def getDataAsSentence(text):
		for sentence in Mecab.__getDataAsSentence__(text):
			yield "".join(map(lambda a:a[0],sentence))
	@staticmethod
	def getWords(text):
		for word,data in Mecab.__analize__(text):
			if word=="EOS" or (data and "\\xe3\\x80\\x82" in str(word.encode())):
				continue
			yield word
