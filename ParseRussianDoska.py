import urllib
from bs4 import BeautifulSoup, UnicodeDammit
import re
from ParseCommon import curr_date
from ParseCommon import Parser
from ParseCommon import start_search_msg, finish_search_msg, cancel_search_msg
import socket

from _thread import start_new_thread
import html
import datetime


class ParserRussianDoska(Parser):
    index = None

    def __init__(self):
        super().__init__('http://www.russiandoska.com/cat/0-692/')
        self.num_threads = 0
        self.thread_started = False

    def run(self):
        self.num_threads = 0
        self.thread_started = False
        self.set_status(start_search_msg)
        self.running = True
        self.load_phones()
        self.running = False
        if self.is_canceled:
            self.set_status(cancel_search_msg)
        else:
            self.set_status(finish_search_msg)

    def parse_details(self, url):
        detail_url_open = False
        while not detail_url_open:
            if self.is_canceled:
                return True
            try:
                html_src = urllib.request.urlopen(url).read()
                dammit = UnicodeDammit(html_src, ["windows-1251"])
                html_src = dammit.unicode_markup
                detail_url_open = True
                curr_name = ''

                for phone_item in re.findall('([0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9])', str(html_src).replace('-', '').replace(' ', ''), re.DOTALL):
                    for phone in Parser.get_phone(phone_item):
                        if Parser.save_phone_name(phone, curr_name):
                            self.inc_phone_count()
                    if self.is_canceled:
                        return True
            except (urllib.request.URLError, urllib.request.HTTPError, socket.timeout) as err:
                self.process_exception(err)
                self.inc_error_count()

    def parse_category(self, url):
        self.limit_date = Parser.get_current_date(self.base_url)
        print('Searching phones on', url)
        print('Limit date - ', self.limit_date)
        Parser.lock.acquire()
        self.num_threads += 1
        self.thread_started = True
        Parser.lock.release()
        start_url = url

        current_url = Parser.get_current_url(start_url)
        if current_url != '':
            url = current_url
            print('Restoring previous session..')

        while not (url is None):
            if self.is_canceled:
                break
            Parser.save_current_url(start_url, url, self.limit_date)

            try:
                html_src = urllib.request.urlopen(url).read()
            except (urllib.request.URLError, urllib.request.HTTPError, socket.timeout) as err:
                self.process_exception(err)
                self.inc_error_count()
                continue

            soup = BeautifulSoup(html_src, 'html.parser')
            old_date_reached = False

            for item in soup.find_all('tr', {"class": 'table_ad_normal'}):
                a_item = item
                item = str(item).lower()
                for i, month in enumerate(['янв','фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']):
                    item = item.replace(' '+month+' ', '.' + str(i + 1).zfill(2) + '.')

                for date_item in re.findall('<td class="cell_embosed2 hide_for_mobile">([0-9][0-9]\.[0-9][0-9]\.[0-9][0-9][0-9][0-9])</td>', str(item), re.DOTALL):
                    if date_item.strip() == '':
                        continue
                    message_date = datetime.datetime.strptime(date_item.strip(), "%d.%m.%Y")
                    if message_date < self.limit_date:
                        old_date_reached = True
                        break
                if old_date_reached:
                    break
                elif self.is_canceled:
                    break

                for a in a_item.find_all('a'):
                    if 'html' in a['href']:
                        self.parse_details(self.base_url[:len(self.base_url) - 11] + a['href'])

            self.inc_page_count()
            if old_date_reached:
                url = None
            elif self.is_canceled:
                url = None
            else:
                url = None
                for div in soup.find_all('div', {'class': 'page_index'}):
                    for a in div.find_all('a'):
                        if a.text == '>':
                            url = a['href']
                            break

        Parser.save_current_url(start_url, '', self.limit_date)
        Parser.lock.acquire()
        self.num_threads -= 1
        print('Search is finished', start_url)
        print('Threads left:', self.num_threads)
        Parser.lock.release()

    def load_phones(self):
        start_time = datetime.datetime.today()
        main_page_open = False
        while not main_page_open:
            if self.is_canceled:
                break
            try:
                html_src = urllib.request.urlopen(self.base_url).read()
                main_page_open = True
            except (urllib.request.URLError, urllib.request.HTTPError, socket.timeout) as err:
                self.process_exception(err)
                self.inc_error_count()

        if main_page_open:
            cat_soup = BeautifulSoup(html_src, 'html.parser')
            cat_list = list()
            for group in cat_soup.find_all("div", class_="index_category_title"):
                for a in group.find_all('a'):
                    if a['href'] in cat_list:
                        continue
                    cat_list.append(a['href'])
                    cat_url = self.base_url[:len(self.base_url) - 11] + a['href']
                    start_new_thread(self.parse_category, (cat_url,))

            while not self.thread_started:
                pass
            while self.num_threads > 0:
                pass

        print('Start time:', start_time)
        print('End time:', datetime.datetime.today())


if __name__ == '__main__':
    try:
        Parser.init_shelves()
        Parser.limit_date_for_search = curr_date()
        p = ParserRussianDoska()
        p.start()
        p.join()
    finally:
        Parser.close_shelves()
