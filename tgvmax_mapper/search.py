"""Create TGVmax destinations html map with given user infos."""

import gc

import folium
import pandas as pd

DATE = "DATE"
ORIGINE = "Origine"
DESTINATION = "Destination"
DEPART_TIME = "Heure_depart"
LAT = "LAT"
LON = "LON"

HTML_DEFAULT_ZOOM = 4
HTML_TILES = "Stamen Terrain"

class DataProcess:
    """Methods used for data processing."""

    def __init__(self, csv_cut_path, csv_results_path):
        """Init data process csv paths"""
        self.csv_cut_path = csv_cut_path
        self.csv_results_path = csv_results_path

    def convert_date(self, date_in):
        """Add missing zeroes for getting the correct date format."""
        str_year = str(date_in.year)
        str_month = str(date_in.month)
        str_day = str(date_in.day)
        if date_in.month < 10:
            str_month = "0" + str_month
        if date_in.day < 10:
            str_day = "0" + str_day
        return str_year + "-" + str_month + "-" + str_day

    def datetime_limit(self, datafrm, time_infos):
        """Drop journeys out of the specified date and time."""
        datafrm = datafrm[datafrm[DATE] == time_infos["date"]]
        datafrm['int'] = int(time_infos["minh"])
        datafrm = datafrm[list(map(int, \
            datafrm[DEPART_TIME].str.slice(0, -3))) >= datafrm['int']]
        datafrm['int'] = int(time_infos["maxh"])
        datafrm = datafrm[list(map(int, \
            datafrm[DEPART_TIME].str.slice(0, -3))) < datafrm['int']]
        del datafrm['int']
        return datafrm

    def get_journeys(self, depart_city, time_infos, column_from, column_to):
        """Calculate possibilities linked with the departure city."""
        datafrm = pd.read_csv(self.csv_cut_path, sep=';')

        datafrm = self.datetime_limit(datafrm, time_infos)
        datafrm = datafrm[datafrm['Disponibilité de places MAX JEUNE et MAX SENIOR'] == 'OUI']
        datafrm = datafrm[datafrm[column_from] == depart_city]
        datafrm["CommonDest"] = datafrm[column_to]
        return datafrm

    def delete_oneway(self, dataframe, column1, column2):
        """Delete lines with first column cities missing into 2nd column."""
        for dest in column1:
            found = False
            for origin in column2:
                if dest == origin:
                    found = True
                    break
            if not found:
                dataframe = dataframe[dataframe[DESTINATION] != dest]
                dataframe = dataframe[dataframe[ORIGINE] != dest]
        return dataframe

    def keep_only_round_trips(self, dataframe):
        """Delete one-way journeys."""
        dataframe = self.delete_oneway(dataframe, \
            dataframe[DESTINATION], dataframe[ORIGINE])
        dataframe = self.delete_oneway(dataframe, \
            dataframe[ORIGINE], dataframe[DESTINATION])
        return dataframe

    def sort_journeys(self, dataframe):
        """Sort journeys by destination first, then date and finally hours."""
        dataframe['hour_diz'] = dataframe[DEPART_TIME].str.get(-5)
        dataframe['hour_uni'] = dataframe[DEPART_TIME].str.get(-4)
        dataframe = dataframe.sort_values(by=['CommonDest', \
            DATE, 'hour_diz', 'hour_uni'], na_position='first')

        for col in ["CommonDest", "hour_diz", "hour_uni"]:
            del dataframe[col]
        dataframe.to_csv(self.csv_results_path)


class MapCreator:
    """Create Destinations map within user entries."""

    def __init__(self, html_filepath, csv_cut_path, csv_coord_path, \
            csv_result_path):
        """Init the map creator with filepaths and DataProcess object."""
        pd.set_option('mode.chained_assignment', None)
        self.html_filepath = html_filepath
        self.csv_cut_path = csv_cut_path
        self.csv_coord_path = csv_coord_path
        self.csv_result_path = csv_result_path
        self.data_process = DataProcess(csv_cut_path, csv_result_path)

    def retrieve_geoloc(self, dest, dataframe, df_coord, row):
        """Retrieve a city geolocalisation from the coordinates CSV."""
        list_lat = df_coord[LAT]
        list_lon = df_coord[LON]
        found = False
        row_coord = 0
        for city in df_coord['CITY']:
            if dest == city:
                dataframe[LAT][row] = round(list_lat[row_coord], 6)
                dataframe[LON][row] = round(list_lon[row_coord], 6)
                found = True
                break
            row_coord += 1
        if not found:
            dataframe[LAT][row], dataframe[LON][row] = 0.0, 0.0
            print("ERROR : " + dest + " geolocalisation not found")
        return dataframe

    def add_geoloc(self, depart_city):
        """Add geolocalisation informations for each destination."""
        dataframe = pd.read_csv(self.csv_result_path)
        df_coord = pd.read_csv(self.csv_coord_path)

        dataframe[LAT], dataframe[LON] = 0.0, 0.0
        row = 0
        for dest in dataframe[DESTINATION]:
            if dest != depart_city:
                dataframe = self.retrieve_geoloc(dest, dataframe, df_coord, row)
            row += 1

        for col in ['Unnamed: 0', 'Unnamed: 0.1']:
            del dataframe[col]
        dataframe.to_csv(self.csv_result_path)

    def get_origine_geoloc(self, origine):
        """Get origine city GPS coordinates."""
        df_coord = pd.read_csv(self.csv_coord_path)
        lat, lon = 0.0, 0.0
        row_coord = 0
        for city in df_coord['CITY']:
            if origine == city:
                lat = round(df_coord[LAT][row_coord], 6)
                lon = round(df_coord[LON][row_coord], 6)
                return [lat, lon]
            row_coord += 1
        print("ERROR : origine " + origine + " geolocalisation not found")
        return [lat, lon]

    def concat_travel_infos(self, dest, d_depart, h_depart, d_return, h_return):
        """Concatenate travel infos."""
        if (d_return and h_return):
            return dest + " -- Aller le " + d_depart + " à " + h_depart + \
                " -- Retour le " + d_return + " à " + h_return
        return dest + " -- Aller le " + d_depart + " à " + h_depart

    def display(self, origin, roundtrip):
        """Display results onto an HTML geographic map."""
        dataframe = pd.read_csv(self.csv_result_path)
        depart_times = dataframe[DEPART_TIME]

        origin_coords = self.get_origine_geoloc(origin)

        destmap = folium.Map(location=origin_coords, \
            zoom_start=HTML_DEFAULT_ZOOM, \
            tiles=HTML_TILES)

        folium.Marker(location=origin_coords, tooltip=origin, \
            icon=folium.Icon(color="green", icon="info-sign")).add_to(destmap)

        h_depart, d_depart, h_return = "unknown", "unknown", "unknown"
        prev_city, real_dest = "unknown", "unknown"
        dest_points = [0.0, 0.0]
        row = -1
        for dest in dataframe[DESTINATION]:
            row += 1
            if dest == origin:
                if dest == prev_city:
                    if depart_times[row] == depart_times[row-1]:
                        continue
                    h_return += " ou " + depart_times[row]
                else:
                    h_return = depart_times[row]

                travel_infos = self.concat_travel_infos(real_dest, d_depart, \
                    h_depart, dataframe[DATE][row], h_return)

                folium.Marker(location=dest_points, tooltip=travel_infos, \
                    icon=folium.Icon(color="red", icon="info-sign") \
                ).add_to(destmap)
                prev_city = dest
                continue

            real_dest = dest
            dest_points = [dataframe[LAT][row], \
                dataframe[LON][row]]
            d_depart = dataframe[DATE][row]
            if dest == prev_city:
                if depart_times[row] == depart_times[row-1]:
                    continue
                h_depart += " ou " + depart_times[row]
            else:
                h_depart = depart_times[row]

            if not roundtrip:
                travel_infos = self.concat_travel_infos(real_dest, d_depart, \
                    h_depart, dataframe[DATE][row], h_return)
                folium.Marker(location=dest_points, \
                    tooltip=self.concat_travel_infos(dest, d_depart, h_depart, \
                    "", ""), icon=folium.Icon(color="red", icon="info-sign") \
                ).add_to(destmap)
            prev_city = dest
        destmap.save(self.html_filepath)

    def generate(self, user_entries):
        """Generate destinations map and save it into HTML format."""
        mode_roundtrip = user_entries["mode"]
        depart_city = user_entries["origin_city"]

        depart_time = user_entries["departure"]
        depart_time["date"] = \
		self.data_process.convert_date(depart_time["date"])

        df_out = self.data_process.get_journeys(depart_city, depart_time, \
            ORIGINE, DESTINATION)
        df_out.to_csv(self.csv_result_path)

        if mode_roundtrip:
            return_time = user_entries["return"]
            return_time["date"] = \
		    self.data_process.convert_date(return_time["date"])
            df_in = self.data_process.get_journeys(depart_city, return_time, \
                DESTINATION, ORIGINE)
            with open(self.csv_result_path, 'a') as file_towrite:
                df_in.to_csv(file_towrite, header=False)
            dataframe = pd.read_csv(self.csv_result_path)
            dataframe = self.data_process.keep_only_round_trips(dataframe)
            self.data_process.sort_journeys(dataframe)
        else:
            dataframe = pd.read_csv(self.csv_result_path)
            self.data_process.sort_journeys(dataframe)
        self.add_geoloc(depart_city)
        self.display(depart_city, mode_roundtrip)
        gc.collect()
