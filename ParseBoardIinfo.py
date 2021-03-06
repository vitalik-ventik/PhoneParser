import urllib
from bs4 import BeautifulSoup
import re
from ParseCommon import curr_date
from ParseCommon import Parser
from ParseCommon import start_search_msg, finish_search_msg, cancel_search_msg
import socket

import datetime


class ParserBoardIinfo(Parser):
    index = None

    def __init__(self):
        super().__init__('http://board.iinfo.co.il/')

    def run(self):
        self.set_status(start_search_msg)
        self.running = True
        self.load_phones()
        self.running = False
        if self.is_canceled:
            self.set_status(cancel_search_msg)
        else:
            self.set_status(finish_search_msg)

    def parse_soup_message_item(self, item):
        item = str(item)

        for row_date in re.findall('ID,Date,Time.+?([0-9][0-9]\.[0-9][0-9]\.[0-9][0-9][0-9][0-9]).+?Text', item, re.DOTALL):
            row_date = row_date.strip()
            if row_date == '':
                continue
            message_date = datetime.datetime.strptime(row_date, "%d.%m.%Y")

            if message_date < self.limit_date:
                return False

        curr_name = ''
        for name in re.findall('>Имя: (.+?)</div>', item, re.DOTALL):
            curr_name = name.strip()

        for phone_item in re.findall('([0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9])', item.replace('-', '').replace(' ', ''), re.DOTALL):
            for phone in Parser.get_phone(phone_item):
                if Parser.save_phone_name(phone, curr_name):
                    self.inc_phone_count()
        return True

    def parse_soup_message(self, soup):
        for item in soup.find_all('table', {"class": lambda l: l and l in ('b11', 'test3', 'border7')}):
            if not self.parse_soup_message_item(item):
                return False
        if self.is_canceled:
            return True
        return True

    def get_next_page(self, soup):
        for item in soup.find_all('a', {'title': 'Next page'}):
            return self.base_url + item['href']
        return None

    def parse_url(self, url):
        Parser.save_current_url(self.base_url, url, self.limit_date)
        print('Searching phones on', url)
        print('Limit date - ', self.limit_date)
        html_src = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(html_src, 'html.parser')
        if self.parse_soup_message(soup):
            return self.get_next_page(soup)

    def load_phones(self):
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
        return True

if __name__ == '__main__':
    try:
        Parser.init_shelves()
        Parser.limit_date_for_search = curr_date()
        p = ParserBoardIinfo()
        p.start()
        p.join()
    finally:
        Parser.close_shelves()
