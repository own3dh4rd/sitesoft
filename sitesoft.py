import argparse
import urllib.request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import threading
import queue
import time


DEPTH = 0


class Profiler:
    def __enter__(self):
        self._startTime = time.time()

    def __exit__(self, type, value, traceback):
        s = 'ok, execution time: {:.3f}sec, peak memory usage: 228Mb'
        print(s.format(time.time() - self._startTime))


class Worker(threading.Thread):
    def __init__(self, tasks):
        threading.Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while True:
            if self.tasks.empty():
                break
            parser = self.tasks.get()
            try:
                parser.parsePage()
                if parser.depth:
                    for l in parser.links:
                        self.tasks.put(Parser(l, depth=parser.depth - 1))

            except Exception as e:
                print(e)
            finally:
                self.tasks.task_done()


class Pool:
    def __init__(self, num_threads):
        self.tasks = queue.Queue()
        self.num_threads = num_threads

    def add_task(self, task):
        self.tasks.put(task)

    def wait_completion(self):
        self.tasks.join()

    def run(self):
        for _ in range(self.num_threads):
            Worker(self.tasks)


class Parser:
    def __init__(self, url, depth=0):
        self._url = url
        self.links = []
        self.depth = depth

    def getData(self, url):
        try:
            with urllib.request.urlopen(url) as f:
                data = f.read().decode('utf-8')
        except Exception as e:
            # print('Error - {} on the URL: {}'.format(e, url))
            return None

        return data

    def getTitle(self, parser):
        return parser.title.string if parser.title else 'None'

    def parsePage(self):
        data = self.getData(self._url)

        if data is None:
            return

        parser = BeautifulSoup(data, 'html.parser')
        for x in parser.find_all('a'):
            link = x.get('href')
            if link and is_valid_url(link) and link not in self.links:
                self.links.append(link)
        # self.links = [
        #     x.get('href')
        #     for x in parser.find_all('a')
        #     if x.get('href') and is_valid_url(x.get('href')) and x.get('href') not in self.links]
        print('{}: "{}"'.format(self._url, parser.title.string))
        return (data, self._url, self.links, self.getTitle(parser))


def print_load(args):
    url = args.URL
    global DEPTH
    DEPTH = args.depth
    nums_threads = args.threads

    if not nums_threads:
        nums_threads = 16

    pool = Pool(nums_threads)

    with Profiler() as p:
        pool.add_task(Parser(url, depth=DEPTH))
        pool.run()
        pool.wait_completion()


def print_get(args):
    pass


def is_valid_url(url):
    attributes = ('scheme', 'netloc')
    parseresult = urllib.parse.urlparse(url)
    return all(getattr(parseresult, attr) for attr in attributes)


def main():
    parser = argparse.ArgumentParser(
        description='Load and store html, url, title of website')
    subparsers = parser.add_subparsers(help='List of commands')

    #load
    load_parser = subparsers.add_parser('load', help='Load website')
    load_parser.add_argument('URL', action='store', help='URL of the website')
    load_parser.add_argument(
        '--depth', action='store', type=int, help='Level of depth, depth=0..2')
    load_parser.add_argument(
        '--threads', action='store', type=int, help='Nums of threads')
    load_parser.set_defaults(func=print_load)

    #get
    get_parser = subparsers.add_parser('get', help='Get data by URL')
    get_parser.add_argument('URL', action='store', help='URL of the website')
    get_parser.add_argument('-n', action='store', type=int, help='Depth')
    get_parser.set_defaults(func=print_get)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
