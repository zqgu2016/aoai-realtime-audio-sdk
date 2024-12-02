import asyncio
import os

import aiohttp
from bs4 import BeautifulSoup


async def bing_search(query, subscription_key):
    url = f"https://api.bing.microsoft.com/v7.0/custom/search?q={query}&mkt=zh-CN&customconfig=0"
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Error: {response.status}, {await response.text()}")


async def fetch_url_info(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), "html.parser")

                content = soup.text
                while content.find("\n\n") >= 0:  # remove unnecessary empty lines
                    content = content.replace("\n\n", "\n")

                return content
    except Exception as e:
        return None, str(e)


async def search_from_web(query: str) -> str:
    """
    Search up-to-date or additional information from web.

    Args:
        query (str): User query to search from web.

    Returns:
        str: The search results.
    """
    try:
        subscription_key = os.environ.get("BING_SEARCH_KEY")
        results = await bing_search(query, subscription_key)

        # 获取前3条结果
        web_pages = results["webPages"]["value"][:3]

        # 创建任务列表
        tasks = []
        for result in web_pages:
            tasks.append(fetch_url_info(result["url"]))

        # 等待所有任务完成
        urls_info = await asyncio.gather(*tasks)

        result_pages = []
        for idx, result in enumerate(web_pages):
            one_page = f'<Webpage url="{result["url"]}" title="{result["name"]}" snippet="{result["snippet"]}">\n{urls_info[idx]}\n</Webpage>'
            result_pages.append(one_page)
        result_content = "\n".join(result_pages)
        return f"<Search_Results>\n{result_content}\n</Search_Results>"

    except Exception as e:
        print(e)
        return "Sorry. I' not able to browse the web now."


signature_search_from_web = {
    "name": "search_from_web",
    "type": "function",
    "description": "Search up-to-date or additional information from web.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "user query to search from web.",
            }
        },
        "required": ["query"],
    },
}


if __name__ == "__main__":

    async def main():
        query = "最近有什么好看的电影上映?"
        result = await search_from_web(query)
        print(result)

    asyncio.run(main())
