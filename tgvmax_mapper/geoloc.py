"""Manage cities geolocalisation coordinates"""

import os
import time

import pandas as pd
from geopy.geocoders import Nominatim

CSV_TEMPGEOLOC = "resources/tempgeoloc.csv"

class GeolocUpdater:
    """Fill the CSV file with associating a city with its GPS coordinates"""

    def __init__(self, csv_src, csv_geoloc_temp, csv_dest):
        self.csv_src = csv_src
        self.csv_geoloc_temp = csv_geoloc_temp
        self.csv_dest = csv_dest

    def get_explicit_name(dest):
        """Get explicit names for some destinations"""
        if dest == "PARIS (intramuros)":
            return "PARIS"
        if dest == "CORBIERES VIERZON VILLE":
            return "VIERZON"
        if dest == "VALENCE TGV RHONE ALPES SUD":
            return "VALENCE FRANCE ALPES"
        if dest == "MONTELIMAR GARE SNCF":
            return "MONTELIMAR"
        if dest == "CORBIERES LES AUBRAIS ORLEANS":
            return "ORLEANS"
        if dest == "LYON (gares intramuros)":
            return "LYON"
        if dest == "AEROPORT CDG2 TGV ROISSY":
            return "ROISSY AEROPORT"
        if dest == "ST DENIS PRES MARTEL":
            return "MARTEL"
        if dest == "DIE":
            return "GARE DIE"
        if dest == "JUVISY TGV":
            return "GARE JUVISY"
        if dest == "ORANGE":
            return "ORANGE FRANCE"
        if dest == "SABLE":
            return "SABLE SUR SARTHE"
        return dest

    def get_dest_list(csv_src):
        """Get destinations list"""
        df_src = pd.read_csv(csv_src)
        return GeolocUpdater.get_unique_destinations(df_src)

    def get_unique_destinations(df_src):
        """Get the list of unique destinations (without duplicatas)"""
        destinations = []
        for dest in df_src["Destination"]:
            found = False
            for already_dest in destinations:
                if dest == already_dest:
                    found = True
                    break
            if not found:
                destinations.append(dest)
        destinations.sort(key=lambda x: x[0][0])
        return destinations

    def generate(self):
        """Get GPS coordinates for each city"""
        destinations = GeolocUpdater.get_dest_list(self.csv_src)

        dataframe = pd.DataFrame(data={"CITY": destinations})
        dataframe["LAT"] = 0.0000
        dataframe["LON"] = 0.0000
        row = 0

        for city in destinations:
            if os.path.isfile(self.csv_geoloc_temp):
                df_already_written = pd.read_csv(self.csv_geoloc_temp)
                if df_already_written["LAT"][row] != 0.0000:
                    dataframe["LAT"][row] = \
                        df_already_written["LAT"][row]
                    dataframe["LON"][row] = \
                        df_already_written["LON"][row]
                    row += 1
                    continue
            city = GeolocUpdater.get_explicit_name(city)
            time.sleep(0.1)
            geolocator = Nominatim()
            loc = geolocator.geocode(city)
            if loc is None:
                print("ERROR : cannot find location for " + city)
            else:
                dataframe["LAT"][row] = loc.latitude
                dataframe["LON"][row] = loc.longitude
            row += 1
            print(str(round(row/len(destinations)*100, 2))+" %")

            dataframe.to_csv(self.csv_geoloc_temp)
        os.remove(self.csv_geoloc_temp)
        dataframe.to_csv(self.csv_dest)
