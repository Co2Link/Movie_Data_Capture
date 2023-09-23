# -*- coding: utf-8 -*-

import re
from lxml import etree
from .httprequest import request_session
from .parser import Parser
from functools import lru_cache


class Msin(Parser):
    source = 'msin'

    expr_number = '//div[@class="mv_fileName"]/text()'
    expr_title = '//div[@class="mv_title"]/text()'
    expr_title_unsubscribe = '//div[@class="mv_title unsubscribe"]/text()'
    expr_studio = '//a[@class="mv_writer"]/text()'
    expr_director = '//a[@class="mv_writer"]/text()'
    expr_actor = '//div[contains(text(),"出演者：")]/following-sibling::div[1]/div/div[@class="performer_text"]/a/text()'
    expr_label = '//a[@class="mv_mfr"]/text()'
    expr_series = '//a[@class="mv_mfr"]/text()'
    expr_release = '//a[@class="mv_createDate"]/text()'
    expr_cover = '//div[@class="movie_top"]/img/@src'
    expr_tags = '//div[@class="mv_tag"]/label/text()'
    expr_genres = '//div[@class="mv_genre"]/label/text()'
    expr_actorphoto = '//div[contains(text(),"出演者：")]/following-sibling::div[1]/div/div[@class="performer_image"]/a/img/@src'

    # expr_outline = '//p[@class="fo-14"]/text()'
    # expr_extrafanart = '//*[@class="item-nav"]/ul/li/a/img/@src'
    # expr_extrafanart2 = '//*[@id="cart_quantity"]/table/tr[3]/td/div/a/img/@src'

    def extraInit(self):
        self.imagecut = 4

    def search(self, number: str):
        self.number = number.lower()
        is_fc2 = False
        if 'fc2' in self.number:
            self.number = "fc2-ppv-" + max(re.findall(r'\d+', self.number), key=len)
            is_fc2 = True
        elif any([prefix in self.number for prefix in ['ibw', 'aoz']]):
            if self.number[-1] == 'z':
                self.number = self.number[:-1]
        elif re.match(r'^[\d]+-[\d]+$', self.number):
            self.number = self.number.replace('-', '_')
        self.cookies = {"age": "off"}
        self.session = request_session(cookies=self.cookies, proxies=self.proxies, verify=self.verify)
        # search domestic
        if not is_fc2:
            print('[!] Search domestic')
            self.detailurl = f'https://db.msin.jp/branch/search?sort=jp.movie&str={self.number}'
            htmlcode = self.session.get(self.detailurl).text
        # search oversea
        if is_fc2 or 'No Results' in htmlcode or'Not Found' in htmlcode:
            print('[!] Search oversea')
            self.detailurl = f'https://db.msin.jp/branch/search?sort=movie&str={self.number}'
            htmlcode = self.session.get(self.detailurl).text

        htmltree = etree.HTML(htmlcode)
        # mutiple search results
        if '上限99件' in htmlcode:
            print('[!] Mutiple results!')
            unique_names = self.getTreeAll(htmltree, "//*[@id='bottom_content']//span[@class='movie_pn']/text()")
            if unique_names and len(set(unique_names)) == 1:
                print('[!] All results point to the same movie, choose the first one as target.')
                target_url = self.getTreeAll(htmltree, "//*[@id='bottom_content']//a[.//img]/@href")[0]
                self.detailurl = f'https://db.msin.jp/{target_url}'
                htmlcode = self.session.get(self.detailurl).text
                htmltree = etree.HTML(htmlcode)
            else:
                print('[!] Not sure which one to choose as result.')
                return 404

        # if title are null, use unsubscribe title
        if super().getTitle(htmltree) == "":
            self.expr_title = self.expr_title_unsubscribe
        # if tags are null, use genres
        if len(super().getTags(htmltree)) == 0:
            self.expr_tags = self.expr_genres
        if len(super().getActors(htmltree)) == 0:
            self.expr_actor = self.expr_director
        self.number = self.number.upper()
        result = self.dictformat(htmltree)
        return result
    
    def getActorPhoto(self, htmltree):
        actor_photos = self.getTreeAll(htmltree, self.expr_actorphoto)
        actor_names = self.getActors(htmltree)
        return {name:photo for name, photo in zip(actor_names, actor_photos)}

    @lru_cache(maxsize=None)
    def getActors(self, htmltree):
        def get_actor_unique_name(actor_url):
            htmlcode = self.session.get(f'https://db.msin.jp{actor_url}').text
            ret = self.getTreeAll(etree.HTML(htmlcode), '//*[@id="top_content"]/h2/div[2]/span/text()')
            return ret[0] if ret else None
        actors = super().getActors(htmltree)
        actor_urls = self.getTreeAll(htmltree, '//div[contains(text(),"出演者：")]/following-sibling::div[1]/div/div[@class="performer_text"]/a/@href')
        ret = []
        for actor_name, actor_url in zip(actors, actor_urls):
            actor_unique_name = get_actor_unique_name(actor_url)
            if actor_unique_name is None:
                breakpoint()
            ret.append(actor_unique_name if actor_unique_name else actor_name)
        return ret

    def getTags(self, htmltree) -> list:
        return super().getTags(htmltree)

    def getRelease(self, htmltree):
        return super().getRelease(htmltree).replace('年', '-').replace('月', '-').replace('日', '')

    def getCover(self, htmltree):
        if ".gif" in super().getCover(htmltree) and len(super().getExtrafanart(htmltree)) != 0:
            return super().getExtrafanart(htmltree)[0]
        return super().getCover(htmltree)

    def getNum(self, htmltree):
        return self.number
