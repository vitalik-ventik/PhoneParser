import urllib
from bs4 import BeautifulSoup
import re
from ParseCommon import curr_date
from ParseCommon import Parser
from ParseCommon import start_search_msg, finish_search_msg, cancel_search_msg
import socket

import datetime


class ParserOrbita(Parser):
    index = None

    def __init__(self):
        super().__init__('http://doska.orbita.co.il/')

    def run(self):
        self.set_status(start_search_msg)
        self.running = True
        self.load_orbita_phones()
        self.running = False
        if self.is_canceled:
            self.set_status(cancel_search_msg)
        else:
            self.set_status(finish_search_msg)

    def parse_soup_reg(self, soup):
        for item in soup.find_all('div', class_="col-xs-24"):
            for row_date in re.findall('<div class="col-sm-7 col-xs-5 message-vip">(.+?)</div>', str(item), re.DOTALL):
                if row_date.strip() == '':
                    continue
                if row_date.find('Это VIP объявление') == -1:
                    message_date = datetime.datetime.strptime(row_date.strip(), "%d.%m.%Y")
                    if message_date < self.limit_date:
                        return False

            for phone in re.findall('<div class="col-md-8 col-xs-12 col-md-pull-8">(.+?)</div>', str(item), re.DOTALL):
                for phone_item in Parser.get_phone(phone):
                    if Parser.save_phone_name(phone_item, ''):
                        self.inc_phone_count()
            if self.is_canceled:
                return True
        return True

    def get_next_page(self, soup):
        for item in soup.select('a[title^="Следующая"]'):
            pages_soup = BeautifulSoup(str(item), 'html.parser')
            for link in pages_soup.find_all('a'):
                return link['href']
        return None

    def parse_url(self, url):
        Parser.save_current_url(self.base_url, url, self.limit_date)
        print('Searching phones on', url)
        print('Limit date - ', self.limit_date)
        html_src = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(html_src, 'html.parser')
        if self.parse_soup_reg(soup):
            return self.get_next_page(soup)

    def load_orbita_phones(self):
        self.limit_date = Parser.get_current_date(self.base_url)
        start_time = datetime.datetime.today()
        url = self.base_url
        current_url = Parser.get_current_url(self.base_url)
        if current_url != '':
            url = current_url
            print('Restoring previous session..')

        while not (url is None):
            if self.is_canceled:
                break
            try:
                url = self.parse_url(url)
            except (urllib.request.URLError, urllib.request.HTTPError, socket.timeout) as err:
                self.process_exception(err)
                self.inc_error_count()
                continue
            self.inc_page_count()

        Parser.save_current_url(self.base_url, '', self.limit_date)
        print('Start time:', start_time)
        print('End time:', datetime.datetime.today())


if __name__ == '__main__':
    try:
        Parser.init_shelves()
        Parser.limit_date_for_search = curr_date()
        parser_orbita = ParserOrbita()
        parser_orbita.start()
        parser_orbita.join()
    finally:
        Parser.close_shelves()
