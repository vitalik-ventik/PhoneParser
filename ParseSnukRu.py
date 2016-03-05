import urllib
from bs4 import BeautifulSoup, UnicodeDammit
import re
from ParseCommon import curr_date
from ParseCommon import Parser
from ParseCommon import start_search_msg, finish_search_msg, cancel_search_msg
import socket

import datetime


class ParserSnukRu(Parser):
    index = None

    def __init__(self):
        super().__init__('http://www.shuk-ru.com/')

    def run(self):
        self.set_status(start_search_msg)
        self.running = True
        self.load_snukru_phones()
        self.running = False
        if self.is_canceled:
            self.set_status(cancel_search_msg)
        else:
            self.set_status(finish_search_msg)

    def parse_soup(self, soup):
        for soup_row in soup.select('tr[style="cursor:hand"]'):
            for row_date in re.findall('<a class="a1".+?([0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]).+?</a>', str(soup_row), re.DOTALL):
                message_date = datetime.datetime.strptime(row_date.strip(), "%d-%m-%Y")
                if message_date < self.limit_date:
                    return False

            curr_name = ''
            for row_name in re.findall('<u>.+?class="spop".+?>(.+?)</a>', str(soup_row), re.DOTALL):
                if '<span' in row_name:
                    row_name = row_name[:row_name.find('<span') - 1]
                curr_name = row_name.strip()

            for phone_row in re.findall('<span class="apop2">.+?<td.+?>(.+?)</td>', str(soup_row), re.DOTALL):
                for phone in re.findall('[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]', phone_row.replace('-', '').replace(' ', ''), re.DOTALL):
                    if Parser.save_phone_name(phone, curr_name):
                        self.inc_phone_count()
            if self.is_canceled:
                return True
        return True

    def load_snukru_phones(self):
        self.limit_date = Parser.get_current_date(self.base_url)
        print('Searching phones on ', self.base_url)
        print('Limit date - ', self.limit_date)

        curr_page = Parser.get_current_url(self.base_url)
        if curr_page != '':
            print('Restoring previous session..')
        else:
            curr_page = 1

        url = self.base_url

        while url is not None:
            if self.is_canceled:
                break
            print('Searching on page #', curr_page)
            Parser.save_current_url(self.base_url, curr_page, self.limit_date)
            try:
                params = bytes(urllib.parse.urlencode({curr_page: curr_page}).encode())
                url = urllib.request.Request(self.base_url, params)
                html_src = urllib.request.urlopen(url).read()
            except (urllib.request.URLError, urllib.request.HTTPError, socket.timeout) as err:
                self.process_exception(err)
                self.inc_error_count()
                continue

            dammit = UnicodeDammit(html_src, ["windows-1251"])
            html_src = dammit.unicode_markup
            soup = BeautifulSoup(html_src, 'html.parser')

            if self.parse_soup(soup) is True:
                curr_page += 1
                if not soup.find_all('input', class_='page', attrs={"id": str(curr_page)}):
                    url = None
            else:
                url = None
            self.inc_page_count()
        Parser.save_current_url(self.base_url, '', self.limit_date)

if __name__ == '__main__':
    try:
        Parser.init_shelves()
        Parser.limit_date_for_search = curr_date()
        parser_snukru = ParserSnukRu()
        parser_snukru.start()
        parser_snukru.join()
    finally:
        Parser.close_shelves()
