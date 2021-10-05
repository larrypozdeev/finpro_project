# -*- coding: utf-8 -*-
import os
import time

from config import logging, settings_data, log_fun
from tkinter import *
from tkinter import _setit
from tkinter.filedialog import askopenfilename

from pandas import read_excel

from file_handler import FillXlsxFile
from update_google_sheets import GoogleSheet

logger = logging.getLogger("main")


class GraphicalInterface:
    def __init__(self):
        self.filename = ""
        self.output_filename = ""
        root = Tk()
        root.title(f"{settings_data['title']} v{settings_data['version']}")

        self.chosen_sheet = StringVar(root)
        self.chosen_sheet.set(list(settings_data["sheets"].keys())[0])
        self.chosen_page = StringVar(root)
        self.chosen_page.set(list(settings_data["sheets"].values())[0][0])
        self.sheet_option = OptionMenu(
            root, self.chosen_sheet, *[x for x in list(settings_data["sheets"].keys())]
        )
        self.page_option = OptionMenu(
            root,
            self.chosen_page,
            *[x for x in list(settings_data["sheets"].values())[0]],
        )

        self.file_label = Label(root, text="Выберите .xlsx файл", height="5")
        self.choose_file_button = Button(root, text="Выбрать", command=self.find_xlsx)
        self.start_button = Button(
            root, text="Заполнить таблицы", command=self.read_and_fill_xlsx
        )

        self.output_file_label = Label(
            root, text="Выберите итоговый файл сохранения", height="5"
        )
        self.choose_output_file_button = Button(
            root, text="Выбрать", command=self.find_output_xlsx
        )
        self.save_in_google_button = Button(
            root,
            text="Сохранить в Google",
            command=self.save_in_google_sheets,
        )

        self.update_results_in_google_button = Button(
            root,
            text="Обновить результаты",
            command=self.update_bargaining_results,
        )
        self.sheet_option.grid(
            row=0,
            column=0,
            columnspan=2,
            pady=(10, 5),
            padx=(30, 10),
        )
        self.page_option.grid(
            row=1,
            column=0,
            columnspan=2,
            pady=(10, 5),
            padx=(30, 10),
        )
        self.file_label.grid(
            row=2,
            column=0,
            pady=(10, 5),
            padx=(30, 10),
        )
        self.choose_file_button.grid(
            row=2,
            column=1,
            pady=(10, 5),
            padx=(10, 30),
        )
        self.output_file_label.grid(row=3, column=0, pady=(5, 5), padx=(30, 10))
        self.choose_output_file_button.grid(row=3, column=1, pady=(5, 5), padx=(10, 30))
        self.update_results_in_google_button.grid(
            row=4, column=0, pady=(5, 10), padx=(30, 10)
        )

        def menu_dropdown(*args):
            for i, j in settings_data["sheets"].items():
                if i == self.chosen_sheet.get():
                    list_of_options = j
            self.chosen_page.set("")  # remove default selection only, not the full list
            self.page_option["menu"].delete(0, "end")  # remove full list
            for opt in list_of_options:
                self.page_option["menu"].add_command(
                    label=opt, command=_setit(self.chosen_page, opt)
                )
            self.chosen_page.set(list_of_options[0])  # default value set

        self.chosen_sheet.trace("w", menu_dropdown)
        root.mainloop()

    def find_xlsx(self):
        """
        Choose xlsx file from file system
        """
        file = askopenfilename()
        if "xls" in file.split(".")[-1]:
            self.file_label["text"] = f'.../{"/".join(file.split("/")[-2:])}'
            self.filename = file
            self.start_button.grid(row=0, column=2, pady=(10, 5), padx=(10, 30))
        elif len(file) == 0:
            pass
        else:
            self.file_label["text"] = "Не xlsx"
            self.filename = ""
            self.start_button.grid_forget()

    def show_google_button(self):
        self.save_in_google_button.grid(row=1, column=2, pady=(5, 10), padx=(10, 30))

    def find_output_xlsx(self):
        """
        Choose xlsx file for saving in Google sheets from file system
        """
        file = askopenfilename()
        if "xls" in file.split(".")[-1]:
            self.output_file_label["text"] = f'.../{"/".join(file.split("/")[-2:])}'

            self.output_filename = file
            self.show_google_button()
        elif len(file) == 0:
            pass
        else:
            self.output_file_label["text"] = "Не xlsx"
            self.output_filename = ""
            self.save_in_google_button.grid_forget()
            pass
    @log_fun
    def read_and_fill_xlsx(self):
        """
        Read chosen xlsx file and create an output using 'file_handler';
        The function activates by pressing 'start_button'
        """
        dir_path = os.path.dirname(os.path.realpath(self.filename))

        # status label will be shown only if read_and_fill_xlsx func has stopped working
        self.file_label["text"] = "Ошибка при чтении файла"
        xlsx_content = read_excel(self.filename)
        xlsx_handler = FillXlsxFile(xlsx_content)
        xlsx_handler.get_all_source_urls()

        status = xlsx_handler.set_initpro_headers()
        if status:
            if status == "error":
                self.file_label["text"] = "Ошибка авторизации initpro"
                self.file_label["fg"] = "red"
                return
        self.file_label["text"] = "Ошибка при получении новых ссылок"
        xlsx_handler.get_all_new_links()
        xlsx_handler.change_links_in_xslx()

        self.file_label["text"] = "Ошибка при получении номеров извещения"
        xlsx_handler.get_all_notice_numbers()
        xlsx_handler.add_notice_numbers_to_xlsx()

        self.file_label["text"] = "Ошибка при получении дат окончания"
        xlsx_handler.get_all_debriefing_dates()

        self.file_label["text"] = "Ошибка при сохранении резульата"
        xlsx_handler.add_debriefing_dates_to_xlsx()
        xlsx_handler.save_xlsx(dir_path)

        self.file_label["text"] = "Готово"

        self.output_file_label["text"] = f"{dir_path}/output.xlsx"
        self.output_filename = f"{dir_path}/output.xlsx"
        self.filename = ""
        self.start_button.grid_forget()
        self.show_google_button()

    def save_in_google_sheets(self):
        """
        Save output of 'read_and_fill_xlsx' in Google sheets using 'update_google_sheets';
        The function activates by pressing 'google_button'
        """
        gs = GoogleSheet(
            file_path=self.output_filename,
            sheet_name=self.chosen_sheet.get(),
            worksheet=self.chosen_page,
        )
        status = gs.read_output()
        if status:
            if status == "error":
                self.output_file_label["text"] = "Неверный output"
                self.output_file_label["fg"] = "red"
                return
        gs.append_list()
        self.output_filename = ""
        self.output_file_label["text"] = "Готово"
        self.save_in_google_button.grid_forget()

    def update_bargaining_results(self):
        """
        Save output of 'read_and_fill_xlsx' in Google sheets using 'update_google_sheets';
        The function activates by pressing 'google_button'
        """
        gs = GoogleSheet(sheet_name=self.chosen_sheet.get(), worksheet=self.chosen_page)
        xlsx_handler = FillXlsxFile([])

        gs.update_all_bargaining_result(xlsx_handler.get_bargaining_result)
        self.update_results_in_google_button["text"] = "Обновлено успешно"
        print("Готово")


if __name__ == "__main__":
    gui = GraphicalInterface()
