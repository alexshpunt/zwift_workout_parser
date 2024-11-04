from typing import List
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, element
from zwift_intervals import * 
from enum import Enum 

class ZWorkoutParseMode(Enum): 
    DEFAULT = 1
    SKIP = 2 
    REPLACE = 3 
    
class ZWorkout(): 
    def parse_values(article: element.Tag):
        breadcrumbs = article.select_one('div.breadcrumbs')
        return breadcrumbs.find('h4')['class']

    def is_bike_workout(article: element.Tag):
        """Checks if the parsed workout is a bike workout

        Parameters 
        ----------
        class_values : List[str]
                    A list of the class values on the workout's html page         
        """
        class_values = ZWorkout.parse_values(article)
        return len([s for s in class_values if 'bike' in s]) > 0

    def is_run_workout(article: element.Tag):
        """Checks if the parsed workout is a run workout

        Parameters 
        ----------
        class_values : List[str]
                    A list of the class values on the workout's html page         
        """

        class_values = ZWorkout.parse_values(article)
        return len([s for s in class_values if 'run' in s]) > 0

class ZRunWorkout():
    def __init__(self, article: element.Tag, mode: ZWorkoutParseMode = ZWorkoutParseMode.DEFAULT) -> None:
        pass

class ZBikeWorkout(): 
    def is_valid_sport_type(class_values: List[str]):
        """Checks if workout's sport type is supported by the parser

        At the moment the parser supports only the bike workouts, 
        so this function checks if there is a bike type in the sport 
        types.

        Parameters 
        ----------
        class_values : List[str]
                    A list of the class values on the workout's html page         
        """

        return len([s for s in class_values if 'bike' in s]) > 0
        
    def parse_interval(raw_str: str): 
        """Returns an interval based on some specific format of input raw interval string
        
        Return
        ------
        ZFreeRide - If the raw interval string contains a 'free ride' sub-string in it
                    for example '10 min free ride'
        ZBikeRangedInterval - If the raw interval string contains a 'from','to' pair of the sub-strings
                    for example '1 min from 50 to 90% FTP' 
        ZIntervalT - If the raw interval string contains a 'x' symbol (meaning times)
                    for example '10x 3min @ 100% FTP, 1 min @ 55% FTP'
        ZBikeSteadyState - Otherwise
                    for example '3min @ 100rpm, 95% FTP'
        """

        if 'free ride' in raw_str: return ZFreeRide(raw_str) #10min free ride 
        if 'from' in raw_str and 'to' in raw_str: return ZBikeRangedInterval(raw_str) #1min from 50 to 90% FTP
        if 'x' in raw_str: return ZBikeIntervalsT(raw_str) #10x 3min @ 100% FTP, 1min @ 55% FTP
        return ZBikeSteadyState(raw_str) #3min @ 100rpmm, 95% FTP

    def __init__(self, article: element.Tag, mode: ZWorkoutParseMode = ZWorkoutParseMode.DEFAULT) -> None:
        self.path, self.filename = (None, None)
        self.mode = mode
        breadcrumbs = article.select_one('div.breadcrumbs')
        sport_type = breadcrumbs.find('h4')['class']

        self.valid = ZBikeWorkout.is_valid_sport_type(sport_type)
        if not self.valid: return 
        
        try: 
            breadcrumbs = [item.string.strip() for item in breadcrumbs] 
        except Exception as e: 
            #Sometimes if @ is contained in the breadcrumbs, it might be obfuscated with Cloudflare, so 
            # it's not really possible to deobfuscate it back. This is why we just ignore it.  
            self.valid = False
            return 

        breadcrumbs = [slugify(b) for b in breadcrumbs if len(b) > 0 and b != '»' and b != 'Workouts']
        self.filename = breadcrumbs.pop(-1)
        self.path = '/'.join(breadcrumbs)
        self.intervals = [] 

        download_button = [a for a in article.find_all('a') if a.string and 'Download workout' in a.string]
        self.download_link = download_button[0]['href'] if download_button and self.mode is not ZWorkoutParseMode.DEFAULT else None
        if not self.download_link: 
            def convert_to_string(data):
                output = [] 
                if isinstance(data, element.NavigableString): return data.string
                for content in data.contents:
                    if isinstance(content, str): output.append(content)
                    else: output.extend([convert_to_string(c) for c in content.contents])
                return "".join(output)

            data = article.select_one('div.one-third.column.workoutlist')
            for div in data.find_all('div'):
                interval = "".join([convert_to_string(c) for c in div.contents]) 
                self.intervals.append(ZBikeWorkout.parse_interval(interval))

        overview = article.select_one('div.overview')
        self.author = 'Zwift Workouts Parser'
        self.description = overview.next_sibling
        if 'Author:' in overview.next_sibling.get_text():
            self.author = overview.next_sibling
            self.description = self.author.next_sibling

        if not isinstance(self.author, str) and 'Author:' in self.author.get_text(): 
            _, self.author = self.author.get_text().split('Author:')
        self.description = self.description.get_text("\n")

        self.name = 'Zwift Workout'
        self.sport_type = 'bike' 
        self.lookup = {
            'author': self.author,
            'name': self.name,
            'description': self.description,
            'sport_type': self.sport_type,
        }

    def save(self, export_dir: str): 
        """Saves workout to a specific folder 

        Params
        ------
        export_dir : str 
                    Folder to save the workout 
        """
        if not self.valid: return

        workout_fullname = f"{self.path}/{self.filename}"
        text = ""
        if not self.download_link:
            data = self.to_xml() 
            import xml.etree.ElementTree as ET
            text = ET.tostring(data)
            xml_header = b'<?xml version="1.0" encoding="utf-8"?>'
            text = BeautifulSoup(text, 'xml').prettify().encode('utf-8')
            text = text.replace(xml_header, b'').strip()
        elif self.mode is ZWorkoutParseMode.REPLACE:
            import requests 
            url = f"https://whatsonzwift.com{self.download_link}"
            text = requests.get(url, allow_redirects=True).content
        else: 
            print(f"-- Skipped workout {workout_fullname}")
            return 

        directory = f"{export_dir}/{self.path}"

        from os import path, makedirs
        if not path.isdir(directory): makedirs(directory)

        with open(f"{directory}/{slugify(self.filename, True)}.zwo", 'wb') as f: 
            f.write(text)

        file_version = "Original" if self.download_link else "Parsed"
        print(f"-- Parsed workout {workout_fullname} ({file_version})")

    def to_xml(self, root : ET.Element = None) -> ET.Element:
        """Creates an XML element from the workout data 

        Params
        root : ET.Element 
                Root of the created workout XML element 
        """
        root = ET.Element('workout_file')
        for k,v in self.lookup.items(): 
            ET.SubElement(root, k).text = v
        tags = ET.SubElement(root, 'tags')
        for t in tags: 
            tag = ET.SubElement(tags, 'tag')
            tag.set('name', t)

        workout = ET.SubElement(root, 'workout')
        for i in self.intervals: i.to_xml(workout)
        return root 

import unicodedata
import re
def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value)
    return re.sub(r'[-\s]+', '-', value).strip('-_')