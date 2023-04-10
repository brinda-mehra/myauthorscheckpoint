import requests
import json 
import webbrowser
import networkx as nx 
from bs4 import BeautifulSoup, Tag
import unidecode
import matplotlib.pyplot as plt


def getAuthorURL(input): 
    japanese_name = input
    ascii_name = unidecode.unidecode(japanese_name)
    search_input = ascii_name.replace(" ", "+")
    searchURL = 'https://www.goodreads.com/search?q=' + search_input
    response = requests.get(searchURL)
    content = response.content.decode('utf-8')
    soup = BeautifulSoup(content, "html.parser")
    author_div = soup.find_all("div",{"class": 'authorName__container'} )
    author_url_clean = [y for x in author_div for y in x.children if isinstance(y, Tag )]
    author_url_list = [[x.contents[0], x.get("href")] for x in author_url_clean]
    author_span = [[x[0].contents[0], x[1]] for x in author_url_list if isinstance(x[0], Tag)]
    auth_span = [[unidecode.unidecode(x[0]), x[1]] for x in author_span]
    authorList = [x for x in auth_span if ascii_name in x[0]]
    if len(authorList) == 0:
        print("Sorry, GoodReads did not find this author. Check the spelling or try another author")
        return None
    author_url = authorList[0]
    url_only = author_url[1]
    return authorList[0]


def getInfluences(url): 
    print(url)
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    influences_section = soup.find_all("div",string="Influences")
    if len(influences_section) == 0:
       print("Sorry, GoodReads has no influences for this author on record! Try another one")
       return []
    influences_text = influences_section[0].find_next_sibling("div")
    influences_span = influences_text.find_all("span")[-1]
    authorList = influences_span.find_all("a")
    authorNames = [{'name': x["title"], 'url': x["href"]} for x in authorList]
    return authorNames

def getAuthorDetails(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    website_section = soup.find_all("div", string="Website")
    if website_section:
        website_div = website_section[0].find_next_sibling("div")
        website = website_div.find_all("a")
        web = website[0]["href"]
    else:
        print("This author doesn't have a personal website listed on Goodreads :(")
        web = None
    genre_section = soup.find_all("div", string="Genre")
    genres = []
    if genre_section: 
        genre_div = genre_section[0].find_next_sibling("div")
        genre_list = genre_div.find_all("a")
        for genre in genre_list: 
            genres.append(genre.text)
    else: 
        print("No genres on record for this author")
    authordetails = {"website": web, "genres":genres}
    return authordetails




# Building the Author-Influence Universe



class Universe:
    authordetailsmap = {}

    def __init__(self) -> None:
        self.createemptygraph()
        self.authordetailsmap = {}
    
    def createemptygraph(self): 
        self.graph = nx.DiGraph()

    def addauth(self, search_string):
        if search_string in self.authordetailsmap.keys():
            details = self.authordetailsmap[search_string]
            auth = [search_string, details["url"]]
        else:
            auth = getAuthorURL(search_string)
        if auth is None: 
            return 
        self.addurl(auth[0], auth[1])
        details = getAuthorDetails(auth[1])
        self.addauthordetails(auth[0], details)
        influence = getInfluences(auth[1])
        self.addmultiurldict(influence)
        self.addtoauthdetails(auth[0],influence)
        self.authtograph(auth, influence)
        return auth[0]
    
    def addtoauthdetails(self, name, influence):
        self.authordetailsmap[name]["influence"] = [x["name"] for x in influence]


    def addauthordetails(self, name, details):
        if not name in self.authordetailsmap.keys():
            self.authordetailsmap[name] = {}
        self.authordetailsmap[name]["website"] = details["website"]
        self.authordetailsmap[name]["genres"] = details["genres"]


    def addurl(self, name, url): 
        if not name in self.authordetailsmap.keys():
            self.authordetailsmap[name] = {}
        self.authordetailsmap[name]['url'] = url

    def addmultiurl(self, urlmap): 
        for k in urlmap:
            if not k[0] in self.authordetailsmap.keys():
                self.authordetailsmap[k[0]] = {}
            self.authordetailsmap[k[0]]["url"] = k[1]

    def addmultiurldict(self, influencemap):
        for item in influencemap:
            if not item["name"] in self.authordetailsmap.keys():
                self.authordetailsmap[item["name"]] = {}
            self.authordetailsmap[item["name"]]["url"] = item["url"]

    def creategraph(self, influencemaps):
        for k,v in influencemaps.items(): 
            self.addmultiurldict(v)
            self.graph.add_node(k)
            for influence in v: 
                self.graph.add_node(influence["name"])
                self.graph.add_edge(k, influence["name"])
        return self.graph
    
    def authtograph(self, auth, influencemap):
        self.graph.add_node(auth[0])
        for influence in influencemap: 
            self.graph.add_node(influence["name"])
            self.graph.add_edge(auth[0], influence["name"])

    @staticmethod
    def createuniverse(authorlist):
      authorurllist = [getAuthorURL(x) for x in authorlist]
      U = Universe()
      U.addmultiurl(authorurllist)
      influencemaps = {k: getInfluences(v) for k,v in authorurllist.items()}
      U.creategraph(influencemaps)
      return U
    
    def draw_graph(self):
        nx.draw(self.graph, with_labels=True)
        plt.show()

    def write_to_disk(self):
       with open('myauthors.json',"w") as fw:
            jsonstring = json.dump(self.authordetailsmap, fw, indent=4)
            print(jsonstring)

    def read_from_disk(self):
        with open('myauthors.json',"r") as fw:
            self.authordetailsmap = json.load(fw)
            print(self.authordetailsmap)




class SearchAuth:
    def __init__(self) -> None:
        self.Universe = Universe()
        self.last_search = ""

    def search_query(self): 
        search_string = "Enter a new author name or type 'preview' to see previous searches: "
        searching = input(search_string)
        if searching != "preview": 
            self.last_search = self.Universe.addauth(searching)
            return None
        if searching == 'exit':
            return None
        search_string2 = ("Enter 1 to see a network of all your author searches and their influences, "
                  "2 to see the main genres your last search writes for,"
                  "3 to open your last search's personal website, "
                  "4 to open the Amazon page for their books,"
                  "and 5 to save information about all your searched authors to the cache: ")
        outputnum = input(search_string2)
        if outputnum.isnumeric():
            outputnum = int(outputnum)
            if outputnum == 1:
                self.Universe.draw_graph()
            if outputnum == 2: 
               print(self.last_search)
               print("Genres:", self.Universe.authordetailsmap[self.last_search]["genres"])
            if outputnum == 3: 
                print("Website:", self.Universe.authordetailsmap[self.last_search]["website"])
            if outputnum == 4:
                self.openAmazon(self.last_search)
            if outputnum == 5:
                self.Universe.write_to_disk()
    
    def openAmazon(self, author_name):
        amazon_url = f"https://www.amazon.com/s?k={author_name}"
        webbrowser.open_new_tab(amazon_url)



if __name__ == "__main__":
    search = SearchAuth()
    while True: 
        output = search.search_query()
        print(output)

