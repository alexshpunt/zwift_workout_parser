from __future__ import annotations
from bs4 import BeautifulSoup, element
from webhelper import get_web_content
from typing import Dict

def purify_workout_data(data : element.Tag): 
    workout = []
    for row in data.find_all('div'):
        workout_set = [] 
        for content in row.contents: 
            if isinstance(content, element.Tag): workout_set.append("".join(content.contents)) 
            else: workout_set.append(content)
        workout.append("".join(workout_set))
    return workout

def parse_workout(article: element.Tag) -> Dict:
    breadcrumbs = [item.string.strip() for item in article.select_one('div.breadcrumbs')] 
    breadcrumbs = [item for item in breadcrumbs if len(item) > 0 and item != '»' and item != 'Workouts']
    filename = breadcrumbs.pop(-1)
    directory = '/'.join(breadcrumbs)
    
    print(f"Parsing {directory}/{filename}")

    workout_data = article.select_one('div.one-third.column.workoutlist')
    pure_workout_data = purify_workout_data(workout_data) 

    from workout import ZWorkout, ZWorkoutFile
    parsed_workout = ZWorkout.parse(pure_workout_data)

    workout_overview = article.select_one('div.overview')
    workout_author = 'Zwift Workouts Parser'
    workout_desc = workout_overview.next_sibling
    if 'Author' in workout_overview.next_sibling.get_text():
        workout_author = workout_overview.next_sibling
        workout_desc = workout_author.next_sibling

    if not isinstance(workout_author, str) and 'Author' in workout_author.get_text(): 
        _, workout_author = workout_author.get_text().split('Author:')
    workout_desc = workout_desc.get_text("\n")

    workout_file = ZWorkoutFile(parsed_workout, 
                                name=filename, author=workout_author.strip(), description=workout_desc) 

    data = workout_file.write()
    import xml.etree.ElementTree as ET
    text = ET.tostring(data)
    xml_header = b'<?xml version="1.0" encoding="utf-8"?>'
    text = BeautifulSoup(text, 'xml').prettify().encode('utf-8')
    text = text.replace(xml_header, b'').strip()
    
    return {
        'directory': directory,
        'filename': filename,
        'text': text
    }

def get_workout_data(url):
    content = get_web_content(url)
    soup = BeautifulSoup(content, features='html.parser')
    workouts = soup.find_all('article', class_ = 'workout')
    return workouts

def save_plan(plan_url, export_dir): 
    print(f"Saving plan by {plan_url}")
    workouts = get_workout_data(plan_url)
    from tqdm import tqdm

    for workout in tqdm(workouts):
        save_workout(workout, export_dir)

def save_workout(workout, export_dir): 
    def unpack(directory, filename, text): return directory, filename, text
    directory, filename, text = unpack(**parse_workout(workout))
    directory = f"{export_dir}/{directory}"

    from os import path, makedirs
    if not path.isdir(directory): makedirs(directory)

    from utility import slugify
    with open(f"{directory}/{slugify(filename, True)}.zwo", 'wb') as f: 
        f.write(text)

def parse_plans(url, export_dir): 
    content = get_web_content(url)
    soup = BeautifulSoup(content, features='html.parser')
    plans = soup.find_all('div', class_ = 'card')
    for plan in plans: 
        sport = "".join([i for i in plan.find('div', class_='card-sports').i['class'] if 'bike' in i])
        if not sport: continue
        plan_url = plan.find('a', class_='button')['href']
        if 'ftp-tests' in plan_url: continue
        save_plan(plan_url, export_dir)