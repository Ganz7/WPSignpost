from lxml import html, etree
from datetime import datetime
from dateutil import parser
from mwapi import MWApi
import codecs
import requests
import urllib2
import re

START_YEAR = 2005
CUR_YEAR = datetime.now().year

api = MWApi('http://en.wikipedia.org')

def content_for_title(title):
    title = urllib2.unquote(title)
    text = api.get({'action': 'parse', 'page': title, 'redirects': '1', 'prop': 'text'})['parse']['text']['*']
    return text

def title_for_year(year):
    return 'Wikipedia:Wikipedia_Signpost/Archives/' + str(year)

def drop_child_elements(element, selectors):
    drop_tags = element.cssselect(', '.join(selectors))
    if len(drop_tags) != 0:
        for t in drop_tags:
            t.drop_tree()

DROP_ARCHIVE_SELECTORS = ['.hlist', '.signpost-article', 'table']
DROP_PAGE_SELECTORS = ['.floatright', 'center']

EXCLUDE_PAGE_TAGS = ['dl']

def parse_article(title):
    doc = html.document_fromstring(content_for_title(title))
    drop_child_elements(doc, DROP_PAGE_SELECTORS)
    # Author tag
    author_el = doc.cssselect("dd a[href*='User:']")
    author_el = author_el[0] if len(author_el) != 0 else None
    if author_el is not None:
        author_name, author_link = unicode(author_el.text), unicode(author_el.get('href'))
        author_el.drop_tree()
    else:
        author_name = author_link = u'Unknown'

    title = doc.cssselect('h2')[0]
    el = title.getnext()
    contents = u''
    while el is not None and el.tag is not etree.Comment:
        if el.tag not in EXCLUDE_PAGE_TAGS:
            contents += html.tostring(el, encoding=unicode)
        el = el.getnext()
    return (author_name, author_link, contents)

from db import *

setup_all()
create_all()

dates = []

cur_issue = None

for year in xrange(START_YEAR, CUR_YEAR + 1):
    doc = html.document_fromstring(content_for_title(title_for_year(year)))
    drop_child_elements(doc, DROP_ARCHIVE_SELECTORS)
    articles = doc.cssselect('li a')
    for article in articles:
        title = html.tostring(article, method='text', encoding='utf-8')
        page_title = article.get('href').replace('/wiki/', '')
        article_title = article.text_content()
        date = parser.parse(page_title.split('/')[1])
        if date not in dates:
            cur_issue = Issue(date=date)
            dates.append(date)
            session.commit()
        author_name, author_link, content = parse_article(page_title)
        Post(permalink=page_title, title=article_title, content=content, author_name=author_name, author_link=author_link, issue=cur_issue)
        session.commit()