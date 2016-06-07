# -*- coding: utf-8 -*-
"""

@author: Steven Lin, Xiang Li

# References
http://www.crummy.com/software/BeautifulSoup/bs3/documentation.html
http://www.crummy.com/software/BeautifulSoup/bs4/doc/
http://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text
http://rufuspollock.org/2006/09/25/unicode-to-ascii-mappings-for-standard-characters-from-wordprocessed-documents/
http://nlp.stanford.edu/software/corenlp.shtml
"""

from bs4 import BeautifulSoup
import re
from urllib2 import urlopen #python 2
import time
from __future__ import division # division results in float if both integers
import os
import json
import pandas
import copy
import numpy as np
from stanford_corenlp_pywrapper import CoreNLP
from nltk.corpus import stopwords
import nltk
from scipy.spatial.distance import cosine
import math
from sklearn.metrics import pairwise_distances
import sys
import numpy as np

path = ''
in_file_name = 'inside_out.html'
out_file_name = 'inside_out.csv'
os.chdir(path)
os.listdir('.') # see if file is in directory

#%% Function replace utf-8 “ and ’ character to ascii equivalent " and '

def processString(unicodeS):
    """ Convert ’ to ' and remove “, strip leading and trailing whitespace
    
    Args:
        unicdeS
    
    Returns:
        str: in ascii
        
    """
    out = unicodeS.replace( u'\u2018', u"'")
    out = out.replace( u'\u2019', u"'")
    out = out.replace( u'\u201c', '')
    out = out.replace( u'\u201d', '')
    out = out.replace('"','')
    return out.encode('ascii').strip()
    

#%% Data processing by div tag ###############################################

#url = 'http://webcache.googleusercontent.com/search?q=cache:zmFBXLVh38EJ:gointothestory.blcklst.com/wp-content/uploads/2015/11/Inside-Out.pdf+&cd=1&hl=en&ct=clnk&gl=us'
#html = urlopen(url)
bsObj = BeautifulSoup(open(in_file_name))

all_tags = bsObj.findAll("div")
len(all_tags) # 4817

# tag1: header, tag2: header, tag3: tags objects combined since there is not a closing "div" tag
# either use tag3:
len(all_tags[2].findAll("div")) # 4814

# or tag4 onwwards
len(all_tags[3:]) # 4814

all_tags = all_tags[3:]

# also ignore cover tags (e.g. Authors, phone number, etc)
all_tags = all_tags[10:]

# divs to ignore: 
#   2 divs in cover page
#   2 divs in header: INSIDE OUT, and page number
#   1 div for Page Number

# page number div tags have tag <b> and also attribute style with left:0
print(all_tags[0].prettify())
len([tag for tag in all_tags if tag.b !=None]) # 129 pages (excluding cover)

# headers have atttribute style with left:108 or left:810
print(all_tags[65].prettify())
print(all_tags[66].prettify())
pattern_head = re.compile(r'left:108|left:810')
len([tag for tag in all_tags if pattern_head.search(tag["style"])!=None]) #256, or 128 each (since second page has no header info)

# remove these div tags
margin_ignore = [0, 108, 810]
pattern_ignore = re.compile(r"{}".format("|".join(["left:" + str(i) for i in margin_ignore])))

tags1 = [tag for tag in all_tags if pattern_ignore.search(tag["style"]) == None]
len(tags1) #4419


# Alternative: process by span tag (page) #####################################
# tag span: attribute style="font-size:19px" is the header of page
# 130 pages, but first 2 pages don't have header (128 headers)
# finds all the page headers
ps = bsObj.findAll("span",style=re.compile('font-size:19px'))
len(ps) # 128

# get pages (represented by span tag), by ignoring span tags headers
pattern = re.compile('font-size:19px')
pages = bsObj.findAll("span", style=lambda tag: pattern.search(tag)==None)

# ignore cover
pages = pages[1:]
len(pages) #129

# do some testing
pages[0].attrs
pages[0].name
pages[0].div
pages[0]["style"]
pages[0].text
pages[0].findAll("nobr")
pages[0].contents # direct children
# generators
for x in pages[0].children:
    print x
for x in pages[0].descendants:
    print x
for x in pages[0].children:
    print x.string
for x in pages[0].strings:
    print x
for x in pages[0].stripped_strings :
    print x
pages[0].parent
print(pages[0].prettify())

# count number of divs
tags = [tag for page in pages for tag in page.findAll("div")]
len(tags) #4419 # this number matches data processing by div in previous section

tags2 = copy.copy(tags)


#%% Find Structure #############################################################

# get left margin
margins = [tag["style"].split(";")[2] for tag in tags]

series = pandas.Series(margins)
c = series.value_counts()
print(c) 

# left:270    1874
# left:162    1302
# left:378    1063
# left:309     131
# left:500      14
# left:324       6
# left:857       6
# left:302       4
# left:633       3
# left:618       3
# left:281       2
# left:291       2
# left:639       2
# left:693       2
# left:222       1
# left:641       1
# left:296       1
# left:629       1
# left:608       1


def removeTag(margin, tags):
    """ Given a margin for left, prints sample tags matching and returns tags
    with these margins removed
    
    Args:
        margin (int): margin left
        tags: list of div tag objects
    
    Returns:
        (list): of div tag object
    
    """
    tagsX = [tag for tag in tags if re.search("left:{}".format(margin), tag["style"])]
    print("Number of tags matching: " + str(len(tagsX)))
    print("Sample matching tags: ")
    print(tagsX[0:min(len(tagsX), 10)])
    
    margin_ignore2 = [margin]
    pattern_ignore2 = re.compile(r"{}".format("|".join(["left:" + str(i) for i in margin_ignore2])))
    tags2 = [tag for tag in tags if pattern_ignore2.search(tag["style"]) == None]
    
    return tags2
    
# Left:270 --> quotes
tags2 = removeTag(270,tags2)
# Left:162 --> scene location (uppercase) and description
# Note: some of the tags 162 (description and location) are quotes when
# multiple people speak at the same time
tags2 = removeTag(162,tags2)
# Left:378 --> character name
tags2 = removeTag(378,tags2)
# Left:309 --> description of quotes (in parenthesis) and also inside description during quote
tags2 = removeTag(309,tags2)
# Left:500 --> quotes, this occurs when multiple characters say around the same time
tags2 = removeTag(500,tags2)
# Left:324 --> description during a quote
tags2 = removeTag(324,tags2)
# Left:857 --> asterisk on the right margin
tags2 = removeTag(857,tags2)
# Left:302 --> character, when multiple characters say around the same time
tags2 = removeTag(302,tags2)
# Left:633 --> character, when multiple characters say around the same time
tags2 = removeTag(633,tags2)
# Left:618 --> character, when multiple characters say around the same time
tags2 = removeTag(618,tags2)
# Left:281 --> character, when multiple characters say around the same time
tags2 = removeTag(281,tags2)
# Left:291 --> character, when multiple characters say around the same time
tags2 = removeTag(291,tags2)
# Left:639 --> character, when multiple characters say around the same time
tags2 = removeTag(639,tags2)
# Left:693 --> CUT TO:
tags2 = removeTag(693,tags2)
# Left:222 --> character, when multiple characters say around the same time
tags2 = removeTag(222,tags2)
# Left:641 --> dissolve to:
tags2 = removeTag(641,tags2)
# Left:296 --> character, when multiple characters say around the same time
tags2 = removeTag(296,tags2)
# Left:629 --> character, when multiple characters say around the same time
tags2 = removeTag(629,tags2)
# Left:608 --> character, when multiple characters say around the same time
tags2 = removeTag(608,tags2)
    
# quote: 270, 500 (when multiple speakers), 162 (when multiple speakers)
# scene location: 162 (UPPER CASE)
# scene description: 162 (not all upper case)
# description quote: 309, 324 (second level)
# character: 378, multiple spearkers: 222, 281, 291,296, 302, 608, 618, 629, 633, 639
    
character_margins =[378, 222, 281, 291,296, 302, 608, 618, 629, 633, 639]

# "position:absolute;top:1470;left:162"   
# check that style contains 3 elements and the last one is left 
for tag in tags:
    if len(tag["style"].split(";")) !=3:
        print(tag)
    elif tag["style"].split(";")[-1].split(":")[0] != "left":
        print(tag)
        
pattern_margin = re.compile(r'[0-9]+$')

def getMargin(tag, pattern_margin):
    """ Returns the left margin number of a tag
    
    Args:
        tag: tag with style attribute
        
    Returns
        int: margin number
    """
    return int(pattern_margin.findall(tag["style"])[0])
      

# ignore left:693 (CUT TO) and left:857 (asterisk) and left: 641: DISSOLVE TO
tags = [tag for tag in tags if getMargin(tag, pattern_margin) not in (693, 857, 641)]

#%% Look at attribue top margin ###############################################
# get the differces in the top margin (vertical spacing) for pair of tags transitions

pattern_margin = re.compile(r'[0-9]+$')

def getMarginTop(tag, pattern_margin):
    """ Returns the top margin number of a tag
    
    Args:
        tag: tag with style attribute
        
    Returns
        int: margin number
    """
    return int(pattern_margin.findall(tag["style"].split(";")[1])[0])
        

marginTop = [getMarginTop(tag, pattern_margin) for tag in tags ]
differences = [t-s for (s, t) in zip(marginTop, marginTop[1:])]
marginLeft = [getMargin(tag, pattern_margin) for tag in tags]
tagsTransition = [str(t) + "->" + str(s) for (s, t) in zip(marginLeft, marginLeft[1:])]

tagDiff = zip(tagsTransition, differences)
tagDiff[0:20]

dftagsDiff = pandas.DataFrame({"tags": tagsTransition,"diff": differences}, columns = ["tags", "diff"])
dftagsDiff.groupby(["tags", "diff"]).size() # some are negating, indicating out of place tags

#%% Create Dataset #############################################################

data_raw = []    
count = 0
location = ""
description = ""
character = ""
quote = ""
current = ""

i=0
while i < len(tags) and tags[i].text != "THE END.":
    margin = getMargin(tags[i],pattern_margin)

    # location
    if margin == 162 and tags[i].text.isupper():
        
        if tags[i].text == "ON THE CONSCIOUSNESS SCREEN:":
            location = tags[i-1].text
            if re.search(r"CONTINUOUS$", location):
                location = re.sub(r" - CONTINUOUS$", "", location)
                  
        elif re.search(r"CONTINUOUS$", tags[i].text):
            #location = tags[i].text.split("-")[0].strip()
            location = re.sub(r" - CONTINUOUS$", "", tags[i].text)
            
        elif tags[i].text == "BEEP!":
            location = "INT. HEADQUARTERS"
            
        else:
            location = tags[i].text
            
        i+=1

    
    # description
    elif margin == 162:
        
        description = ""
        while margin == 162 and not tags[i].text.isupper() and i<len(tags):
            description += " " + tags[i].text
            i+=1
            margin = getMargin(tags[i],pattern_margin)
        
    # character
    elif margin in character_margins:
    #elif margin == 378:
        character = tags[i].text
        if tags[i+1].text[0] == "/":
            i+=1
            character = character + " " + tags[i].text
        
        # quote
        i+=1
        margin = getMargin(tags[i],pattern_margin)
        quote = ""
        while (margin in [270, 309, 324, 500] or 
        (margin == 162 and getMarginTop(tags[i],pattern_margin)-getMarginTop(tags[i-1],pattern_margin) == 18)) and i<len(tags)  :
                   
            quote += " " + tags[i].text
            i+=1
            margin = getMargin(tags[i],pattern_margin)
            
            if tags[i].text == "(MORE)":
                i+=1
                margin = getMargin(tags[i],pattern_margin)
            
        
        # remove (CONT'D) (O.S) (V.O) from character name        
        clean_character = re.sub(r'\(.*','',character).strip()
        
        data_raw.append({"location": processString(location),
                        "description": processString(description),
                        "character": processString(clean_character),
                        "quote": processString(quote)})
        
    else:
        i+=1
        
x = pandas.DataFrame(data_raw, columns = ["location", "description", "character", "quote"])
# x.to_csv(out_file_name, sep=",", header=True, index=True, encoding = 'utf-8')
         
#%% Clean Dataset #############################################################
         
# check character names         
pandas.Series(x["character"]).value_counts()         
characters = np.sort(pandas.unique(x["character"]))
for i in characters :
    print(i)
    
# find all characters
# table = bsObj.findAll("div", style=re.compile('left:378'))

# Some of the tags are our of place (e.g. top:XXX, when have (CONT'D) in character
# as a result of new page). This will usually show blank in quotes.
   
# names separted by / --> split in different row with same quote, location, etc

data_clean = []

index = 0
for row in data_raw:
    if row["quote"] != "":
        
        character_names = [ch.strip() for ch in row["character"].split("/")]
        
        for ch in character_names:
            character = ch
            data_clean.append({ "time": index,
                                "location": row["location"],
                                "description": row["description"],
                                "character": ch,
                                "quote": row["quote"]})
            index+=1
        
                
df_data_clean = pandas.DataFrame(data_clean, columns = ["time","character", "quote", "location", "description"])            
df_data_clean.to_csv("data_clean.csv", sep=",", header=True, index=False, encoding = 'utf-8')
      
with open('data_clean.json', 'w') as fp:
    json.dump(data_clean, fp, indent=2, encoding = 'utf-8')
    
#%% Replace Character Name and Standardize Locations  #######################
    
# chracter counts
df_data_clean["character"].value_counts()

# locations 
df_data_clean["location"].value_counts().sort_index()

# change locations
# Standardize locations if contain
location_standard = ['TRAIN STATION','TRAIN CAR', 'SUBCONSCIOUS STAIRS',
                     'SUBCONSCIOUS GATE','SUBCONSCIOUS CAVE', 'STAGE B',
                     'SHCOOL', 'SAN FRANCISCO STREET', 'SAN FRANCISCO HOUSE',
                     "MOM'S HEADQUARTERS", 'MINNESOTA LAKE','MINNESOTA HOUSE',
                     'MINNESOTA HOSPITAL', 'MIND WORLD', 'MEMORY DUMP',
                     'LONG-TERM MEMORY', 'IMAGINATIONLAND', 'HOSPITAL', 
                     'HOCKEY RINK', 'HEADQUARTERS', 'GOOFBALL ISLAND',
                     'DREAM PRODUCTIONS', 'DO NOT ENTER WHEN LIGHT FLASHING.',
                     "DAD'S HEADQUARTERS",'CLASSROOM','BUS','ABSTRACT THOUGHT BUILDING']

# dictionary based on San Francisco or Minnesota to handle cases like "KITCHEN"
location_standard_dic_sf = {k:v for (k,v) in zip(location_standard,location_standard)} 
location_standard_dic_mn = {k:v for (k,v) in zip(location_standard,location_standard)} 

house_locations = ("LIVING ROOM", "DINING ROOM","BEDROOM", "KITCHEN", "BATHROOM", "RILEY'S ROOM")

for house in house_locations:
    location_standard_dic_sf[house] = 'SAN FRANCISCO HOUSE'
    location_standard_dic_mn[house] = 'MINNESOTA HOUSE'     

def standardizeLocation(s, dic):    
    """ Standardize Locations
    
    Args:
        s: string to standardie
        dic: dictionary key= pattern, value = to replace with
    Returns:
        string: standardized string or not match original string

    """        
    for loc in dic:
        if re.search(r'{}'.format(loc),s):
            return dic[loc]
    return s
    

# e.g. JOY will say SADNESS a lot, which is a negative sentiment
# Also NER will not be able to regonize Sadness as a person

# Mapping
# Joy --> Joyce
# Sadness --> Sandra
# Anger -->Angelo
# Fear --> Felipe
# Disgust --> Diane


emotion_to_person = {"Joy": "Joyce", "Sadness": "Sandra", "Anger": "Angelo",
                     "Fear": "Felipe", "Disgust": "Diane"}
                     
                     
person_to_emotion = {v: k for k,v in emotion_to_person.items()}


def convertEmotionToPerson(s, emotion_to_person):
    """ Convert the emotion to a person name
    
    Args:
        s (string): string to convert
        emotion_to_person (dic): mapping emotion to name
    
    Returns:
        string: with replaced emotions with names
    
    """
    
    for (emotion,person) in emotion_to_person.items():

        s = re.sub(r"{upper}|{regular}".format(upper = emotion.upper(),
                                               regular = emotion),person, s)
                   
    return s
        
data_names = copy.deepcopy(data_clean) # deep copy otherwise change data_clean since list of objects
for row in data_names:
    
    # in minnesota
    if row["time"] < 65:    
        row["location"] =standardizeLocation(row["location"], location_standard_dic_mn)
    
    # in san francisco
    else:
        row["location"] =standardizeLocation(row["location"], location_standard_dic_sf)
        
    for field in ("character","quote","description"):
        row[field] = convertEmotionToPerson(row[field], emotion_to_person)

print(data_names[0])
print(data_clean[0])

df_data_names = pandas.DataFrame(data_names, columns = ["time","character", "quote", "location", "description"])            
df_data_names.to_csv("data_names.csv", sep=",", header=True, index=False, encoding = 'utf-8')
      
with open('data_names.json', 'w') as fp:
    json.dump(data_names, fp, indent=2, encoding = 'utf-8')
    
# chracter counts
df_data_names["character"].value_counts()

# location counts
df_data_names["location"].value_counts()



#%% Lemmatize ################################################################

# Note: Stanford NLP does not have stop word removal. So have to remove in python code using
# stopwords from nltk

# Note: Stanford NLP converts to lower cases regulars words (e.g does not 
# convert lower case I, China, etc). So need to add "I" to stopwords

# Note: Stanford NLP: parentheis are -rrb- and -lrb-

# stopwords list , add "I" since Stanford NLP does not lowercase I but stopwords
# from nltk includes "i"
stop = set(stopwords.words('english'))
stop.add("I")

# regex: only keep words composed of alphanumeric characters or alphanumeric or ! or ?
# words joined by "-" (e.g. keep data-driven)
# ignore parenthesis -rrb-, -lrb- so use match instead of search
# match: Determine if the RE matches at the beginning of the string.
pattern = re.compile(r'^(?:[A-Za-z0-9]+[- ][A-za-z0-9]+|[A-Za-z0-9]+|[?!]+)$')
#pattern_parenthesis = re.compile("-rrb-|-lrb-")


proc = CoreNLP("pos", corenlp_jars=["/Users/Documents/corenlp/stanford-corenlp-full-2015-04-20/*"])

# You can also specify the annotators directly. For example, say we want to 
# parse but don't want lemmas. This can be done with the configdict option:
# no longer need to specify output_types (the outputs to include are inferred from the annotators setting
p = CoreNLP(configdict={'annotators':'tokenize, ssplit, pos, parse, lemma, ner,entitymentions, dcoref'}, 
            #output_types=['pos','parse'],
            corenlp_jars=["/Users/Documents/corenlp/stanford-corenlp-full-2015-04-20/*"])
            
            
data_lemmas = copy.deepcopy(data_names) # deep copy otherwise change data_clean since list of objects

# lemmatize quotes and description
for row in data_lemmas:
    # Now it's ready to parse documents. You give it a string and it returns JSON-safe data structures
    # dictionary key = 'sentences', value = list of sentences
    # each sentence dictionary with key='lemmas', 'tokens', etc
    # key = 'lemmas', value = list of lemmas 
    
    for field in ("quote","description"):
        parsed = proc.parse_doc(row[field])["sentences"]
        sentences = [sentence["lemmas"] for sentence in parsed]
        
        # flatten nested list so each element is a token
        row_tokenized = [token.strip() for sentence in sentences for token in sentence
                         if token.strip() not in stop and pattern.match(token.strip())]
        row_string = " ".join(row_tokenized)
        row[field] = row_string
        #row[field] = row_tokenized           
        
print(data_names[0])
print(data_lemmas[0])

df_data_lemmas = pandas.DataFrame(data_lemmas, columns = ["time","character", "quote", "location", "description"])            
df_data_lemmas.to_csv("data_lemmas.csv", sep=",", header=True, index=False, encoding = 'utf-8')
      
with open('data_lemmas.json', 'w') as fp:
    json.dump(data_lemmas, fp, indent=2, encoding = 'utf-8')

#%% Bag of words ##############################################################

# combine quotes-description (because want to remove duplicates
# that were generated when people speak at the same time)

combine =  df_data_lemmas["quote"] + "@" + df_data_lemmas["description"]
len(combine)
combine_unique = list(set(combine)) #1073

# alternative
# remove duplicates columns quote and description, keep first (default: Drop duplicates except for the first occurrence)
df_data_lemmas_unique = copy.deepcopy(df_data_lemmas)
df_data_lemmas_unique.drop_duplicates(['quote','description'], inplace=True) # Whether to drop duplicates in place or to return a copy


quotes_token = df_data_lemmas_unique ["quote"].map(lambda x: x.split(" "))
quotes_token_flat = [token for q in quotes_token for token in q]

descriptions_nodup = df_data_lemmas_unique.drop_duplicates(['description'])["description"]
descriptions_token = descriptions_nodup .map(lambda x: x.split(" "))
descriptions_token_flat = [token for d in descriptions_token for token in d]

quotes_descriptions_token_flat = quotes_token_flat + descriptions_token_flat

# these are the inputs for the word cloud
with open('quotes_token.txt', 'w') as fp:
    for q in quotes_token_flat:
        fp.write(q+'\n')
        
with open('descriptions_token.txt', 'w') as fp:
    for d in descriptions_token_flat:
        fp.write(d+'\n')
        
with open('quotes_descriptions_quotes_token.txt', 'w') as fp:
    for d in quotes_descriptions_token_flat:
        fp.write(d+'\n')      

#%% Create base data #########################################################

# based on quotes or quotes+descriptions
# document = character
# document = index (aggregate)
# document = location

# remove punctuation except !
# keep uppercase


#%% Testing

fdist1 = nltk.FreqDist(" ".join(descriptions_token_flat))
fdist1.most_common(50)
fdist1["Joyce"]



# Reference for pandas dataframe
# iloc --> by row number/col number, loc --> by index 
# df_data_clean.iloc[0]
# df_data_clean.iloc[0:10]
# df_data_clean.iloc[0:10, 2] # rows 0 to 10, column 2
# df_data_clean["quote"].loc[0] # index 0 for column "quote"
# df_data_clean["quote"][0:10] # rows 0 to 10 for column "quote"

quotes = df_data_clean["quote"].loc[0] 

##############################################################################
#%% Document Similarity ######################################################

#%% Functions ###############################################################
    
def getCounts(doc):
    """ Gets the frequencies for elements in document
    
    args:
        doc (list) = list of tokens in document
    returns:
        pandas.core.series.Series: index = element, value = count
    """
    series = pandas.Series(doc)
    c = series.value_counts()
    return c
    
def getTermDocument(doc_dic_normalized):
    """ Term Document Dataframe, with column = document name, row = terms
    
    args:
        doc_dic_normalized (dic) = key: document name, value: list of terms
    returns:
        pandas.DataFrame with index = terms, column name = document name
    """    
       
    # key = document_name, value = pandas series counts
    counts = {name: getCounts(doc) for (name,doc) in doc_dic_normalized.items()}
    
    # Vocabulary = distinct words from all documents
    vocabulary = set([v for k in counts for v in counts[k].index])
    len(vocabulary) # 1769
    
    # for each class, fill missing values for words of that class that are not in the vocabulary
    # do this by creating a pandas series from the current count series using vocabulary
    # as index. The resulting series will include all the words in the vocabulary as index
    # with value equal to the count in the orignal series, except for words that are not
    # in the original series which will get a NaN value, which in turns gets filled with zero
    counts_fill = {k: pandas.Series(v, index = vocabulary).fillna(0, inplace=False) for k,v in counts.items()}
    
    # actually previous step not needed, can include vectors with different elements
    # in data frame, and any missing elements for other documents will have NaN values (fill with zeros)
    
    # column name = document name, row names = token
    # df = pandas.DataFrame(counts , index = vocabular).fillna(0, inplace = False) # no need to provide index
    df = pandas.DataFrame(counts).fillna(0, inplace = False)
    
    return df


def convertBoolean(term_document):
    """ Term Document Binarized (counts > 1 have value 1, else 0)
    
    args:
        term_document (pandas.DataFrame): with index = terms, column name = document name
    returns:
        pandas.DataFrame with index = terms, column name = document name
    """    
    
    term_document_boolean = term_document.copy(deep = True)
    term_document_boolean[term_document_boolean>1] = 1
    
    return term_document_boolean
 
def findMaxPairs(df):
    """ Returns the most similar document for each document
    
    args:
        df (pandas.Dataframe): row, col = documents, value = boolean similarity
    
    returns:
        pandas.Dataframe: most similar document for each document
    
    """
    df2 = df.copy(deep=True)
    np.fill_diagonal(df2.values, -1)
    return df2.idxmax()
    
def findMinPairs(df):
    
    """ Returns the least similar document for each document
    
    args:
        df (pandas.Dataframe): row, col = documents, value = boolean similarity
    
    returns:
        pandas.Dataframe: least similar document for each document
    
    """
    return df.idxmin() 
    
 
def rankSimilarity(df, top = True, rank = 3):
    
    """ Returns the most similar documents or least similar documents
    
    args:
        df (pandas.Dataframe): row, col = documents, value = boolean similarity
        top (boolean): True: most, False: least (default = True)
        rank (int): number of top or bottom (default = 3)
    
    returns:
        pandas.Dataframe: row =rank, columns = indices, names, value
    
    """
    df2 = df.copy(deep = True)
    df_np = df2.as_matrix()
    
    if top:
        np.fill_diagonal(df_np, -1)
    
    results_dic = {"indices": [], "names": [], "value": [] }
    
    for n in range(rank):
        
        if top:
            indices = np.unravel_index(df_np.argmax(), df_np.shape) # returns indices of first max found
            # np.where(df_np == df_np.max()) # will return all indices of maxs
        else:
            indices = np.unravel_index(df_np.argmin(), df_np.shape) # returns indices of first min found
            # np.where(df_np == df_np.min()) # will return all indices of mins
            
        results_dic["indices"].append(indices)
        results_dic["names"].append((df.index[indices[0]], df.index[indices[1]]))
        results_dic["value"].append(df.iloc[indices])
        
        if top:
            df_np[indices[0],indices[1]] = -1 # set to -1 to find the next max
            df_np[indices[1],indices[0]] = -1 # because symmetric
        
        else:
            df_np[indices[0],indices[1]] = 1 # set to 1 to find the next min
            df_np[indices[1],indices[0]] = 1 # because symmetric
        
    df_result = pandas.DataFrame(results_dic, index = range(1,rank+1))  
    df_result.index.name = "rank"   
    
    return df_result
        
#%% Analysis by document name = character, documents = quotes #################

freq_char = df_data_lemmas.groupby('character')['quote'].count().order(ascending = False)
print(freq_char)

# save results
freq_char.to_csv("freq_char.csv", sep=",", header=True, index=True)

# this converts to dataframe with column1 = character, column2 = list of quotes
df_data_lemmas.groupby('character')['quote'].apply(lambda x: x.tolist()).iloc[0]

# this convert dataframe with column1 = character, column2 = list of tokens 
# (concatenates quotes with space in between then split to token)
# need to remove the last element of list because extra space as a result of concatenation
quotes_by_char = df_data_lemmas.groupby('character')['quote'].apply(lambda x: (x + " ").sum().split(" ")[:-1])
quotes_by_char = quotes_by_char.map(lambda x: [token for token in x if token != '']) # remove "" tokens
type(quotes_by_char) # series

# key: document name (character), value = list of lemmas
doc_dic_normalized  = quotes_by_char.to_dict()

# key: name, value = index number
map_name_index = {name: index for (name,index) in zip(quotes_by_char.index, range(len(quotes_by_char.index)))}

# document-term matrix 
term_document = getTermDocument(doc_dic_normalized)
term_document.index 
term_document.columns
term_document.shape # (1289, 52)

term_document_boolean = convertBoolean(term_document) # term's raw frequency in this document

#%% Boolean Similarity ##########################################################

# Note that spatial.distance.cosine computes the distance, and not the similarity.
# So, you must subtract the value from 1 to get the similarity.
# Note also need to transpose because pairwise distances does it row by row
term_document_boolean_tp = term_document_boolean.transpose()
similarity_boolean = 1-pairwise_distances(term_document_boolean_tp, metric="cosine")
np.shape(similarity_boolean) # 30 by 30

df_similarity_boolean = pandas.DataFrame(similarity_boolean , index=term_document_boolean.columns, columns=term_document_boolean.columns)
document_name_check = df_similarity_boolean.index[0]
document_name_check2 = df_similarity_boolean.index[-1]
df_similarity_boolean[document_name_check][document_name_check] # 1
df_similarity_boolean[document_name_check][document_name_check2] # 0.1856

# save results
np.savetxt("boolean.txt", similarity_boolean , fmt='%.3f', delimiter = " ")
df_similarity_boolean.to_csv("boolean_w_headers.csv", sep=",", header=True, index=True, float_format= '%.3f')

max_pairs = findMaxPairs(df_similarity_boolean)
min_pairs = findMinPairs(df_similarity_boolean)
max_pairs
min_pairs

max_pairs[document_name_check] # 'bhargava_anuj'
min_pairs[document_name_check] # 'leboeuf_mark'

map_name_index[document_name_check] # 15
map_name_index[max_pairs[document_name_check]] # 2
map_name_index[min_pairs[document_name_check]] # 13
        
topSimilar = rankSimilarity(df_similarity_boolean, top = True, rank =10) 

bottomSimilar = rankSimilarity(df_similarity_boolean, top = False, rank =10)

# save results
topSimilar.to_csv("boolean_top.csv", sep=",", header=True, index=True)
bottomSimilar.to_csv("boolean_bottom.csv", sep=",", header=True, index=True)

# save output to output.txt
orig_stdout = sys.stdout
f = open('boolean_output.txt', 'w')
sys.stdout = f

print("\n********************************\n")
print("\n*Top****************************\n")

print(topSimilar)

print("\n*Bottom*************************\n")

print(bottomSimilar)

print("\n********************************\n")
print("Output files saved in: {}\n".format(os.getcwd()))
                                       
f.close()
sys.stdout =  orig_stdout       


print("\n********************************\n")
print("\n*Top****************************\n")

print(topSimilar)

print("\n*Bottom*************************\n")

print(bottomSimilar)

print("\n********************************\n")
print("Output files saved in: {}\n".format(os.getcwd()))

# ignore documents with very few values (e.g. characters with only 1 or 2 quotes)
# as these will tend to be the most dissimlar
# focus on characters with at least 20 quotes

freq_char[freq_char>20]
top_char = freq_char[freq_char>20].index

df_similarity_boolean_top = df_similarity_boolean.loc[top_char,top_char]

topSimilar = rankSimilarity(df_similarity_boolean_top, top = True, rank =10) 
bottomSimilar = rankSimilarity(df_similarity_boolean_top, top = False, rank =10)

# save results
topSimilar.to_csv("boolean_top2.csv", sep=",", header=True, index=True)
bottomSimilar.to_csv("boolean_bottom2.csv", sep=",", header=True, index=True)

# save output to output.txt
orig_stdout = sys.stdout
f = open('boolean_output2.txt', 'w')
sys.stdout = f

print("\n********************************\n")
print("\n*Top****************************\n")

print(topSimilar)

print("\n*Bottom*************************\n")

print(bottomSimilar)

print("\n********************************\n")
print("Output files saved in: {}\n".format(os.getcwd()))
                                       
f.close()
sys.stdout =  orig_stdout       


print("\n********************************\n")
print("\n*Top****************************\n")

print(topSimilar)

print("\n*Bottom*************************\n")

print(bottomSimilar)

print("\n********************************\n")
print("Output files saved in: {}\n".format(os.getcwd()))


#%% Manual calculations, less efficient #######################################
# check cosine formula
"""
x = term_document_boolean["lin_luis"]
y = term_document_boolean["li_xiang"]
sum(pandas.Series.multiply(x,y)) #20
np.dot(x, y) #20
sum(i*j for (i,j) in zip(x,y)) #20
math.sqrt(sum(i**2 for i in x)) # 12.6
math.sqrt(sum(i**2 for i in y)) # 8.54
sum(i*j for (i,j) in zip(x,y))/(math.sqrt(sum(i**2 for i in x))*math.sqrt(sum(i**2 for i in y)))
np.dot(x, y)/(np.linalg.norm(x)*np.linalg.norm(y))
1 - cosine(x,y)
"""

# do manually
"""
m = term_document_boolean.shape[1]
mat = np.zeros((m, m))
np_term_document_boolean = term_document_boolean.as_matrix()
np.shape(np_term_document_boolean)
for i in range(m):
    for j in range(i,m):
        if i != j:
            mat[i][j] = 1 - cosine(np_term_document_boolean[:,i], np_term_document_boolean[:,j])
            mat[j][i] = mat[i][j]
        else:
            mat[i][j] = 1
            
np.sum(mat-similarity_boolean) # basically zero
"""

#%% tf_idf ##################################################################

# term's raw frequency in this document
tf = 1+np.log10(term_document) # 1+log(tf) if tf > 0
tf = tf.replace([-np.inf],0)   # 0 otherwise

# the number of documents the term occurs in
# index = term, value = count documents
df = term_document_boolean.sum(axis=1)

# check
term_name_check = df.index[0]
sum(term_document_boolean.loc[term_name_check,:]) == df[term_name_check]

# N the total number of documents
N = term_document.shape[1]

idf = np.log10(N/df)
tf_idf = tf.multiply(idf,axis = 'index')

# check
document_name_check = tf_idf.columns[0]
sum(tf_idf[document_name_check]) == sum(tf[document_name_check]*idf)
tf_idf.loc[term_name_check,document_name_check ] == tf.loc[tf_idf.index[0],document_name_check ]*idf[term_name_check]

# Note that spatial.distance.cosine computes the distance, and not the similarity.
# So, you must subtract the value from 1 to get the similarity.
# Note also need to transpose because pairwise distances does it row by row
term_document_tfidf_tp = tf_idf.transpose()
similarity_tfidf = 1-pairwise_distances(term_document_tfidf_tp, metric="cosine")
np.shape(similarity_tfidf) # 30 by 30

document_name_check2 = tf_idf.columns[-1]
df_similarity_tfidf = pandas.DataFrame(similarity_tfidf , index=tf_idf.columns, columns=tf_idf.columns)
df_similarity_tfidf[document_name_check][document_name_check] # 1
df_similarity_tfidf[document_name_check][document_name_check2] # 0.048035582616980377

# save results
np.savetxt("tf_idf.txt", similarity_tfidf , fmt='%.3f', delimiter = " ")
df_similarity_tfidf.to_csv("tf_idf_w_headers.csv", sep=",", header=True, index=True, float_format= '%.3f')
            
max_pairs = findMaxPairs(df_similarity_tfidf)
min_pairs = findMinPairs(df_similarity_tfidf)
max_pairs
min_pairs

max_pairs[document_name_check] # 'bhargava_anuj'
min_pairs[document_name_check] # 'fassois_demetrios'

map_name_index[document_name_check] # 15
map_name_index[max_pairs[document_name_check]] # 2
map_name_index[min_pairs[document_name_check]] # 6
        
topSimilar = rankSimilarity(df_similarity_tfidf, top = True, rank =10) 

bottomSimilar = rankSimilarity(df_similarity_tfidf, top = False, rank =10)

# save results
topSimilar.to_csv("tf_idf_top.csv", sep=",", header=True, index=True)
bottomSimilar.to_csv("tf_idf_bottom.csv", sep=",", header=True, index=True)

# save output to output.txt
orig_stdout = sys.stdout
f = open('tf_idf_output.txt', 'w')
sys.stdout = f

print("\n********************************\n")
print("\n*Top****************************\n")

print(topSimilar)

print("\n*Bottom*************************\n")

print(bottomSimilar)

print("\n********************************\n")
print("Output files saved in: {}\n".format(os.getcwd()))
                                       
f.close()
sys.stdout =  orig_stdout       


print("\n********************************\n")
print("\n*Top****************************\n")

print(topSimilar)

print("\n*Bottom*************************\n")

print(bottomSimilar)

print("\n********************************\n")
print("Output files saved in: {}\n".format(os.getcwd()))

# ignore documents with very few values (e.g. characters with only 1 or 2 quotes)
# as these will tend to be the most dissimlar
# focus on characters with at least 20 quotes

freq_char[freq_char>20]
top_char = freq_char[freq_char>20].index

df_similarity_tfidf_top = df_similarity_tfidf.loc[top_char,top_char]

topSimilar = rankSimilarity(df_similarity_tfidf_top, top = True, rank =10) 
bottomSimilar = rankSimilarity(df_similarity_tfidf_top, top = False, rank =10)

# save results
topSimilar.to_csv("tf_idf_top2.csv", sep=",", header=True, index=True)
bottomSimilar.to_csv("tf_idf_bottom2.csv", sep=",", header=True, index=True)

# save output to output.txt
orig_stdout = sys.stdout
f = open('tf_idf_output2.txt', 'w')
sys.stdout = f

print("\n********************************\n")
print("\n*Top****************************\n")

print(topSimilar)

print("\n*Bottom*************************\n")

print(bottomSimilar)

print("\n********************************\n")
print("Output files saved in: {}\n".format(os.getcwd()))
                                       
f.close()
sys.stdout =  orig_stdout       


print("\n********************************\n")
print("\n*Top****************************\n")

print(topSimilar)

print("\n*Bottom*************************\n")

print(bottomSimilar)

print("\n********************************\n")
print("Output files saved in: {}\n".format(os.getcwd()))

#%% Manual calculations, less efficient #######################################
# check cosine formula
"""
x = term_document_boolean["lin_luis"]
y = term_document_boolean["li_xiang"]
sum(pandas.Series.multiply(x,y)) #20
np.dot(x, y) #20
sum(i*j for (i,j) in zip(x,y)) #20
math.sqrt(sum(i**2 for i in x)) # 12.6
math.sqrt(sum(i**2 for i in y)) # 8.54
sum(i*j for (i,j) in zip(x,y))/(math.sqrt(sum(i**2 for i in x))*math.sqrt(sum(i**2 for i in y)))
np.dot(x, y)/(np.linalg.norm(x)*np.linalg.norm(y))
1 - cosine(x,y)
"""

# do manually
"""
m = term_document_boolean.shape[1]
mat = np.zeros((m, m))
np_term_document_boolean = term_document_boolean.as_matrix()
np.shape(np_term_document_boolean)
for i in range(m):
    for j in range(i,m):
        if i != j:
            mat[i][j] = 1 - cosine(np_term_document_boolean[:,i], np_term_document_boolean[:,j])
            mat[j][i] = mat[i][j]
        else:
            mat[i][j] = 1
            
np.sum(mat-similarity_boolean) # basically zero
"""



