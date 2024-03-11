import os
import re
import signal
import time
import traceback
from argparse import ArgumentParser

import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas
from tqdm import tqdm

from pagefill import fill_page_with_image
from requester import Requester


def natural_sort_key(s):
    # Extract numeric part from the file name
    return [int(text) if text.isdigit() else text.lower() for text in re.split('(\d+)', s)]


class Main:
    def __init__(self, out_file: str, from_page: int, to_page: int, cleanup: bool, url: str) -> None:
        self.output_file = out_file
        self.from_page = from_page
        self.to_page = to_page
        self.cleanup = cleanup
        self.url = url
        self.r = Requester()
        signal.signal(signal.SIGINT, self.stop)
        self.bar = None
        self.tmp = os.path.join(os.getcwd(), "imgs")

    def save(self, req: requests.Response, num: int):
        if req.status_code == 400:
            self.bar.write("Request returned 404, aborting")
            self.r.close()
            return
        if req.status_code != 200:
            self.bar.write("Request returned incorrect status code")
            return
        if not os.path.exists(self.tmp):
            os.mkdir(self.tmp)
        imf = os.path.join(self.tmp, f"img{num}.jpg")
        if not os.path.isfile(imf):
            with open(imf, "wb") as f:
                f.write(req.content)
            self.bar.desc = f"#{num} saved"
            self.bar.refresh()
        self.bar.update()

    def create_pdf(self):
        # Get a list of all files in the directory
        files = [file for file in os.listdir(
            self.tmp) if file.lower().endswith('.jpg')]
        files.sort(key=natural_sort_key)  # Sort the files

        doc = Canvas(self.output_file, pagesize=letter)
        t = tqdm(total=len(files)+1, desc="Adding images", ncols=100)
        for file in files:
            image_path = os.path.join(self.tmp, file)
            fill_page_with_image(image_path, doc)
            doc.showPage()
            # t.write(f"Added {file}")
            t.update()
            t.refresh()
        t.desc = "Saving PDF"
        t.refresh()
        try:
            doc.save()
            t.update()
            t.close()
        except Exception as e:
            t.close()
            print(f"Cannot build PDF: {e}")
            traceback.print_tb(e.__traceback__)

    def clean_up(self):
        try:
            [os.remove(os.path.join(self.tmp, file)) for file in os.listdir(
                self.tmp) if file.lower().endswith('.jpg')]
        except Exception as e:
            print("Cannot cleanup:", e)
            traceback.print_tb(e.__traceback__)

    def main(self):
        print("Fetching proxies")
        pn = self.r.fetch_proxies()
        print(f"Fetched {pn} proxies")
        size = self.to_page-self.from_page+1
        self.bar = tqdm(total=size, desc="Getting images", ncols=100)
        self.bar.refresh()
        for n in range(self.from_page, self.to_page+1):
            self.r.get(f"{self.url}{n}.jpg", self.save, (n,))

        while not self.r.closed:
            if self.r.is_done(True):
                self.r.close()
                break
            time.sleep(0.1)
        self.bar.close()
        print("Creating PDF")
        self.create_pdf()

        if self.cleanup:
            print("Clearing images..")
            self.clean_up()
        print("Finished")

    def stop(self, *args):
        self.r.close()


def main():
    parser = ArgumentParser()
    parser.add_argument("-n", "--no-cleanup", action="store_false",
                        help="Disable cleanup", default=True, required=False, dest="cleanup")
    parser.add_argument("-f", "--file", required=True, help="Output file")
    parser.add_argument("start", type=int, help="Start page")
    parser.add_argument("end", type=int, help="End page")
    parser.add_argument("url", type=str, help="Images url, including /")
    args = parser.parse_args()
    file = os.path.normpath(args.file)
    Main(file, args.start, args.end, args.cleanup, args.url).main()


if __name__ == "__main__":
    main()
