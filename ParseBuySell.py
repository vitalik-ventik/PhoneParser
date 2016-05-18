import urllib
from bs4 import BeautifulSoup
import re
from ParseCommon import curr_date
from ParseCommon import Parser
from ParseCommon import start_search_msg, finish_search_msg, cancel_search_msg
import socket

from _thread import start_new_thread
import datetime


class ParserBuySell(Parser):
    index = None

    def __init__(self):
        super().__init__('http://doska.buy-sell.co.il/')
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

    def parse_detail_url(self, url):
        detail_url_open = False
        while not detail_url_open:
            if self.is_canceled:
                return True
            try:
                html_src = urllib.request.urlopen(url).read()
                detail_url_open = True
                soup = BeautifulSoup(html_src, 'html.parser')
                name = ''

                for item in re.findall('<div class="address_ads"><img.+?>(.+?)</div>', str(soup), re.DOTALL):
                    name = item.split(',')[0]

                for div in soup.find_all('div', {'class': 'phone_ads'}):
                    for item in re.findall('([0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9])', str(div).replace('-', '').replace(' ', ''), re.DOTALL):
                        for phone in Parser.get_phone(item):
                            if Parser.save_phone_name(phone, name):
                                self.inc_phone_count()
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
            print(url)
            if self.is_canceled:
                break
            Parser.save_current_url(start_url, url, self.limit_date)
            try:
                html_src = urllib.request.urlopen(url).read()
            except (urllib.request.URLError, urllib.request.HTTPError, socket.timeout) as err:
                self.process_exception(err)
                self.inc_error_count()
                continue
            old_date_reached = False

            soup = BeautifulSoup(html_src, 'html.parser')
            for box in soup.find_all('div', {'class': lambda l: l and l in ('box_all_content', 'box_vip_content')}):
                for date_box in box.find_all('div', {'class': 'f_right'}):
                    if 'VIP' in str(date_box):
                        break
                    for date_item in re.findall('[0-9][0-9]\.[0-9][0-9]\.[0-9][0-9][0-9][0-9]', str(date_box), re.DOTALL):
                        date_item = date_item.strip()
                        if date_item == '':
                            continue
                        try:
                            message_date = datetime.datetime.strptime(date_item, "%d.%m.%Y")
                            if message_date < self.limit_date:
                                old_date_reached = True
                                break
                        except ValueError:
                            print('Error while encoding date', date_item)
                            continue
                if old_date_reached:
                    break
                for div in box.find_all('div', {'class': 'title f_left'}):
                    for a in div.find_all('a'):
                        self.parse_detail_url(self.base_url[:-1] + a['href'])

            self.inc_page_count()
            if old_date_reached:
                url = None
            elif self.is_canceled:
                url = None
            else:
                url = None
                for td in soup.find_all('td', {'id': 'list2'}):
                    for next_a in re.findall('<span class="sel">.+?<a.+?href="(.+?)"', str(td), re.DOTALL):
                        url = self.base_url[:-1] + next_a

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
            for cat_url in cat_soup.find_all("a", {'class': lambda l: l and l.startswith('namecat_')}):
                start_new_thread(self.parse_category, (self.base_url[:-1] + cat_url["href"],))

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
        p = ParserBuySell()
        p.start()
        p.join()
    finally:
        Parser.close_shelves()
