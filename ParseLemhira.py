import urllib
from bs4 import BeautifulSoup
import re
from ParseCommon import curr_date
from ParseCommon import Parser
from ParseCommon import start_search_msg, finish_search_msg, cancel_search_msg
import socket

from _thread import start_new_thread
import datetime


class ParserLemhira(Parser):
    index = None

    def __init__(self):
        super().__init__('http://www.lemhira.com/')
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

    def parse_detail_url(self, url, need_to_check_date):
        detail_url_open = False
        while not detail_url_open:
            if self.is_canceled:
                return True
            try:
                html_src = urllib.request.urlopen(url).read()
                detail_url_open = True
                soup = BeautifulSoup(html_src, 'html.parser')
                name = ''

                if need_to_check_date:
                    for date_item in soup.find_all('span', class_="item-change-date"):
                        date_item = date_item.text.strip()
                        if date_item == '':
                            continue
                        try:
                            message_date = datetime.datetime.strptime(date_item, "%d.%m.%Y")
                            need_to_check_date = False
                            if message_date < self.limit_date:
                                return False
                        except ValueError:
                            print('Error while encoding date', date_item)
                            continue

                    if need_to_check_date:
                        for date_item in soup.find_all('span', class_="item-create-date"):
                            date_item = date_item.text.strip()
                            if date_item == '':
                                continue
                            try:
                                message_date = datetime.datetime.strptime(date_item, "%d.%m.%Y")
                                need_to_check_date = False
                                if message_date < self.limit_date:
                                    return False
                            except ValueError:
                                print('Error while encoding date', date_item)
                                continue

                for item in soup.find_all('td', class_="item-name-1"):
                    name = item.text.strip()

                for item in re.findall('tel:([0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9])', str(html_src), re.DOTALL):
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

        current_page = Parser.get_current_url(start_url)
        if current_page == '':
            current_page = '1'
        else:
            current_page = current_page[-current_page[::-1].find('='):]
            print('Restoring previous session..')

        while not (current_page == ''):
            if self.is_canceled:
                break
            url = start_url + "?js&page=" + current_page
            Parser.save_current_url(start_url, url, self.limit_date)
            try:
                html_src = urllib.request.urlopen(url).read()
            except (urllib.request.URLError, urllib.request.HTTPError, socket.timeout) as err:
                self.process_exception(err)
                self.inc_error_count()
                continue
            old_date_reached = False

            if len(html_src) == 26:
                current_page = ''
                continue

            html_src = str(html_src).replace('\\', '')
            for data_box in re.findall("<div data-box='.+?<a class='fullanch blessbmark' itemprop='url' href='.+?'>", html_src, re.DOTALL):
                need_to_check_date = True
                for date_item in re.findall("<span class='date'>(/+?)</span>", data_box, re.DOTALL):
                    date_item = date_item.strip()
                    if date_item == '':
                        continue
                    try:
                        message_date = datetime.datetime.strptime(date_item, "%d.%m.%Y")
                        need_to_check_date = False
                        if message_date < self.limit_date:
                            old_date_reached = True
                            break
                    except ValueError:
                        print('Error while encoding date', date_item)
                        continue
                if old_date_reached:
                    break
                for details in re.findall("<a class='fullanch blessbmark' itemprop='url' href='(.+?)'>", data_box, re.DOTALL):
                    if not self.parse_detail_url(self.base_url[:-1] + details, need_to_check_date):
                        old_date_reached = True
                        break

            self.inc_page_count()
            if old_date_reached:
                current_page = ''
            elif self.is_canceled:
                current_page = ''
            else:
                current_page = str(int(current_page) + 1)

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
            for group in cat_soup.find_all("div", class_="subca"):
                for cat_url in group.find_all("a"):
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
        p = ParserLemhira()
        p.start()
        p.join()
    finally:
        Parser.close_shelves()
