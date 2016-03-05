import urllib
from bs4 import BeautifulSoup
import re
from ParseCommon import curr_date
from ParseCommon import Parser
from ParseCommon import start_search_msg, finish_search_msg, cancel_search_msg
import socket

from _thread import start_new_thread
import html
import datetime


class ParserZahav(Parser):
    index = None

    def __init__(self):
        super().__init__('http://doska.zahav.ru/')
        self.num_threads = 0
        self.thread_started = False

    def run(self):
        self.num_threads = 0
        self.thread_started = False
        self.set_status(start_search_msg)
        self.running = True
        self.load_zahav_phones()
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
                for item in soup.find_all('div', class_="f_g_t_container"):
                    for re_item in re.findall('Имя:</div><div class="f_g_t_text">(.+?)</div>', str(item), re.DOTALL):
                        if re_item.startswith('<a'):
                            re_item = re.findall('target="_blank">(.+?)</a>', re_item)[0]
                        name = re_item
                    for re_item in re.findall('Телефон:</div><div class="f_g_t_text">(.+?)</div>', str(item), re.DOTALL):
                        for phone_item in re.findall('<span class="f_g_t_text__phone">(.+?)</span>', re_item):
                            for phone in Parser.get_phone(phone_item,):
                                if Parser.save_phone_name(phone, name):
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

        current_url = Parser.get_current_url(self.base_url)
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

            for item in soup.find_all('tr', class_='in'):
                for date_item in re.findall('<td class="date".+?>(..\...\.....)<.+?</td>', str(item), re.DOTALL):
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
                for id_item in re.findall('lDet\((.+?)\);', str(item), re.DOTALL):
                    id_item = [c.strip().replace('\'', '') for c in id_item.split(',')]
                    detail_url = self.base_url + 'ajax.php?action='+id_item[1]+'&branch='+id_item[2]+'&id='+id_item[3]
                    self.parse_detail_url(detail_url)

            self.inc_page_count()
            if old_date_reached:
                url = None
            elif self.is_canceled:
                url = None
            else:
                url = None
                for next_item in soup.find_all('span', class_='next'):
                    for next_a in re.findall('<a href="(.+?)">', str(next_item), re.DOTALL):
                        url = start_url + html.unescape(str(next_a))

        Parser.save_current_url(start_url, '', self.limit_date)
        Parser.lock.acquire()
        self.num_threads -= 1
        print('Search is finished', start_url)
        print('Threads left:', self.num_threads)
        Parser.lock.release()

    def load_zahav_phones(self):
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
            for group in cat_soup.find_all("a", class_="main__category__item__title__link"):
                cat_url = self.base_url[:len(self.base_url) - 1] + group['href']
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
        parser_zahav = ParserZahav()
        parser_zahav.start()
        parser_zahav.join()
    finally:
        Parser.close_shelves()
