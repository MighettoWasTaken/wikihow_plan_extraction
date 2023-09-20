from typing import List

import os
import re
import json
import requests
# https://requests.readthedocs.io/projects/requests-html/en/latest/
from requests_html import HTMLSession
import argparse
from absl import logging
from bs4 import BeautifulSoup
from string import Template

import datetime
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
            logging.StreamHandler(), 
            # logging.FileHandler(f"InstructionsParse{'{0:%Y-%m-%d %H_%M_%S}'.format(datetime.datetime.now())}.log")
        ]
)

#for name, value in os.environ.items():
 #  print("{0}: {1}".format(name, value))
"""
API_KEY = os.environ['API_KEY']
SEARCH_ENGINE_ID = os.environ['SEARCH_ENGINE_ID']
"""
CATEGORIES = ['EDUCATION',
 'ENTERTAINMENT',
 'COMMUNICATION',
 'FOOD_AND_DRINK',
 'LIFESTYLE',
 'MAPS_AND_NAVIGATION',
 'MUSIC_AND_AUDIO',
 'NEWS_AND_MAGAZINES',
 'SHOPPING',
 'PRODUCTIVITY',
 'TOOLS',
 'TRAVEL_AND_LOCAL',
 'WEATHER',
 'SOCIAL',
 'SYSTEM']
CATEGORY_TO_SEARCHQUERY = {
}
   
# see: currently we filter video and some documents like pdf, docx, but it's easy to add them from the engineer perspective
CATEGORY_TO_SEARCHQUERY['SYSTEM'] = Template('how to ${goal} step by step on ${device}')
CATEGORY_TO_SEARCHQUERY['EDUCATION'] = Template('${goal}')

def extract_wikihow(url, content):
  #print("in wikihow")
  domain = url.split('://')[1].split('/')[0]
  soup = BeautifulSoup(content, 'html.parser')
  title = soup.head.title.text.replace(' - wikiHow', '')
  if "- how to articles from" in str(title):
      return []
  #print(soup.find('div', {'id':'method_toc'}))
  #print(soup.find_all(True, {'class':['whb']}))
  #print(soup.find_all('div', {'class':'method_label'}))
  switch = soup.find_all('div', {'class':'method_label'}) == [] 
  steps = []
  output = []
  
  if switch:
    #process nonmethod pages 
    headlines = soup.body.find_all('span', class_='mw-headline')
    #print(headlines)
    end_step = soup.find('span', id='qa_headline')
    for item in headlines: 
      if item == end_step:
          break 
      if (item.text != 'Steps'):
        steps.append(item.text.replace("\\n", ""))
      #print(item.get_text())
    output.append([title.replace("\\n", ""), steps])
    
  else: 
      # process method pages 
      # need to figure out: combine methods and steps correctly. Currently have both, but seperate from each other. 
      # methods = method section titles 
      
      curr_steps = [] 
      full = soup.body.find_all(True, {'class':['mw-headline', 'whb']})
      end_step = soup.find('span', id='qa_headline')
      curr_goal = end_step 
      
      for item in full: 
          #print(item.get('class'))
          #print(item.text)
          if item.text != 'Steps':
            if item == end_step: 
                break 
            elif item.get('class') == ['mw-headline']: 
                if curr_goal != end_step: 
                  output.append([curr_goal.text.replace("\\n", ""), curr_steps])
                  #print(output)
                curr_goal = item 
                curr_steps = []
                
            else: 
                #print(soup.index(item))
                curr_steps.append(item.text.replace("\\n", ""))

      # same as nonmethod, contains the steps as raw html 
  indexes = []
  for item in output: 
    for step in item[1]: 
      start = soup.text.index(step)
      indexes.append((start, start + len(step)))
    item.append(indexes)
    indexes = []





  return output

class ReturnPage(dict):
    def __init__(self, search_item, start, i):
        # rank of the page
        self.rank = i + start - 1
        # get the page title
        self.title = search_item.get("title")
        # page snippet
        self.snippet = search_item.get("snippet")
        # alternatively, you can get the HTML snippet (bolded keywords)
        self.html_snippet = search_item.get("htmlSnippet")
        # extract the page url
        self.link = search_item.get("link")
        # instructions
        self.instructions = None
        # long description
        try:
            self.long_description = search_item["pagemap"]["metatags"][0]["og:description"]
        except KeyError:
            self.long_description = "N/A"
        
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def retrieveInstructions(self):
        try:
            # s = HTMLSession()
            # response = s.get(self.link)
            # # see: load dynamic pages
            # response.html.render(sleep=2, timeout = 20)
            response = requests.get(self.link)
            self.instructions = process_html(self.link, response.content)
        except Exception as e:
            logger.error(f"Error when retrieving instructions from {self.link}: {e}")
            self.instructions = []

    def __str__(self) -> str:
       return json.dumps({
          "rank": self.rank,
          "title": self.title,
          "link": self.link,
          "instructions": self.instructions, 
          "need_correction": len(self.instructions) == 0
       })
    
    def __json__(self):
       return self.__str__()

def process_html(url, content):
  """Processes single html webpage and extracts instructions as tasks."""
  def process_tag(soup, tag, returnme):
    """Processes single tag and extracts instructions as tasks."""
    ols = soup.find_all(tag)
    for _, ol in enumerate(ols):

      if domain == 'support.google.com':
        for s in ol.find_all('img'):
          # In Google support web, the 'alt' text are duplicated with text ahead
          # But the arrow image should be replaced with its alt, see both example:
          # https://support.google.com/pixelphone/answer/7444033
          if s['alt'].lower().strip() == 'and then':
            s.replace_with('and then')
      else:
        for s in ol.find_all('img'):
          s.replace_with(s['alt'])

      if domain in ['steps.app', 'www.techbone.net']:
        # This website has no separater between steps, if call get_text(), the
        # words between steps will mess up.
        instruction_got = ol.get_text('. ', strip=True)
      else:
        # Replace any HTML tag with a space, especially between steps of instruction
        # See https://www.crummy.com/software/BeautifulSoup/bs4/doc/#get-text
        instruction_got = ol.get_text(' ', strip=True)

      processed_str = _replace_unicode_with_space(instruction_got)
      # Decide whether the instruction is Android-related by URL/instruction.
      # Sometimes instruction does not contain "android" but it's indeed valid, so
      # add url as part of the text.
      if _is_valid(url.split('?')[0], processed_str):
        returnme.append(processed_str)

  # function for extracting plan from wikihow html 
  # two modes: method and nonmethod 
  # nonmethod returns: ("plan", "steps")
  # plan = article title, steps = steps section 
  # method returns [("plan", "steps"), ..., ("plan", "steps")]
  # where plan in the method name and steps are the steps for that method
  


    


  returnme = []

  domain = url.split('://')[1].split('/')[0]
  soup = BeautifulSoup(content, 'html.parser')

  # Remove unnecessary tags which could exist in <ol>
  for s in soup.select('script'):
    s.extract()
  for s in soup.select('noscript'):
    s.extract()
  for s in soup.select('table'):
    s.extract()
  for s in soup.select('figure'):
    s.extract()

  if domain == 'www.lifewire.com':
    for s in soup.find_all('div', {'class': 'theme-experttiptip'}):
      s.extract()
    for s in soup.find_all('div', {'class': 'theme-experttipimportant'}):
      s.extract()

  # For specific websites, need fine tune the parser to remove (.extract()) some
  # unnecessary tags to clean up the result got from ol.get_text()


  if domain == 'www.wikihow.com':
    for s in soup.select('span'):
      s.extract()
    #print(output)
  
  process_tag(soup, 'ol', returnme)
  process_tag(soup, 'ul', returnme)

  return returnme

def _is_valid(url, inst):
  url_words = re.compile(r'\w+').findall(url.lower())
  instruction_words = re.compile(r'\w+').findall(inst.lower())

  phone_set = {'android', 'phone', 'pixel', 'nexus', 'galaxy', 'samsung', 'lg',}
  click_set = {'tap', 'click', 'press', 'touch', 'select', 'choose', 'pick', 'open'}

  return (set(url_words + instruction_words).intersection(phone_set) and
          set(instruction_words).intersection(click_set))

def _replace_unicode_with_space(text):
  """Replaces all unwanted unicode chars with single space."""
  returnme = ''.join([i if ord(i) < 128 else ' ' for i in text])
  returnme = ' '.join(returnme.split())  # Change all space/newline to one space
  return returnme

def retrieveStepForGoal(args) -> List[ReturnPage]:
    if  args.category not in CATEGORY_TO_SEARCHQUERY:
        raise ValueError(f"{args.category} should be one of {CATEGORY_TO_SEARCHQUERY}")
    goal, num, device, app, threshold = args.goal, args.number, args.device, args.app, args.threshold
    page = 0
    invalid = 0
    query = CATEGORY_TO_SEARCHQUERY[args.category].substitute(goal=goal, device=device, app=app)
    curr_visited = {}
    result = []
    while len(result) - invalid < num and len(result) < threshold:
        page += 1; start = (page - 1) * num + 1
        url = f"https://customsearch.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={query}&start={start}&num={num}"
        data = requests.get(url).json()
        search_items = data.get("items")
        if search_items is not None:
            for i, search_item in enumerate(search_items):
                r = ReturnPage(search_item, start, i)
                if r.link not in curr_visited:
                    # see: handle with documents
                    if r.link.endswith(".pdf") \
                        or r.link.endswith(".excel") \
                        or r.link.endswith(".docx") \
                        or r.link.startswith("https://www.youtube.com/"):
                        continue
                    curr_visited[r.link] = r
                    r.retrieveInstructions()
                    result.append(r)
                    if len(r.instructions) == 0:
                      invalid += 1
                    if len(result) - invalid == num or len(result) == threshold:
                      break
    return result

def config():
    argument = argparse.ArgumentParser()
    argument.add_argument('--number', default=10)
    argument.add_argument('--threshold', default=30)
    argument.add_argument('--category', default='EDUCATION')
    # argument.add_argument('--goal', default='How do I activate subtitles for videos on TED.com or the TED app?')
    argument.add_argument('--goal', default='How to setup an account in Netflix?')
    # argument.add_argument('--device', default='Pixel 6')
    argument.add_argument('--device', default='Android')
    argument.add_argument('--app', default='Entertainment app')
    args = argument.parse_args()
    return args

if __name__ == "__main__":
    args = config()
    result = retrieveStepForGoal(args)
    with open(f"result_{CATEGORY_TO_SEARCHQUERY[args.category].substitute(goal=args.goal, device=args.device, app=args.app)}.json", "w") as f:
        json.dump(result, f, indent=4)