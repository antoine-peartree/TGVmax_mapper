"""Contains graphical user interface object used by TGVmax destinations map."""

import os
import os.path
from tkinter import Tk, Frame, Label, Radiobutton, Scale, Button, StringVar
from tkinter import GROOVE, HORIZONTAL, LEFT, RIGHT
from tkinter import ttk
import datetime

from tkcalendar import Calendar
import webview
import requests
import pandas as pd

from geoloc import GeolocUpdater
from data_validity import TimeKeeper
from search import MapCreator

# Resources
RESOURCES_PATH = "resources/"
CSV_CUT = RESOURCES_PATH + "cut_tgvs.csv"
CSV_COORDS = RESOURCES_PATH + "city_coords.csv"
CSV_RESULT = RESOURCES_PATH + "result.csv"
UPDT_TMS_PATH = RESOURCES_PATH + "last_updt.json"
HTML_FILEPATH = RESOURCES_PATH + "map.html"

# Data download parameters
OPENDATA_URL = "https://data.sncf.com/explore/dataset/tgvmax/download" + \
    "/?format=csv&timezone=Europe/Berlin&use_labels_for_header=true"
CHUNK_SIZE = 1024*1024*1024
UPDT_DELAY_S = 12*60*60

# CSV useless columns
DISPO_TGVMAX = "Disponibilité de places TGV Max"
ENTITY = "ENTITY"
AXE = "Axe"
TRAIN_NO = "TRAIN_NO"
CODE_EQUIP = "CODE_EQUIP"
DEST_IATA = "Destination IATA"
ORIGINE_IATA = "Origine IATA"
ARRIVAL_TIME = "Heure_arrivee"
USELESS_COLUMNS = [DISPO_TGVMAX, ENTITY, AXE, TRAIN_NO, CODE_EQUIP, \
  DEST_IATA, ORIGINE_IATA, ARRIVAL_TIME]

# HTML parameters
HTML_MAPNAME = "TGVmax destinations map"
HTML_MIN_SIZE = (600, 450)

# Labels
APP_TITLE = "Carte des destinations TGVmax"
MODE = "mode"
CITY = "city"
TIME = "time"
ACTIONS = "actions"
DEPART_DATE = "depart_date"
DEPART_MINH = "depart_minh"
DEPART_MAXH = "depart_maxh"
RETURN_DATE = "return_date"
RETURN_MINH = "return_minh"
RETURN_MAXH = "return_maxh"
LABELS = {
    MODE : "Mode de recherche",
    CITY : "Ville de départ",
    ACTIONS : "Rechercher",
    DEPART_DATE : "Date de départ",
    DEPART_MINH : "Heure minimum de départ pour l'aller",
    DEPART_MAXH : "Heure maximum de départ pour l'aller",
    RETURN_MINH : "Heure minimum de départ pour le retour",
    RETURN_MAXH : "Heure maximum de départ pour le retour",
    RETURN_DATE : "Date de retour"
}
DEPARTURE_INFOS = {"date" : "2019-01-01", "minh" : "3", "maxh" : "23"}
RETURN_INFOS = {"date" : "2019-01-01", "minh" : "3", "maxh" : "23"}
DEFAULT_USER_INPUTS = {
    "mode" : "unknown",
    "origin_city" : "unknown",
    "departure" : DEPARTURE_INFOS,
    "return" : RETURN_INFOS
}

# Style parameters
RELIEF_TYPE = GROOVE
BG_COLOR = "black"
FG_COLOR = "white"
PARAM_FONT = 'Helvetica 12 bold'
CALENDAR_FONT = "Arial 12"


class LoadingUi:
    """UI loading display for downloading data when the app is starting."""

    def __init__(self):
        """Init loadingUI if timestamp is outdated."""
        self.time_keeper = TimeKeeper(UPDT_TMS_PATH, UPDT_DELAY_S)
        if not self.time_keeper.is_tms_outdated():
            self.update_needed = False
            return
        self.update_needed = True
        self.root = Tk()
        self.label = Label(self.root)
        self.button_action = Button(self.root)
        self.progress = ttk.Progressbar(self.root, orient="horizontal", \
            length=200, mode="determinate")
        self.progress_label = Label(self.root)

    def download_data(self, url, chunk_size, csv_path, cols_useless):
        """Download TGVmax possiblities from SNCF open database."""
        response = requests.get(url, stream=True)
        handle = open(csv_path, "wb")
        nb_chunks_dl = 0
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:  # filter out keep-alive new chunks
                handle.write(chunk)
                nb_chunks_dl += 1
                percent = round(nb_chunks_dl*100/88)
                print("Wait... "+str(percent)+"%")
                self.progress["value"] = percent
                self.progress_label.config(text=str(percent) + " %")
                self.progress.pack(padx=10, pady=10)
                self.progress_label.pack(padx=10)
                self.root.update()

        data = pd.read_csv(csv_path, sep=';')
        data = data[data[DISPO_TGVMAX] == 'OUI']
        for col in cols_useless:
            del data[col]
        os.remove(csv_path)
        data.to_csv(csv_path)

    def start_data_updt_cb(self):
        """Start data update."""
        self.button_action.pack_forget()
        self.progress.pack(padx=10, pady=10)
        self.progress_label.pack(padx=10)
        self.root.update()
        self.download_data(OPENDATA_URL, CHUNK_SIZE, CSV_CUT, USELESS_COLUMNS)
        self.time_keeper.write_cur_tms()
        self.root.destroy()

    def config(self):
        """Configure loadingUI elements."""
        self.root.title(APP_TITLE)
        self.label.config( \
            text="Les données SNCF locales datent de plus de 12 heures")
        self.button_action.config(command=self.start_data_updt_cb, \
            text="METTRE A JOUR")
        self.progress["value"] = 0
        self.progress["maximum"] = 100
        self.progress_label.config(text="0 %")

    def launch(self):
        """Launch loadingUI."""
        if not self.update_needed:
            return
        self.config()
        self.label.pack(padx=10, pady=10)
        self.button_action.pack(padx=10, pady=10)
        self.root.mainloop()


class MainUi:
    """Graphical user interface."""

    def __init__(self):
        """Initialise UI elements with their parents"""
        self.root = Tk()
        self.width = self.root.winfo_screenwidth()
        self.height = self.root.winfo_screenheight()

        self.frame1 = Frame(self.root)
        self.label_mode = Label(self.frame1)
        self.label_city = Label(self.frame1)
        self.cities = []
        self.menu_cities = ttk.Combobox(self.frame1)
        self.checkbox_oneway = Radiobutton(self.frame1)
        self.checkbox_roundtrip = Radiobutton(self.frame1)

        self.frame2 = Frame(self.root)
        self.frame2_1 = Frame(self.frame2)
        self.frame2_2 = Frame(self.frame2)
        self.label_date_depart = Label(self.frame2_1)
        self.label_hour_depart_min = Label(self.frame2_1)
        self.label_hour_depart_max = Label(self.frame2_1)
        self.scale_hour_depart_min = Scale(self.frame2_1)
        self.scale_hour_depart_max = Scale(self.frame2_1)
        self.calendar_depart = Calendar(self.frame2_1)
        self.label_date_return = Label(self.frame2_2)
        self.scale_hour_return_min = Scale(self.frame2_2)
        self.scale_hour_return_max = Scale(self.frame2_2)
        self.label_hour_return_min = Label(self.frame2_2)
        self.label_hour_return_max = Label(self.frame2_2)
        self.calendar_return = Calendar(self.frame2_2)
        self.label_middle_calendar = Label(self.frame2)

        self.frame3 = Frame(self.root)
        self.button_action = Button(self.frame3)
        self.roundtrip_choice = None

    def search_cb(self):
        """Callback for search button."""
        self.button_action.config(text="CHARGEMENT ...")
        self.button_action.pack(padx=10, pady=10)
        self.root.update()

        if self.roundtrip_choice is None:
            print("Choisissez un mode (aller ou aller/retour)")
            return
        user_inputs = DEFAULT_USER_INPUTS
        user_inputs["mode"] = self.roundtrip_choice
        user_inputs["origin_city"] = self.menu_cities.get()
        user_inputs["departure"]["date"] = self.calendar_depart.selection_get()
        user_inputs["departure"]["minh"] = self.scale_hour_depart_min.get()
        user_inputs["departure"]["maxh"] = self.scale_hour_depart_max.get()

        if self.roundtrip_choice:
            user_inputs["return"]["date"] = self.calendar_return.selection_get()
            user_inputs["return"]["minh"] = self.scale_hour_return_min.get()
            user_inputs["return"]["maxh"] = self.scale_hour_return_max.get()

        map_creator = MapCreator(HTML_FILEPATH, CSV_CUT, CSV_COORDS, CSV_RESULT)
        map_creator.generate(user_inputs)
        webview.create_window(HTML_MAPNAME, HTML_FILEPATH, \
            min_size=HTML_MIN_SIZE)
        self.button_action.config(text="Lancer la recherche")
        self.button_action.pack(padx=10, pady=10)
        self.root.update()
        del map_creator
        webview.start(gui='cef', debug=True)

    def checkbox_roundtrip_cb(self):
        """Callback for roundtrip checkbox."""
        self.roundtrip_choice = True
        self.label_middle_calendar.pack(side=LEFT, padx=10)
        self.frame2_2.pack(side=RIGHT)

    def checkbox_oneway_cb(self):
        """Callback for oneway checkbox."""
        self.roundtrip_choice = False
        self.label_middle_calendar.pack_forget()
        self.frame2_2.pack_forget()

    def config_root(self):
        """Configure root graphical window."""
        self.root.title(APP_TITLE)
        self.root.geometry(str(max(800, round(self.width/3))) + \
           "x" + str(round(self.height*0.8)))

    def config_elements(self):
        """Main configurations of UI elements."""
        self.label_mode.configure(text=LABELS[MODE])
        self.label_city.configure(text=LABELS[CITY])
        self.checkbox_oneway.configure(text="Aller simple", \
            value=0, command=self.checkbox_oneway_cb)
        self.checkbox_roundtrip.configure(text="Aller-retour", \
            value=1, command=self.checkbox_roundtrip_cb)

        self.cities = GeolocUpdater.get_dest_list(CSV_CUT)
        self.menu_cities.configure(values=self.cities)
        self.menu_cities.set("Choisissez une ville de départ")

        self.label_date_depart.configure(text=LABELS[DEPART_DATE])
        self.label_date_return.configure(text=LABELS[RETURN_DATE])
        self.label_hour_depart_min.configure(text=LABELS[DEPART_MINH])
        self.label_hour_depart_max.configure(text=LABELS[DEPART_MAXH])
        self.label_hour_return_min.configure(text=LABELS[RETURN_MINH])
        self.label_hour_return_max.configure(text=LABELS[RETURN_MAXH])

        self.root.update()
        scale_length = self.root.winfo_width()/3
        self.scale_hour_depart_min.configure(from_=3, to=24, resolution=1, \
            orient=HORIZONTAL, length=scale_length, width=20, tickinterval=20, \
            variable=StringVar(value=3))
        self.scale_hour_depart_max.configure(from_=3, to=24, resolution=1, \
            orient=HORIZONTAL, length=scale_length, width=20, tickinterval=20, \
            variable=StringVar(value=23))
        self.scale_hour_return_min.configure(from_=3, to=24, resolution=1, \
            orient=HORIZONTAL, length=scale_length, width=20, tickinterval=20, \
            variable=StringVar(value=3))
        self.scale_hour_return_max.configure(from_=3, to=24, resolution=1, \
            orient=HORIZONTAL, length=scale_length, width=20, tickinterval=20, \
            variable=StringVar(value=23))

        mindate = datetime.date.today()
        maxdate = mindate + datetime.timedelta(days=31)
        self.calendar_depart.configure(selectmode='day', locale='fr', \
            mindate=mindate, maxdate=maxdate, \
            disabledforeground='red', cursor="hand1")
        self.calendar_return.configure(selectmode='day', locale='fr', \
            mindate=mindate, maxdate=maxdate, \
            disabledforeground='red', cursor="hand1")
        self.label_middle_calendar.configure(text=">>>>>>")

        self.button_action.configure(text="Lancer la recherche", \
            command=self.search_cb)

    def config_background(self):
        """Configure elements background color."""
        self.root.configure(bg=BG_COLOR)
        self.frame1.configure(bg=BG_COLOR)
        self.frame2.configure(bg=BG_COLOR)
        self.frame3.configure(bg=BG_COLOR)
        self.frame2_1.configure(bg=BG_COLOR)
        self.frame2_2.configure(bg=BG_COLOR)
        self.label_mode.configure(bg=BG_COLOR)
        self.label_city.configure(bg=BG_COLOR)
        self.label_date_depart.configure(bg=BG_COLOR)
        self.label_hour_depart_min.configure(bg=BG_COLOR)
        self.label_hour_depart_max.configure(bg=BG_COLOR)
        self.label_date_return.configure(bg=BG_COLOR)
        self.label_hour_return_min.configure(bg=BG_COLOR)
        self.label_hour_return_max.configure(bg=BG_COLOR)
        self.button_action.configure(bg="white")
        self.label_middle_calendar.configure(bg="green")

    def config_foreground(self):
        """Configure elements foreground color."""
        self.label_mode.configure(fg=FG_COLOR)
        self.label_city.configure(fg=FG_COLOR)
        self.label_middle_calendar.configure(fg=FG_COLOR)
        self.label_date_depart.configure(fg=FG_COLOR)
        self.label_hour_depart_min.configure(fg=FG_COLOR)
        self.label_hour_depart_max.configure(fg=FG_COLOR)
        self.label_date_return.configure(fg=FG_COLOR)
        self.label_hour_return_min.configure(fg=FG_COLOR)
        self.label_hour_return_max.configure(fg=FG_COLOR)

    def config_border(self):
        """Configure frame borders."""
        self.frame1.configure(borderwidth=2)
        self.frame2.configure(borderwidth=2)
        self.frame3.configure(borderwidth=0)

    def config_relief(self):
        """Configure frame relief."""
        self.frame1.configure(relief=RELIEF_TYPE)
        self.frame2.configure(relief=RELIEF_TYPE)
        self.frame3.configure(relief=RELIEF_TYPE)
        self.frame2_1.configure(relief=RELIEF_TYPE)
        self.frame2_2.configure(relief=RELIEF_TYPE)

    def config_font(self):
        """Configure texts font."""
        self.label_mode.configure(font=PARAM_FONT)
        self.label_city.configure(font=PARAM_FONT)
        self.label_middle_calendar.configure(font=PARAM_FONT)
        self.label_date_depart.configure(font=PARAM_FONT)
        self.label_hour_depart_min.configure(font=PARAM_FONT)
        self.label_hour_depart_max.configure(font=PARAM_FONT)
        self.label_date_return.configure(font=PARAM_FONT)
        self.label_hour_return_min.configure(font=PARAM_FONT)
        self.label_hour_return_max.configure(font=PARAM_FONT)
        self.calendar_depart.configure(font=CALENDAR_FONT)
        self.calendar_return.configure(font=CALENDAR_FONT)

    def configure(self):
        """Call configuring functions."""
        self.config_root()
        self.config_elements()
        self.config_background()
        self.config_foreground()
        self.config_border()
        self.config_relief()
        self.config_font()

    def pack(self):
        """Pack elements."""
        self.frame1.pack(padx=10, pady=10)
        self.frame2.pack(padx=10, pady=10)
        self.frame3.pack(padx=10, pady=10)

        self.label_mode.pack(padx=10, pady=10)
        self.checkbox_oneway.pack(padx=10, pady=10)
        self.checkbox_roundtrip.pack()
        self.label_city.pack(padx=10, pady=10)
        self.menu_cities.pack(padx=10, pady=10)

        self.frame2_1.pack(side=LEFT)
        self.label_middle_calendar.pack(side=LEFT, padx=10)
        self.frame2_2.pack(side=RIGHT)

        self.label_date_depart.pack(padx=10)
        self.calendar_depart.pack(padx=10)
        self.label_hour_depart_min.pack(padx=10, pady=10)
        self.scale_hour_depart_min.pack()
        self.label_hour_depart_max.pack(padx=10, pady=10)
        self.scale_hour_depart_max.pack(pady=10)

        self.label_date_return.pack(padx=10)
        self.calendar_return.pack(padx=10)
        self.label_hour_return_min.pack(padx=10, pady=10)
        self.scale_hour_return_min.pack()
        self.label_hour_return_max.pack(padx=10, pady=10)
        self.scale_hour_return_max.pack(pady=10)

        self.button_action.pack(padx=10, pady=10)

    def run(self):
        """Run the graphical interface loop."""
        self.root.mainloop()
