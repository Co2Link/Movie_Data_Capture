# -*- coding: utf-8 -*-

import re
from lxml import etree
from .httprequest import request_session
from .parser import Parser
from .utils import UniqueNameFinder
from functools import lru_cache
from scrapinglib.javbus import Javbus
import json
import urllib


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

    
    def is_not_found(self, htmlcode: str):
        return 'No Results' in htmlcode or 'Not Found' in htmlcode

    def extraInit(self):
        # for javbus
        self.specifiedSource = None
        self.session = request_session(cookies={"age": "off"}, proxies=self.proxies, verify=self.verify)
        self.imagecut = 4
        self.unique_name_finder = UniqueNameFinder()

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
        # search domestic
        if not is_fc2:
            print('[!] Search domestic')
            self.detailurl = f'https://db.msin.jp/branch/search?sort=jp.movie&str={self.number}'
            htmlcode = self.session.get(self.detailurl).text
        # search oversea
        if is_fc2 or self.is_not_found(htmlcode):
            print('[!] Search oversea')
            self.detailurl = f'https://db.msin.jp/branch/search?sort=movie&str={self.number}'
            htmlcode = self.session.get(self.detailurl).text
            # TODO: fix 年齢確認

        htmltree = etree.HTML(htmlcode)
        # mutiple search results
        if '上限99件' in htmlcode:
            print('[!] Mutiple results!')
            unique_names = self.getTreeAll(htmltree, "//*[@id='bottom_content']//span[@class='movie_pn']/text()")
            if unique_names and len(set(unique_names)) == 1:
                print('[!] All results point to the same movie, choose the first one as target.')
                target_url = self.getTreeAll(htmltree, "//*[@id='bottom_content']//a[.//img]/@href")[0]
                self.detailurl = f'https://db.msin.jp{target_url}'
                htmlcode = self.session.get(self.detailurl).text
                htmltree = etree.HTML(htmlcode)
            else:
                print('[!] Not sure which one to choose as result.')
                return 404
        elif self.is_not_found(htmlcode):
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
        actors = super().getActors(htmltree)
        actor_urls = self.getTreeAll(htmltree, '//div[contains(text(),"出演者：")]/following-sibling::div[1]/div/div[@class="performer_text"]/a/@href')
        actor_names = []
        for actor_name, actor_url in zip(actors, actor_urls):
            actor_unique_name = self.unique_name_finder.get_actor_unique_name(actor_url)
            if actor_unique_name is None:
                breakpoint()
            actor_names.append(actor_unique_name if actor_unique_name else actor_name)
        # There are cases where actor names can be found in Javbus but not in Msin for some movies
        if not actor_names:
            print('[!] Try to search in Javbus to retrieve actor names')
            jav_engine = Javbus()
            result = jav_engine.scrape(self.number, self)
            if result != 404:
                result = json.loads(result)
                actor_names = result['actor']
                if actor_names:
                    print(f'[!] Actor names{actor_names} found in Javbus for {self.number}')
                    for i in range(len(actor_names)):
                        name = actor_names[i]
                        unique_name = self.unique_name_finder.search_actor_unique_name(name)
                        if unique_name and unique_name != name:
                            actor_names[i] = unique_name
                            print(f'[!] Successfully replace {name} with {unique_name}')
                        elif not unique_name:
                            print(f'[!] Can not find actor {name} in Msin')
                            
        director = self.getDirector(htmltree)
        if not actor_names and director:
            print(f'[!] Use director name {director} as actor name')
            return director
        return actor_names

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
