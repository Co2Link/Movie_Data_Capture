# -*- coding: utf-8 -*-

from lxml.html import HtmlElement
from scrapinglib.httprequest import request_session
from lxml import etree
import urllib

def getTreeElement(tree: HtmlElement, expr='', index=0):
    """ 根据表达式从`xmltree`中获取匹配值,默认 index 为 0
    :param tree (html.HtmlElement)
    :param expr 
    :param index
    """
    if expr == '':
        return ''
    result = tree.xpath(expr)
    try:
        return result[index]
    except:
        return ''

def getTreeAll(tree: HtmlElement, expr='') -> list[str] | str:
    """ 根据表达式从`xmltree`中获取全部匹配值
    :param tree (html.HtmlElement)
    :param expr 
    :param index
    """
    if expr == '':
        return []
    result = tree.xpath(expr)
    try:
        return result
    except:
        return []


class UniqueNameFinder:
    def __init__(self):
        self.session = request_session(cookies={"age": "off"})
        self.expr_actor_unique_name = '//*[@id="top_content"]/h2/div[2]/span/text()'
    
    def get_actor_unique_name(self, actor_url: str):
        htmlcode = self.session.get(f'https://db.msin.jp{actor_url}').text
        actor_unique_name = getTreeAll(etree.HTML(htmlcode), self.expr_actor_unique_name)
        return actor_unique_name[0] if actor_unique_name else None

    def is_not_found(self, htmlcode: str):
        return 'No Results' in htmlcode or 'Not Found' in htmlcode

    def search_actor_unique_name(self, actor_name: str):
        def _search(is_domestic):
            htmlcode = self.session.get(f'https://db.msin.jp/branch/search?sort={"jp." if is_domestic else ""}actress&str={urllib.parse.quote_plus(actor_name)}').text
            if self.is_not_found(htmlcode):
                return None
            # Mutiple matches for this actor_name, select the first one as result
            if '検索結果' in htmlcode:
                actor_url = getTreeAll(etree.HTML(htmlcode), '//div[@class="actress_view"]/div[1]//div[@class="act_image"]/a/@href')[0]
                return self.get_actor_unique_name(actor_url)
            else:
                name = getTreeAll(etree.HTML(htmlcode), self.expr_actor_unique_name)
                return name[0] if name else None 
        
        unique_name = _search(is_domestic=True)
        if not unique_name:
            unique_name = _search(is_domestic=False)

        return unique_name