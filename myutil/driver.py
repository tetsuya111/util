from pyppeteer import launch
import asyncio
import sys
import io

sys.stdout=io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def getHTMLOfE(page,e):
	return await page.evaluate("(e)=>e.outerHTML",e)

async def getHTML(page):
	head=await page.J("head")
	head=await getHTMLOfE(page,head) if head else ""
	body=await page.J("body")
	body=await getHTMLOfE(page,body) if body else ""
	return head + body

if __name__=="__main__":
	async def test():
		url="https://gcolle.net/product_info.php/products_id/706980"
		browser=await launch()
		page=await browser.newPage()
		await page.goto(url)
		html=await getHTML(page)
		print(html)
		await browser.close()
	asyncio.get_event_loop().run_until_complete(test())
