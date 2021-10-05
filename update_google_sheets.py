import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from file_handler import multi_threading
from config import *


class GoogleSheet:
    def __init__(self, file_path=None, sheet_name="Copy of ЦК СТС", worksheet="Лист 1"):
        SCOPE = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive",
        ]
        CREDS = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, SCOPE)

        CLIENT = gspread.authorize(CREDS)

        for spreadsheet in CLIENT.openall():
            print(spreadsheet.title)

        worksheet_index = int(worksheet.get()[-1]) - 1
        self.sheet = CLIENT.open(sheet_name).get_worksheet(worksheet_index)
        self.data = self.sheet.get_all_records(numericise_ignore=["all"])
        self.file_path = file_path
        self.xlsx_content = None

    def find_last_row(self):
        last_row = 0
        for i in range(len(self.data)):
            if self.data[i][settings_data["sheet_fields"]["id"]]:
                last_row = i
        return last_row

    def read_output(self):
        self.xlsx_content = pd.read_excel(
            self.file_path,
            index_col=0,
            converters={"Номер извещения": lambda x: str(x)},
        ).fillna("")
        self.xlsx_content = self.xlsx_content.fillna("")
        try:
            self.xlsx_content["Номер извещения"]
        except Exception as e:
            return "error"

    def append_data(self, d):
        last_row = self.find_last_row()
        new_row = last_row + 1

        if last_row != 0 and self.data[last_row][settings_data["sheet_fields"]["id"]]:
            new_index = (
                int(self.data[last_row][settings_data["sheet_fields"]["id"]]) + 1
            )
        else:
            new_index = 1
        creation_date = datetime.today().strftime("%d.%m.%Y")

        self.data.insert(
            new_row,
            {
                settings_data["sheet_fields"]["id"]: new_index,
                settings_data["sheet_fields"]["creation_date"]: creation_date,
                settings_data["sheet_fields"]["number"]: f'№ {d["Номер извещения"]}',
                settings_data["sheet_fields"]["name"]: d["Название"],
                settings_data["sheet_fields"]["region"]: d["Регион"],
                settings_data["sheet_fields"]["client"]: d["Заказчик"],
                settings_data["sheet_fields"]["client_INN"]: d["ИНН заказчика"],
                settings_data["sheet_fields"]["starting_price"]: d["Нач. цена, руб."],
                settings_data["sheet_fields"]["starting_date"]: d["Начало"],
                settings_data["sheet_fields"]["ending_date"]: d["Окончание"],
                settings_data["sheet_fields"]["holding_date"]: d[
                    "Дата подведения итогов"
                ],
                settings_data["sheet_fields"]["purchase_method"]: d["Способ закупки"],
                settings_data["sheet_fields"]["link"]: d["Ссылка"],
            },
        )

    def update_all_bargaining_result(self, get_fn):
        indent = 250
        df = pd.DataFrame(self.data)
        df.fillna("", inplace=True)
        df_copy = df.copy()
        today = datetime.today().strftime("%d.%m.%Y")
        links_indices = []
        links = []
        for i in range(len(df[settings_data["sheet_fields"]["link"]])):
            if df[settings_data["sheet_fields"]["participaters"]][i]:
                continue
            if df[settings_data["sheet_fields"]["winner"]][i]:
                continue
            if str(df[settings_data["sheet_fields"]["price"]][i]):
                continue
            if not df[settings_data["sheet_fields"]["id"]][i]:
                continue
            links_indices.append(i)
            links.append(df[settings_data["sheet_fields"]["link"]][i])
        print(links_indices[-indent:])
        updated_dict = multi_threading(get_fn, links[-indent:], 4)
        updated_dict = [
            x if x != "" else [{"name": "", "status": "", "number": ""}]
            for x in updated_dict
        ]

        for (i, el_list) in enumerate(updated_dict):
            if len(el_list) == 1:
                if len(el_list[0]["status"]):
                    sheet_index = links_indices[-indent:][i]
                    print(el_list[0]["status"], sheet_index)
                    df[settings_data["sheet_fields"]["participaters"]][
                        sheet_index
                    ] = el_list[0]["status"]
                continue

            sheet_index = links_indices[-indent:][i]
            if len(el_list) == 2 and len(el_list[0]["status"]) > 25:
                df[settings_data["sheet_fields"]["winner"]][sheet_index] = el_list[0][
                    "status"
                ]
                df[settings_data["sheet_fields"]["participaters"]][
                    sheet_index
                ] = el_list[1]["name"]
                continue

            participants = []
            for j in el_list:
                participants.append(j["name"])
                if "победитель" in j["status"].lower():
                    df[settings_data["sheet_fields"]["winner"]][sheet_index] = j["name"]
                    df[settings_data["sheet_fields"]["price"]][sheet_index] = j[
                        "number"
                    ]
                    continue
            df[settings_data["sheet_fields"]["participaters"]][
                sheet_index
            ] = ";\n".join(participants)

        self.sheet.update([df.columns.values.tolist()] + df.values.tolist())

    def append_list(self):
        for index, row in self.xlsx_content.iterrows():
            self.append_data(row.to_dict())
        self.save()

    def save(self):
        df = pd.DataFrame(self.data)
        df.fillna("", inplace=True)
        self.sheet.update([df.columns.values.tolist()] + df.values.tolist())

    def __repr__(self):
        return str(self.data[0:2])


if __name__ == "__main__":
    print(repr(GoogleSheet(sheet_name="ЦК СТС -проеткные ,СМР")))
