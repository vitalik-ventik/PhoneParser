import urllib
from bs4 import BeautifulSoup, UnicodeDammit
import re
from ParseCommon import curr_date
from ParseCommon import Parser
from ParseCommon import start_search_msg, finish_search_msg, cancel_search_msg
import socket

import demjson
import datetime


class ParserIsraVid(Parser):
    index = None

    def __init__(self):
        super().__init__('http://isravid.com')

    def run(self):
        self.set_status(start_search_msg)
        self.running = True
        self.load_isra_vid_phones()
        self.running = False
        if self.is_canceled:
            self.set_status(cancel_search_msg)
        else:
            self.set_status(finish_search_msg)

    def get_phone_by_id(self, adv_id):
        params = bytes(urllib.parse.urlencode({'id_advert': adv_id, 'type_data': 'phone'}).encode())
        try:
            url = urllib.request.Request(self.base_url + '/moduls/doska/include/get_type_data_elm_doska.php', params)
        except urllib.request.HTTPError as err:
            self.process_exception(err)
            return ''
        html_src = urllib.request.urlopen(url).read()
        js = str(html_src)
        js = js[2:len(js)-1]
        js = demjson.decode(js)
        try:
            return js['data']['phone']
        except KeyError:
            return ''

    def parse_adv_url(self, adv_url):
        main_page_open = False
        while not main_page_open:
            if self.is_canceled:
                return
            try:
                html_src = urllib.request.urlopen(adv_url).read()
                main_page_open = True
            except (urllib.request.URLError, urllib.request.HTTPError, socket.timeout) as err:
                self.process_exception(err)
                self.inc_error_count()

        curr_name = ''
        dammit = UnicodeDammit(html_src, ["windows-1251"])
        html_src = dammit.unicode_markup
        for name in re.findall(("<tr><td class='td_name_param'>Имя пользователя</td>"
                                "<td>(.+?)</td></tr>"), str(html_src), re.DOTALL):
            curr_name = name
        for adv_id in re.findall(('<span class="elm_container_mask_phone_advert" '
                                  'onclick="view_mask_phone_advert.action_view\((.+?)\)">'), str(html_src), re.DOTALL):
            adv_id = int(adv_id)
            phone = self.get_phone_by_id(int(adv_id))
            for phone_item in Parser.get_phone(phone):
                if Parser.save_phone_name(phone_item, curr_name):
                    self.inc_phone_count()

    def parse_soup_message_item(self, item):
        for row_date in re.findall(('<span class="value_data_advert">'
                                    '([0-9][0-9].[0-9][0-9].[0-9][0-9][0-9][0-9])'), str(item), re.DOTALL):
            row_date = row_date.strip()
            if row_date == '':
                continue
            message_date = datetime.datetime.strptime(row_date, "%d.%m.%Y")
            if message_date < self.limit_date:
                return False

        for adv_url in item.find_all('a', class_="title_synopsis_adv"):
            self.parse_adv_url(self.base_url + adv_url['href'])
        return True

    def parse_soup_reg(self, soup):
        for item in soup.find_all('div', class_="block_info_adv"):
            if not self.parse_soup_message_item(item):
                return False
        return True

    def get_next_page(self, soup):
        for item in re.findall('<a href="(\S+?)"><span>»</span></a>', str(soup), re.DOTALL):
            return self.base_url + item
        return None

    def parse_url(self, url):
        Parser.save_current_url(self.base_url, url, self.limit_date)
        print('Searching phones on', url)
        print('Limit date - ', self.limit_date)
        html_src = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(html_src, 'html.parser')
        if self.parse_soup_reg(soup):
            return self.get_next_page(soup)

    def load_isra_vid_phones(self):
        self.limit_date = Parser.get_current_date(self.base_url)
        start_time = datetime.datetime.today()
        url = self.base_url + '/alladv/'
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
        parser_isra_vid = ParserIsraVid()
        parser_isra_vid.start()
        parser_isra_vid.join()
    finally:
        Parser.close_shelves()
