import random
import re
import time
import urllib.request
from config import logging, log_fun
from lxml import html


class ExistingData:
    """Used to store data (website's html) for further usage."""

    data = []

    def add_data(self, key, value):
        self.data.append({"link": key, "value": value})

    def get_data(self, key, value):
        for i, dic in enumerate(self.data):
            if dic[key] == value:
                return self.data[i]["value"]
        return None


pages_data = ExistingData()


def get_tree(link):
    data = pages_data.get_data("link", link)
    if data is not None:
        print("Saved data is used")
        return data
    try:
        req = urllib.request.Request(
            link,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_16_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36 Edg/83.0.478.61",
                "Referer": link,
            },
        )
        page = urllib.request.urlopen(req)
        page_data = html.fromstring(page.read())
        pages_data.add_data(link, page_data)  # saves the page for further use
        return page_data
    except Exception as e:
        print(e)
        if e.code != 503:
            print(e.code, link)
            return ""
        time.sleep(random.uniform(0.1, 5))
        return get_tree(link)


def notice_zakupki_gov(link):
    tree = get_tree(link)
    notice_number_el = tree.xpath("//h1[@class='padBtm8']/text()")
    if len(notice_number_el):
        return notice_number_el[0].split("№")[-1]
    else:
        return ""


def notice_zakupki_gov_epz(link):
    if "regNumber=" in link:
        return link.split("regNumber=")[-1].replace("/", "")

    page = get_tree(link)
    parsed_html = " ".join(page.text_content().split())
    pattern = re.compile(r"№\s{0,4}(\d{5,25})")
    number_match = pattern.search(parsed_html)
    number = ""
    if number_match:
        number = number_match.group(1)
    return number


def notice_b2b(link):
    return link.split("/tender-")[-1].split("/")[0]


@log_fun
def debriefing_date_zakupki_gov(link):
    page = get_tree(link)

    if type(page) != str:
        page = page.text_content().split()

    parsed_html = " ".join(page)
    pattern = re.compile(r"Дата подведения итогов\s{0,4}(\d{2}\.\d{2}\.\d{4})")
    date_match = pattern.search(parsed_html)
    date = ""
    if date_match:
        date = date_match.group(1)

    print(date)
    return date


@log_fun
def debriefing_date_zakupki_gov_epz(link):
    page = get_tree(link)
    parsed_html = " ".join(page.text_content().split())
    pattern = re.compile(
        r"Дата проведения аукциона в электронной форме\s{0,4}(\d{2}\.\d{2}\.\d{4})"
    )
    date_match = pattern.search(parsed_html)
    date = ""
    if date_match:
        date = date_match.group(1)
    return date


def debriefing_date_b2b(link):
    return ""


@log_fun
def results_zakupki_gov_epz(link):
    link = link.replace("common-info.html", "supplier-results.html")
    res_page = get_tree(link)
    try:
        main_el = res_page.xpath("/html/body/div[2]/div/div[2]/div/div")[0].xpath(
            "section[@class='blockInfo__section']"
        )[0]
    except:
        print(link)
        return [{"name": "", "status": "", "number": ""}]

    if "не завершено" in main_el.text_content():
        return [{"name": "", "status": "", "number": ""}]

    tables = main_el.xpath("div/table")
    participants_table = ""

    for table in tables:
        name = table.xpath("thead/tr/th/text()")[0]
        if "Участник(и), с которыми планируется заключить контракт" in " ".join(
            name.split()
        ):
            participants_table = table
            break
    print(tables)
    participants = []
    if participants_table != "":
        for row in participants_table.xpath("tbody/tr[@class='tableBlock__row']"):
            participants.append(
                {
                    "name": " ".join(row.xpath("td[1]/text()")[0].split()),
                    "status": " ".join(row.xpath("td[2]/text()")[0].split()),
                    "number": " ".join(row.xpath("td[3]/text()")[0].split()),
                }
            )
    return participants


def results_zakupki_gov(link):
    return [{"name": "", "status": "", "number": ""}]


def results_b2b(link):
    return [{"name": "", "status": "", "number": ""}]
