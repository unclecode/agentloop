
__author__ = 'Nasrin'

from config import TELEGRAM
from requests import get


class Error:
    def __init__(self, loc, ex, log=True):
        self.loc = loc
        self.ex = ex
        if log:
            self.error()

    def error(self):
        txt = f"Mojito AI:\n{self.loc}\n\n{str(self.ex)}"
        self.send_message(txt)

    def send_message(self, text):
        token = TELEGRAM['TOKEN']
        chat_id = TELEGRAM['BUGS_GROUP']
        params = {
            "chat_id": chat_id,
            "text": text,
        }
        try:
            get(f"https://api.telegram.org/bot{token}/sendMessage", params=params)
        except:
            pass

    @staticmethod
    def send_raw_message(text):
        token = TELEGRAM['TOKEN']
        chat_id = TELEGRAM['BUGS_GROUP']
        params = {
            "chat_id": chat_id,
            "text": text,
        }
        try:
            get(f"https://api.telegram.org/bot{token}/sendMessage", params=params)
        except:
            pass