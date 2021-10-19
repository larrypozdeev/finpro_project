import random
import re
import time
import urllib.request
from typing import Optional, List
from http.client import RemoteDisconnected
from lxml import html
from config import logging, log_fun


logger = logging.getLogger(__name__)


class ParticipantItem:
    """Used to store a results position with participants."""

    def __init__(self, name: str = "", status: str = "", number: str = "") -> None:
        self.name = name
        self.status = status
        self.number = number

    def get(self) -> object:
        """Returns representation of the class as object."""
        return {"name": self.name, "status": self.status, "number": self.number}

    def __eq__(self, o: object) -> bool:
        if isinstance(o, self.__class__):
            return self.get() == o.get()
        return False

    def __repr__(self) -> str:
        return f"{self.get()}"


def clean_text(text: str) -> str:
    return " ".join(text.split())


class ExistingData:
    """Used to store data (website's html) for further usage."""

    data = []

    def add_data(self, key, value):
        self.data.append({"link": key, "value": value})

    def get_data(self, key, value) -> Optional[html.HtmlElement]:
        for i, dic in enumerate(self.data):
            if dic[key] == value:
                return self.data[i]["value"]
        return None


pages_data = ExistingData()


def get_tree(link) -> Optional[html.HtmlElement]:
    data = pages_data.get_data("link", link)
    if data is not None:
        logger.info("Saved data is used")
        return data
    try:
        req = urllib.request.Request(
            link,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_16_0) "
                + "AppleWebKit/537.36 (KHTML, like Gecko) "
                + "Chrome/83.0.4103.116 Safari/537.36 Edg/83.0.478.61",
                "Referer": link,
            },
        )
        page = urllib.request.urlopen(req)
        page_data = html.fromstring(page.read())
        pages_data.add_data(link, page_data)  # saves the page for further use
        return page_data
    except (urllib.error.URLError, urllib.error.HTTPError) as ex:
        logger.warning(ex, link)
        if hasattr(ex, "code"):
            if ex.code not in [54, 60, 503]:
                logger.warning(ex.code, link)
                return None
        time.sleep(random.uniform(0.1, 1.5))
        return get_tree(link)
    except RemoteDisconnected as ex:
        print(ex, link)
        return None


def notice_zakupki_gov(link) -> str:
    tree = get_tree(link)
    notice_number_el = tree.xpath("//h1[@class='padBtm8']/text()")
    if len(notice_number_el):
        return notice_number_el[0].split("№")[-1]
    else:
        return ""


def notice_zakupki_gov_epz(link) -> str:
    if "regNumber=" in link:
        return link.split("regNumber=")[-1].replace("/", "")

    page = get_tree(link)
    parsed_html = clean_text(page.text_content())
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

    if isinstance(page, html.HtmlElement):
        page = clean_text(page.text_content())

    pattern = re.compile(r"Дата подведения итогов\s{0,4}(\d{2}\.\d{2}\.\d{4})")
    date_match = pattern.search(page)
    date = ""
    if date_match:
        date = date_match.group(1)

    return date


@log_fun
def debriefing_date_zakupki_gov_epz(link):
    page = get_tree(link)
    parsed_html = clean_text(page.text_content())
    pattern = re.compile(
        r"Дата проведения аукциона в электронной форме\s{0,4}(\d{2}\.\d{2}\.\d{4})"
    )
    date_match = pattern.search(parsed_html)
    date = ""
    if date_match:
        date = date_match.group(1)
    return date


def debriefing_date_b2b(link: str = ""):
    return ""


@log_fun
def results_zakupki_gov_epz(link) -> List[ParticipantItem]:
    empty_result = [ParticipantItem()]
    link = link.replace("common-info.html", "supplier-results.html")
    res_page = get_tree(link)
    try:
        main_el = res_page.xpath("/html/body/div[2]/div/div[2]/div/div")[0].xpath(
            "section[@class='blockInfo__section']"
        )[0]
    except:
        print(link)
        return empty_result

    if "не завершено" in main_el.text_content():
        return empty_result

    tables = main_el.xpath("div/table")
    participants_table = ""

    for table in tables:
        name = table.xpath("thead/tr/th/text()")[0]
        if "Участник(и), с которыми планируется заключить контракт" in clean_text(name):
            participants_table = table
            break
    participants = []
    if participants_table != "":
        for row in participants_table.xpath("tbody/tr[@class='tableBlock__row']"):
            participants.append(
                ParticipantItem(
                    name=clean_text(row.xpath("td[1]/text()")[0]),
                    status=clean_text(row.xpath("td[2]/text()")[0]),
                    number=clean_text(row.xpath("td[3]/text()")[0]),
                )
            )
    return participants


@log_fun
def results_zakupki_gov(link: str) -> List[ParticipantItem]:
    """
    Scrapping goverment procurements webpage (223)

    Three steps. Firstly, updates the link, then checks
    if there is a final/partial decision.
    If there is, provides the link

    Args:
        link (str): link for "https://zakupki.gov.ru/223"

    Returns:
        List[ParticipantItem]
    """

    empty_result = [ParticipantItem()]
    if not "/223/" in link:
        return empty_result

    link = link.replace("common-info.html", "protocols.html")
    page = get_tree(link)

    if not isinstance(page, html.HtmlElement):
        return empty_result

    def find_result_links(arr: list) -> List[ParticipantItem]:
        result_list = []
        for elem in arr:
            result_a_onclick_attrib = elem.getparent().attrib["onclick"]
            result_link_part = result_a_onclick_attrib.split("'")[1]
            result_link_part = result_link_part.replace(
                "/view-protocol.html", "/documents.html"
            )
            link = f"https://zakupki.gov.ru{result_link_part}"
            span_text = clean_text(elem.text)
            print(span_text)
            result_list.append(ParticipantItem(status=span_text + ": \n" + link))
        return result_list

    final_result_elements = page.xpath("//span[contains(text(),'Итоговый ')]")
    partial_result_elements = page.xpath(
        "//span[contains(text(),'протокол') or contains(text(),'Протокол ')]"
    )

    if final_result_elements:
        return find_result_links(final_result_elements)
    elif partial_result_elements:
        return find_result_links(partial_result_elements)

    return empty_result


def results_b2b(link) -> List[ParticipantItem]:
    return [ParticipantItem()]
