import api
import json
import sys

query=sys.argv[1]
for data in api.searchN(query,start=2,n=2):
	print(json.dumps(data,indent=4,ensure_ascii=False))
