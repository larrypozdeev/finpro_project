# -*- coding: utf-8 -*-
import concurrent.futures
from get_from_sites import *
import pandas as pd
from requests import Session, get
from time import sleep
import pickle

pd.options.mode.chained_assignment = None
pd.set_option("colwidth", 35)

from config import logging, log_fun, creds_json

logger = logging.getLogger(__name__)


def multi_threading(function, func_arg_list, max_workers):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        result = executor.map(function, func_arg_list)
    return [x for x in result]


def check_urls(url):
    if not url:
        return ""
    if "initpro" in url:
        return ""
    else:
        return url


class FillXlsxFile:
    def __init__(self, xlsx):
        self.xlsx_content = xlsx
        self.new_links = []
        self.notice_numbers = []
        self.all_source_urls = []
        self.session = Session()
        self.headers = {}
        self.checked_urls = []
        self.phpsessid = ""
        self.password = creds_json["password_init_pro"]

    def filterURLs(self, url):
        if not "//zakupki.gov.ru" in url:
            return True
        return False

    @log_fun
    def get_all_source_urls(self):
        self.all_source_urls = list(
            filter(self.filterURLs, self.xlsx_content["Ссылка"].to_list())
        )
        if "initpro" in self.all_source_urls[0]:
            logger.info(f"{len(self.all_source_urls)} source links were found")
        else:
            logger.error(
                f'"get_all_source_urls" func. Source inks do not contain "initpro". f.e \n{self.all_source_urls}'
            )

    @log_fun
    def new_session(self):
        self.phpsessid = self.session.get(
            f"http://initpro.ru/api-new/auth/login?username=finpro.spb@yandex.ru&password={self.password}"
        ).cookies.get_dict()["PHPSESSID"]
        with open("session.pkl", "wb") as f:
            pickle.dump(self.phpsessid, f)

    @log_fun
    def set_initpro_headers(self, bad=0):
        if bad == 1:
            self.new_session()
        else:
            try:
                with open("session.pkl", "rb") as f:
                    self.phpsessid = pickle.load(f)
                    logger.info(
                        f'PHPSESSION was restored from "session.pkl". The value is "{self.phpsessid}"'
                    )
            except IOError:
                self.set_initpro_headers(bad=1)

        self.headers = {
            "Cookie": f"_ym_uid=15935313441902282; _ym_d=1593531344; _ym_visorc_9035083=w; _ym_isad=2; PHPSESSID={self.phpsessid}",
            "Referer": "http://initpro.ru/app-new/?",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36 Edg/83.0.478.56",
            "host": "initpro.ru",
        }
        link = self.get_new_link(self.all_source_urls[0])
        if link == "N/A":
            logger.warning(f'Bad response from "{self.all_source_urls[0]}" - N/A')
            self.set_initpro_headers(bad=1)

        if link == "error" and bad != 1:
            logger.warning(
                f'Bad response from "{self.all_source_urls[0]}" - DoubleLogin'
            )
            return self.set_initpro_headers(bad=1)

        elif link == "error" and bad == 1:
            return "error"

        return ""

    def get_new_link(self, old_url):
        tenderID = old_url.split("/")[-1]
        new_url_response = get(
            f"http://initpro.ru/api-new/tender/getTenderInfo?tenderId={tenderID}",
            headers=self.headers,
        ).json()
        if "error" in new_url_response:
            if new_url_response["error"] == "doublelogin":
                return "error"
        if "href" in new_url_response:
            return new_url_response["href"].replace("http:/", "https:/")
        elif "htenderId" in new_url_response:
            return self.get_new_link(new_url_response["htenderId"])

    @log_fun
    def get_all_new_links(self):
        self.new_links = multi_threading(self.get_new_link, self.all_source_urls, 4)
        logger.info(f'{len(self.new_links)} new links were extracted from "initpro"')

    @log_fun
    def change_links_in_xslx(self):
        links = self.new_links
        for link in range(len(links)):
            link_position = self.xlsx_content[
                self.xlsx_content["Ссылка"] == self.all_source_urls[link]
            ].index.values[0]
            self.xlsx_content["Ссылка"][link_position] = links[link]

    def get_smth_from_link(self, functions, link):
        if len(link) == 0:
            return ""

        if "zakupki.gov.ru/epz" in link:
            return functions["epz"](link=link)
        elif "zakupki.gov.ru" in link:
            return functions["zakupki"](link=link)
        elif "b2b-center.ru" in link:
            return functions["b2b"](link=link)
        else:
            return ""

    def get_notice_number(self, link):
        return self.get_smth_from_link(
            {
                "epz": notice_zakupki_gov_epz,
                "zakupki": notice_zakupki_gov,
                "b2b": notice_b2b,
            },
            link,
        )

    def get_debriefing_date(self, link):
        return self.get_smth_from_link(
            {
                "epz": debriefing_date_zakupki_gov_epz,
                "zakupki": debriefing_date_zakupki_gov,
                "b2b": debriefing_date_b2b,
            },
            link,
        )

    def get_bargaining_result(self, link):
        return self.get_smth_from_link(
            {
                "epz": results_zakupki_gov_epz,
                "zakupki": results_zakupki_gov,
                "b2b": results_b2b,
            },
            link,
        )

    def get_all_from_url(self, function, workers):
        checked_urls = list(map(check_urls, self.xlsx_content["Ссылка"]))
        return multi_threading(function, checked_urls, workers)

    @log_fun
    def get_all_notice_numbers(self):
        self.notice_numbers = self.get_all_from_url(self.get_notice_number, 3)

    @log_fun
    def get_all_debriefing_dates(self):
        self.debriefing_dates = list(
            map(
                self.get_debriefing_date,
                list(map(check_urls, self.xlsx_content["Ссылка"])),
            )
        )

    def new_column(self, position, column_name, filling):
        df = pd.Series(filling)
        self.xlsx_content.insert(position, column_name, df)

    @log_fun
    def add_notice_numbers_to_xlsx(self):
        self.new_column(0, "Вид", [])
        column_name = "Номер извещения"
        self.new_column(0, column_name, self.notice_numbers)

    @log_fun
    def add_debriefing_dates_to_xlsx(self):
        column_name = "Дата подведения итогов"
        self.new_column(8, column_name, self.debriefing_dates)

    @log_fun
    def save_xlsx(self, dir_path):
        self.xlsx_content.to_excel(f"{dir_path}/output.xlsx", engine="xlsxwriter")
        logger.info("Сохранено")
