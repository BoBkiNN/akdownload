import random
from asyncio import Future
from concurrent.futures import ThreadPoolExecutor
from threading import current_thread

import requests

PROXYSCRAPER_URL = "https://api.proxyscrape.com/?request=getproxies&proxytype=http&timeout=10000&country=all&ssl=all&anonymity=anonymous"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


class Requester:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.proxies: list[str] = []
        self.executor = ThreadPoolExecutor(10, "Request")
        self.closed = False
        self.futures: list[Future] = []
    
    def fetch_proxies(self):
        r = self.session.get(PROXYSCRAPER_URL)
        self.proxies = r.text.splitlines()
        return len(self.proxies)
    
    def log(self, *args):
        print(current_thread().name+":", *args)
    
    def _get(self, url: str, cb, args: tuple):
        try:
            r = self.session.get(url, proxies={"http": random.choice(self.proxies)})
        except Exception as e:
            self.log(f"Cannot get: {e}")
            return
        try:
            cb(r, *args)
        except Exception as e:
            self.log(f"Cannot handle callback: {e}")
    
    def close(self):
        self.executor.shutdown(True, cancel_futures=True)
        self.session.close()
        self.futures.clear()
        self.closed = True
    
    def update_futures(self):
        ls = self.futures.copy()
        for f in ls:
            if f.done():
                self.futures.remove(f)
    
    def is_done(self, update=True):
        if update: self.update_futures()
        return len(self.futures) == 0

    def get(self, url: str, cb, args=()):
        f = self.executor.submit(self._get, url, cb, args)
        self.futures.append(f)

if __name__ == "__main__":
    r = Requester()
    r.fetch_proxies()
    r.get("sdfsdf", None)
    r.close()