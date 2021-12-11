def get_web_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36 Vivaldi/4.3',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive'
    }

    import ssl, certifi, urllib.request
    req = urllib.request.Request(url, headers=headers)
    context = ssl.create_default_context(cafile=certifi.where())
    response = urllib.request.urlopen(req, context=context)
    return response.read().decode('utf-8')

from bs4 import BeautifulSoup
def get_filtered_web_content(url, tag, tag_class):
    content = get_web_content(url)

    soup = BeautifulSoup(content, features='html.parser')
    return soup.find_all(tag, class_ = tag_class)

def get_plans_web_content(url): return get_filtered_web_content(url, 'div', 'card')
def get_workouts_web_content(url): return get_filtered_web_content(url, 'article', 'workout')

from zwift_workout import ZWorkout
class Parser:
    """
    A class is used to parse any **bike** zwift workout, presented on the 
    www.whatsonzwift.com
    """

    def __init__(self, export_dir, *urls) -> None:
        """
        Parameters 
        ----------
        export_dir : str 
                The folder that is used to save all the parsed workouts. 
        urls : List[str]
                A list of urls that need to be parsed, can be either a 
                direct link to a single workout, plan or a page which 
                contains multiple plans/workouts. 
        """
        self.export_dir = export_dir
        for i, url in enumerate(urls): 
            print(f'Parsing url {url} ({i+1}/{len(urls)})')
            parsed = self.__try_parse(url) 
            if not parsed: 
                print(f"Couldn't find a parser for {url} hence skipping it.")
                continue
    
    def __try_parse(self, url):
        parsed = self.__try_parse_plans(url); 
        if not parsed: 
            parsed = self.__try_parse_workout(url);  
        return parsed 

    def __try_parse_plans(self, url):
        plans_data = get_plans_web_content(url); 
        if not plans_data: return False;   
        any_parsed = False  
        for i, plan_data in enumerate(plans_data):
            card_sports = plan_data.find('div', class_='card-sports')
            if not card_sports: continue

            card_classes = card_sports.i['class']
            valid = ZWorkout.is_valid_sport_type(card_classes) 
            url = plan_data.find('a', class_='button')['href']

            if not valid: 
                print(f"Couldn't parse {url} because some of the {card_classes} sports are not suppored yet") 
                continue

            print(f"Parsing plan ({i+1}/{len(plans_data)})")
            self.__try_parse_workout(url)
            any_parsed = True 
        return any_parsed 

    def __try_parse_workout(self, url):
        workouts_data = get_workouts_web_content(url) 
        if not workouts_data: 
            print(f"Coulnd't get workout data by {url} for unknown reason.")
            return False 

        for i, workout_data in enumerate(workouts_data): 
            print(f"- Parsing workout ({i+1}/{len(workouts_data)})")
            ZWorkout(workout_data).save(self.export_dir)
        return True 

import argparse  
if __name__ == '__main__': 
    parser = argparse.ArgumentParser(description="Parses Zwift workouts from www.whatsonzwift.com")
    parser.add_argument('urls', metavar='URLs', type=str, nargs="+", help="an URL of the workout to parse")
    parser.add_argument("--output",  nargs="?", help="output directory of the parsed workouts")
    args = vars(parser.parse_args()) 
    
    if 'urls' in args and args['urls']: 
        urls = args['urls'] 
        export_dir = args['output'] if 'output' in args and args['output'] else 'export/'
        Parser(export_dir, *urls)