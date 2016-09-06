import argparse
import urllib.request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
import time
import concurrent.futures
import redis
import json
import os.path
import resource
from sys import platform


db = redis.StrictRedis()

EXTENSIONS = ('.wav', '.mp3', '.bmp', '.gif', '.jpg', '.png', '.mp4')


class Profiler:
    def __enter__(self):
        self._startTime = time.time()

    def __exit__(self, type, value, traceback):
        s = '>> ok, execution time: {}s, peak memory usage: {}Mb'
        ex_time = int(time.time() - self._startTime)

        if platform.startswith('linux'):
            memory_usage = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
        elif platform.startswith('darwin'):
            memory_usage = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024)
        else:
            memory_usage = '???'
            #windows ;(
        print(s.format(ex_time, memory_usage))


def save(db, url, data):
    db.set(url, data)


def load(db, url):
    return db.get(url)


def getTitle(data):
    title_tag = SoupStrainer('title')
    parser_title = BeautifulSoup(data, 'lxml', parse_only=title_tag)
    return parser_title.title.text if parser_title.title else 'None'


def getURLS(data):
    a_tags = SoupStrainer('a')
    parser_a = BeautifulSoup(data, 'lxml', parse_only=a_tags)
    urls = []
    for x in parser_a.find_all('a'):
        url = x.get('href')
        if url and is_valid_url(url) and url not in urls:
            urls.append(url)

    return urls


def getHTML(data):
    html_tag = SoupStrainer('html')
    parser_html = BeautifulSoup(data, 'lxml', parse_only=html_tag)
    return parser_html.html.text if parser_html.html else 'None'


def load_url(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as conn:
        return conn.read().decode('utf-8')


def run(root, links, num_workers=32, depth=0):
    result = []
    s = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_url = {
            executor.submit(load_url, url, 60): url for url in links}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()

                if not data:
                    continue

                title = getTitle(data)
                html = getHTML(data)

                # print('{}: "{}"'.format(url, title))

                s.append({'url': url, 'title': title, 'html': html})

                if depth == 2:
                    t = getURLS(data)
                    for x in t:
                        result.append(x)
            except Exception as exc:
                # print('%r generated an exception: %s' % (url, exc))
                pass

    _json = json.dumps(s, ensure_ascii=False).encode('utf-8')
    save(db, root, _json)

    return result


def print_load(args):
    url = args.URL
    DEPTH = args.depth
    num_workers = args.workers

    if not num_workers:
        num_workers = 32

    with Profiler() as p:
        if DEPTH == 0:
            data = load_url(url)
            title, html = getTitle(data), getHTML(data)

            s = [{'url': url, 'title': title, 'html': html}]
            _json = json.dumps(s, ensure_ascii=False).encode('utf-8')
            save(db, url, _json)
            return
        elif DEPTH == 1 or DEPTH == 2:
            data = load_url(url)
            urls, title, html = getURLS(data), getTitle(data), getHTML(data)
        # print('{}: "{}"'.format(url, title))

        result = run(url, urls, num_workers, DEPTH)
        if result:
            run(url, result, num_workers)


def print_get(args):
    url = args.URL
    n = args.n

    if not n:
        raise Exception("n must be positive")
        return

    try:
        data = json.loads(load(db, url).decode('utf-8'))[0:n]
    except AttributeError:
        print('Wrong URL')
        return
    for i, dct in enumerate(data, start=1):
        print('>> {}. {}: "{}"'.format(i, dct['url'], dct['title']))


def is_valid_url(url):
    if os.path.splitext(os.path.basename(urlparse(url).path))[1] in EXTENSIONS: return False

    parseresult = urllib.parse.urlparse(url)
    attributes = ('scheme', 'netloc')
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
        '--workers', action='store', type=int, help='Nums of workers')
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
