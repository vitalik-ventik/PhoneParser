import datetime
import threading
import shelve
import os
import _pickle
import time
import socket

start_search_msg = 'Поиск..'
cancel_search_msg = 'Поиск отменен'
finish_search_msg = 'Поиск окончен'
socket.setdefaulttimeout(5)


def curr_date():
    """
    today() return current date with time part, and this function cleans time part
    :return: Current date without time
    """
    return datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)


class Parser(threading.Thread):
    limit_date_for_search = datetime.datetime(year=2016, month=2, day=28)
    lock = threading.Lock()
    cfg = None
    phones = None
    root = None
    source_excel = dict()
    data_dir = os.path.dirname(os.path.abspath(__file__)) +'\data'

    def __init__(self, base_url):
        threading.Thread.__init__(self)
        self.base_url = base_url
        self.running = False
        self.page_count = 0
        self.phone_count = 0
        self.error_count = 0
        self.status = ''
        self.is_canceled = False
        self.limit_date = None

    def inc_page_count(self):
        Parser.lock.acquire()
        self.page_count += 1
        Parser.lock.release()
        self.notify()

    def inc_phone_count(self):
        Parser.lock.acquire()
        self.phone_count += 1
        Parser.lock.release()
        self.notify()

    def inc_error_count(self):
        Parser.lock.acquire()
        self.error_count += 1
        Parser.lock.release()
        self.notify()

    def set_status(self, status):
        self.status = status
        self.notify()

    def cancel(self):
        self.is_canceled = True

    def process_exception(self, err):
        print(self.base_url + ' - ' + 'HTTP Error:', err)
        time.sleep(5)

    def notify(self):
        Parser.lock.acquire()
        if Parser.root is not None:
            Parser.root.event_generate('<<'+self.base_url+'>>')
        Parser.lock.release()

    def run(self):
        pass

    @staticmethod
    def init_shelves():
        if not os.path.exists(Parser.data_dir):
            os.makedirs(Parser.data_dir)
        Parser.cfg = shelve.open(Parser.data_dir+'\sessions.db')
        Parser.phones = shelve.open(Parser.data_dir+'\phones.db')

    @staticmethod
    def delete_files_starting_with(dir, start_str):
        for f in os.listdir(dir):
            if f.startswith(start_str):
                os.remove(os.path.join(dir, f))

    @staticmethod
    def recreate_cfg_shelves():
        Parser.cfg.close()
        Parser.delete_files_starting_with(Parser.data_dir, 'sessions.db')
        Parser.cfg = shelve.open(Parser.data_dir+'\sessions.db')

    @staticmethod
    def recreate_phones_shelves():
        Parser.phones.close()
        Parser.delete_files_starting_with(Parser.data_dir, 'phones.db')
        Parser.phones = shelve.open(Parser.data_dir+'\phones.db')

    @staticmethod
    def close_shelves():
        Parser.cfg.close()
        Parser.phones.close()

    @staticmethod
    def get_phone(phone):
        """
        This function receives a string with phone numbers, splits it, cleares from nondigit and return list of phones
        :param phone: string with phones
        :return: list with founded phones
        """
        result = []
        for item in phone.split(','):
            result.append(''.join([c for c in item.strip() if c.isdigit()])[:10])
        return result

    @staticmethod
    def check_phone(phone):
        """
        Checks if phone is what we are looking for
        :param phone: number of phone
        :return: True or False
        """
        return phone[:3] in ['050', '052', '054', '058', '055']

    @staticmethod
    def save_phone_name(phone, name):
        """
        Saves phone and name in shelve. Name is cleared from not allowed letters. If there is some name for this phone,
        current name is added
        :param phone: Phone
        :param name: Name
        :return: None
        """
        need_resave_phone = False
        Parser.lock.acquire()
        try:
            if not Parser.check_phone(phone):
                return False
            allowed_letters = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                               'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
                               '1234567890 !@#$%^&*()_+=-][}{/?\\\'".,№;:')
            name = ''.join([c for c in name if c.upper() in allowed_letters])
            if phone in Parser.source_excel.keys():
                return False
            if phone in Parser.phones.keys():
                if name == '':
                    return False
                try:
                    names = Parser.phones[phone]
                except (EOFError, _pickle.UnpicklingError, KeyError):
                    names = ''
                    Parser.phones[phone] = names
                if name in (names.split(',')):
                    return False
                if names != '':
                    names += ','
                names += name
                Parser.phones[phone] = names
                result = False
            else:
                Parser.phones[phone] = name
                result = True
            Parser.phones.sync()
        finally:
            Parser.lock.release()
        return result

    @staticmethod
    def save_current_url(current_url, url, current_date):
        """
        Saves current session of searching process
        :param base_url: Name of searching process (in multi-threaded it must be a base url)
        :param url: Current url that programm begins to process
        :return: None
        """
        Parser.lock.acquire()
        try:
            Parser.cfg[current_url] = [url, current_date]
            Parser.cfg.sync()
        finally:
            Parser.lock.release()

    @staticmethod
    def get_current_url(current_url):
        if current_url in Parser.cfg.keys():
            return Parser.cfg[current_url][0]
        else:
            return ''

    @staticmethod
    def get_current_date(current_url):
        current_date = Parser.limit_date_for_search
        if current_url in Parser.cfg.keys():
            try:
                url_value = Parser.cfg[current_url][0]
            except (EOFError, _pickle.UnpicklingError, KeyError):
                url_value = ''
                Parser.cfg[current_url] = ['', current_date]
            if isinstance(url_value, int):
                if url_value != 0:
                    current_date = Parser.cfg[current_url][1]
            else:
                if url_value != '':
                    current_date = Parser.cfg[current_url][1]
        return current_date
