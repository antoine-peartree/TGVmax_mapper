"""Determine data validity"""

import os
import json
import time

TIMESTAMP_LABEL = 'timestamp'

class TimeKeeper:
    """Manage informations about data validity"""

    def __init__(self, update_tms_path, update_delay_s):
        """Init Time Keeper for further data validity checking"""
        self.update_tms_path = update_tms_path
        self.update_delay_s = update_delay_s

    def write_cur_tms(self):
        """Write current timestamp into json file"""
        data = {}
        data[TIMESTAMP_LABEL] = time.time()
        with open(self.update_tms_path, 'w') as outfile:
            json.dump(data, outfile)

    def get_updt_tms(self):
        """Read previous timestamp from json file"""
        with open(self.update_tms_path) as infile:
            data = json.load(infile)
        return data[TIMESTAMP_LABEL]

    def is_tms_outdated(self):
        """Compare previous update timestamp with current one"""
        if not os.path.isfile(self.update_tms_path):
            return True
        return time.time() > self.get_updt_tms() + self.update_delay_s
