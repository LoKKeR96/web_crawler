import gevent
import requests
from requests_futures.sessions import FuturesSession
from lxml.html import fromstring
from urllib.parse import urlparse
import random

# Initialise random generator
random.seed()

# List of possible resource suffixes
resources_suffix = [".js", ".css", ".jpg", ".gif", ".png", ".mp4", ".ico", ".svg", ".json", ".xml"]

# Header used to pull pages. This ensures we always obtain a valid response.
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE'
}

# Maximum amount of tentatives to sync a page
max_attempts = 3

# URL Paths to avoid if they did not sync successfully after the maximum amount of attempts
avoid_paths = []

session = FuturesSession(max_workers=4)


class Page:
    def __init__(self, url, domain_url, domain_name):
        self.url = url  # URL of the page
        self.domain_url = domain_url  # Website domain url
        self.domain_name = domain_name  # Website domain name
        self.dom = None  # Page DOM from lxml
        self.is_root_page = False  # Is page the main page of the website
        self.sub_pages = []  # List of sub pages of type Page
        self.domain_links = []  # List of sub pages by link  -- can be deleted
        self.domain_links_by_path = {}  # List of sub pages of type Page


def is_link_to_resource(link):
    """
    Checks whether the link contains a file or resource suffix which means it is most likely
    a link to obtain that resource
    :param link: string, the URL link to check
    :return: True if the link contains a reference to a resource otherwise False
    """
    for suffix in resources_suffix:
        if suffix in link:
            return True


def get_page_dom(page, cur_attempt=0):
    """
    Pulls the dom of a page such that it's easier to navigate through the HTML tags.
    :param page: object of type Page
    :return: no return value
    """
    page.dom = None

    # Skip sub pages that point to root page
    if page.is_root_page == False and page.url == page.domain_url:
        print("Skipping: " + page.url)
        return

    parsed_url = urlparse(page.url)
    if cur_attempt < max_attempts:
        if parsed_url.path not in avoid_paths:
            print("Processing: " + page.url)
            try:
                gevent.sleep(random.uniform(0.25, 2))
                future = session.get(page.url)
                response = future.result()
                if response.ok:
                    page.dom = fromstring(response.content)
                    return
                else:
                    print("Did not succeed requesting page, err=" + str(response.status_code))
            except requests.exceptions.TooManyRedirects as e:
                # Should probably not try again
                print("Too many redirects...")
            except requests.exceptions.ConnectionError as e:
                print("Could not connect...")
            except requests.exceptions.Timeout as e:
                print("Timeout. Try again.")
            get_page_dom(page, cur_attempt + 1)
        else:
            print("Skipping: " + page.url)
    else:
        print(parsed_url.path)
        avoid_paths.append(parsed_url.path)


def parse_links(page):
    """
    Parse all links in the page dom and group them by URL path
    :param page: object of type Page, dom attribute must be no None
    :return: no return value
    """
    # Reformat all internal links with domain url
    page.dom.make_links_absolute(domain_url, resolve_base_href=True)

    domain_links = []

    for element, attribute, link, pos in page.dom.iterlinks():
        # Format all links with the same http syntax
        strip_link = link.replace("https://", "http://").replace("www.", "")

        # Exclude attributes types: None, src, action, style and so on
        # as they are most likely not relevant links
        if attribute == "href":
            if not is_link_to_resource(strip_link):
                # If it's a link to a page
                if "http" in strip_link:
                    # If domain is in link but not as a redirect
                    if page.domain_name in strip_link and strip_link.count("http") == 1:
                        domain_links.append(strip_link)
                    # Anything else is a link to other domains

    domain_links = list(dict.fromkeys(domain_links))

    # Remove domain self-reference
    if page.is_root_page:
        try:
            domain_links.remove(page.domain_url)
        except Exception as e:
            # Ignore
            pass

    path_groups = []
    domain_links_by_path = {}

    # Map paths from every link and group links by path
    for item in domain_links:
        parsed_url = urlparse(item)
        path = parsed_url.path
        if path not in path_groups:
            path_groups.append(path)
            if path not in domain_links_by_path:
                domain_links_by_path[path] = []
            domain_links_by_path[path].append(item)

    page.domain_links = domain_links
    page.domain_links_by_path = domain_links_by_path

    for path in page.domain_links_by_path.keys():
        for link in page.domain_links_by_path[path]:
            sub_page = Page(link, domain_url, domain_name)
            sub_page.is_sub = True
            page.sub_pages.append(sub_page)


def sync_page(page):
    """
    Syncs the dom of a page and parses the internal domain links.
    :param page: object of type Page
    :return: no return value
    """
    get_page_dom(page)
    if page.dom is not None:
        parse_links(page)


def sync_subpages(root_page, depth, cur_depth=0):
    """
    Syncs the subpages of the root page asynchronously
    :param root_page: object of type Page
    :param depth: integer, how many levels of sub pages to sync
    :param cur_depth: integer, current depth of the recursion
    :return:
    """
    if cur_depth < depth:
        threads = []
        for sub_page in root_page.sub_pages:
            threads.append(gevent.spawn(sync_page, sub_page))
            gevent.joinall(threads)
            sync_subpages(sub_page, depth, cur_depth + 1)


def print_pages_graph(root_page, depth, cur_depth=0):
    """
    Prints the graph showing which page links to which sub page.
    Use the depth parameter to control how many levels of sub pages
    to print in the graph.
    :param root_page: object of type Page
    :param depth: integer, depth of the graph
    :param cur_depth: integer, current depth of the recursion
    :return:
    """
    if cur_depth < depth:
        for subPage in root_page.sub_pages:
            print(root_page.url + " => " + subPage.url)
            if subPage.dom is not None:
                print_pages_graph(subPage, depth, cur_depth + 1)


if __name__ == '__main__':
    # URL in the format http://domain.com
    domain_url = "http://news.ycombinator.com"

    parsed_main_url = urlparse(domain_url)
    split_parsed_url = parsed_main_url.netloc.split(".")
    domain_name = split_parsed_url[len(split_parsed_url) - 2]
    print("DOMAIN: " + domain_name + "\n")

    print("Syncing main page...")
    main_page = Page(domain_url, domain_url, domain_name)
    main_page.is_root_page = True
    sync_page(main_page)

    print("Syncing sub pages...")
    sync_subpages(main_page, 2)

    print("\n\nPages graph:")
    print_pages_graph(main_page, 2)
