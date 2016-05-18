import urllib
from bs4 import BeautifulSoup
import re
from ParseCommon import curr_date
from ParseCommon import Parser
from ParseCommon import start_search_msg, finish_search_msg, cancel_search_msg
import socket

import datetime


class ParserBoardIsra(Parser):
    index = None

    def __init__(self):
        super().__init__('http://www.boardisra.com/')

    def run(self):
        self.set_status(start_search_msg)
        self.running = True
        self.load_phones()
        self.running = False
        if self.is_canceled:
            self.set_status(cancel_search_msg)
        else:
            self.set_status(finish_search_msg)

    def parse_detail(self, url):
        detail_url_open = False
        while not detail_url_open:
            if self.is_canceled:
                return True
            try:
                html_src = urllib.request.urlopen(url).read()
                soup = BeautifulSoup(html_src, 'html.parser')
                detail_url_open = True

                for date_item in re.findall('<font color="bordo">([0-9][0-9]\.[0-9][0-9]\.[0-9][0-9])</font>', str(soup), re.DOTALL):
                    if date_item.strip() == '':
                        continue
                    message_date = datetime.datetime.strptime(date_item.strip(), "%d.%m.%y")
                    if message_date < self.limit_date:
                        return False

                curr_name = ''
                for item in re.findall('<hr>.+?<br>(/+?)<br>', str(soup), re.DOTALL):
                    curr_name = item

                for phone_item in re.findall('([0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9])', str(soup).replace('-', '').replace(' ', ''), re.DOTALL):
                    for phone in Parser.get_phone(phone_item):
                        if Parser.save_phone_name(phone, curr_name):
                            self.inc_phone_count()
                    if self.is_canceled:
                        return True
                return True
            except (urllib.request.URLError, urllib.request.HTTPError, socket.timeout) as err:
                self.process_exception(err)
                self.inc_error_count()

    def parse_soup_message(self, soup):
        for a in soup.find_all('a'):
            if a['href'].startswith('idv.php?id='):
                if not self.parse_detail(self.base_url + a['href']):
                    return False
        if self.is_canceled:
            return True
        return True

    def get_next_page(self, url):
        curr_id = int(url[len(url)-url[::-1].find('='):])
        return self.base_url + '?pn=' + str(curr_id + 1)

    def parse_url(self, url):
        Parser.save_current_url(self.base_url, url, self.limit_date)
        print('Searching phones on', url)
        print('Limit date - ', self.limit_date)
        html_src = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(html_src, 'html.parser')
        if self.parse_soup_message(soup):
            return self.get_next_page(url)

    def load_phones(self):
        self.limit_date = Parser.get_current_date(self.base_url)
        start_time = datetime.datetime.today()
        url = self.base_url + '?pn=0'
        current_url = Parser.get_current_url(self.base_url)
        if current_url != '':
            url = current_url
            print('Restoring previous session..')

        while not (url is None):
            if self.is_canceled:
                break
            try:
                url = self.parse_url(url)
            except (urllib.request.URLError, urllib.request.HTTPError, socket.timeout, ConnectionResetError) as err:
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
        p = ParserBoardIsra()
        p.start()
        p.join()
    finally:
        Parser.close_shelves()
