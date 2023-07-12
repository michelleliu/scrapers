import sys
import csv
import re
from urllib.request import urlopen, Request

from bs4 import BeautifulSoup

from model import ArticleContent, SectionContent


def is_blank(string):
    return not (string and string.strip())


class SerContentExtractor:
    def __init__(self):
        self.base_url = 'https://www.britishecologicalsociety.org/applied-ecology-resources/search/'
        self.ignored_section_names = {'Funding', 'Contacts', 'Timeframe', 'Learn More'}

    def traverse_and_extract(self, start_page=1, page_limit=10):
        page = start_page

        while page_limit < 0 or page <= page_limit:
            projects = self.__read_html(f'{self.base_url}/page/{page}').find_all('div', class_='faux-block-container')
            if len(projects) == 0:
                print("No projects found.")
                break
            else:
                print(f'Extracting {len(projects)} docs from page #{page}...')
                for i, project in enumerate(projects):
                    if (project_url_doc := project.find('a', href=True)) is not None:
                        yield self.__extract(project_url_doc['href'])
                        print(f'Extracted {i + 1} of {len(projects)}')
                page += 1

    def __extract(self, url) -> ArticleContent:
        doc = self.__read_html(url)

        title = self.__extract_title(doc)
        abstract = self.__extract_abstract(doc)
        #location = self.__extract_location(doc)
        publication_date, published_by, content_type, journal_title, doi, website, authors, email, language, location = self.__extract_metadata(doc)
        download_link = self.__extract_download_link(doc)
        keywords = self.__extract_keywords(doc)
        #start_date, end_date = self.__extract_dates(doc)
        #text = self.__extract_text(doc)

        return ArticleContent(url, title, publication_date, published_by, content_type, journal_title, doi, website, authors, email, language, location, download_link, abstract, keywords)

    def __read_html(self, url) -> BeautifulSoup:
        with urlopen(Request(url, headers={'User-Agent': "Magic Browser"})) as resp:
            text = resp.read().decode("utf8")
            return BeautifulSoup(text, 'html.parser')

    def __extract_title(self, doc: BeautifulSoup):
        if (main_container := doc.find(class_='bleed-area')) is not None:
            return main_container.find('h1').get_text()
        else:
            return None

    def __extract_abstract(self, doc: BeautifulSoup):

        if (content_doc := doc.find('div', class_ = 'content-block')) is not None:
            if (h2_doc := content_doc.find('h2', string='Abstract')) is not None:
                abstract_text_doc = h2_doc.find_next_sibling("p")

                result = abstract_text_doc.get_text()
            else:
                return None
        else:
            return None

        return result

    def __extract_text(self, doc: BeautifulSoup):
        result = []

        # Check for overview
        if (overview_doc := doc.find(lambda tag: tag.name == 'div' and 'overview' in tag.attrs.get('class', []))) is not None:
            if (h2_doc := overview_doc.find('h2', string='Overview')) is not None:
                overview_text_docs = h2_doc.find_next_siblings()
                if len(overview_text_docs) != 0:
                    result.append(SectionContent('Overview', ''.join([doc.get_text() for doc in overview_text_docs])))

        # Check for other sections
        section_buttons = doc.find_all('button', class_='accordion')

        for section_button in section_buttons:
            section_name = section_button.string

            if section_name not in self.ignored_section_names:
                section: BeautifulSoup = section_button.find_next_sibling('div', class_='panel')
                result = result + self.__parse_section(section_name, section)

        return result

    def __parse_section(self, section_name, section_doc: BeautifulSoup):
        result = []

        def append(name, text):
            if not is_blank(text):
                result.append(SectionContent(name, text))

        current_name = section_name
        current_text = ''

        for element in section_doc:
            if element.name == 'h2':
                append(current_name, current_text)
                current_name = element.string
                current_text = ''
            else:
                current_text = current_text + element.get_text()

        append(current_name, current_text)
        return result

    def __extract_dates(self, doc: BeautifulSoup):
        timeframe_button = doc.find('button', string='Timeframe')

        if timeframe_button is not None:
            start_date = None
            start_date_doc = timeframe_button.find_next(self.__get_attr_predicate('Start Date:'))
            if start_date_doc is not None:
                start_date = start_date_doc.text.removeprefix('Start Date: ')

            end_date = None
            end_date_doc = timeframe_button.find_next(self.__get_attr_predicate('End Date:'))
            if end_date_doc is not None:
                end_date = end_date_doc.text.removeprefix('End Date: ')

            return start_date, end_date

        return None, None

    def __extract_location(self, doc: BeautifulSoup):
        if ( meta_details := doc.find('div', class_='document-meta__details')) is not None:
            if (location_doc := meta_details.find('dt', string='Location')) is not None:
                return location_doc.find_next_sibling('dd').string

    def __extract_download_link(self, doc: BeautifulSoup):
        if ( meta_details := doc.find('div', class_='document-meta__download')) is not None:
            if (download_link_doc := meta_details.find('a', href=True)) is not None:
                return download_link_doc['href']
            return None

        return None
    def __extract_metadata(self, doc: BeautifulSoup):
        if ( meta_details := doc.find('div', class_='document-meta__details')) is not None:

            if (metadata_doc := meta_details.find('dt', string='Published online')) is not None:
                publication_date = metadata_doc.find_next_sibling('dd').string
            else:
                publication_date = None

            if (metadata_doc := meta_details.find('dt', string='Published by')) is not None:
                published_by = metadata_doc.find_next_sibling('dd').string
            else:
                published_by = None

            if (metadata_doc := meta_details.find('dt', string='Content type')) is not None:
                content_type = metadata_doc.find_next_sibling('dd').string
            else:
                content_type = None

            if (metadata_doc := meta_details.find('dt', string='Journal title')) is not None:
                journal_title = metadata_doc.find_next_sibling('dd').string
            else:
                journal_title = None

            if (metadata_doc := meta_details.find('dt', string='DOI')) is not None:
                doi_doc = metadata_doc.find_next('a', href=True)
                doi = doi_doc['href']
            else:
                doi = None

            if (metadata_doc := meta_details.find('dt', string='Website(s)')) is not None:
                website_doc = metadata_doc.find_next('a', href=True)
                website = website_doc['href']
            else:
                website = None

            if (metadata_doc := meta_details.find('dt', string='Author(s)')) is not None:
                authors = metadata_doc.find_next('a', href=True).string
            else:
                authors = None

            if (metadata_doc := meta_details.find('dt', string='Contact email(s)')) is not None:
                email = metadata_doc.find_next_sibling('dd').string
            else:
                email = None

            if (metadata_doc := meta_details.find('dt', string='Publication language')) is not None:
                language = metadata_doc.find_next_sibling('dd').string
            else:
                language = None

            if (metadata_doc := meta_details.find('dt', string='Location')) is not None:
                location = metadata_doc.find_next_sibling('dd').string
            else:
                location = None

        return publication_date, published_by, content_type, journal_title, doi, website, authors, email, language, location

    def __extract_keywords(self, doc):
        keywords = []
        if ( keywords_doc := doc.find('ul', class_='key-words cf')) is not None:
            keywords_list = keywords_doc.find_all('li', recursive=False, string=True)
            for keyword in keywords_list:
                keywords.append(keyword.string)

        return keywords

    def __get_attr_predicate(self, pattern):
        return lambda tag: \
            tag.name == 'p' and \
            tag.attrs.get('class') == ['singleattr'] and \
            tag.find('strong', string=re.compile(pattern)) is not None


class IteratorAsList(list):
    def __init__(self, it):
        super().__init__()
        self.it = it

    def __iter__(self):
        return self.it

    def __len__(self):
        return 1


if __name__ == '__main__':
    extractor = SerContentExtractor()

    firstpage = 1
    lastpage = 1
    suffix=''

    if len(sys.argv) == 2:
        start_page = int(sys.argv[1])
        page_limit = int(sys.argv[1])
        suffix="_"+str(start_page)
    elif len(sys.argv) == 3:
        start_page = int(sys.argv[1])
        page_limit = int(sys.argv[2])
        suffix="_"+str(start_page)+"-"+str(page_limit)

    articles = extractor.traverse_and_extract(start_page, page_limit)

    with open('bes_aer_projects_data'+suffix+'.tsv', 'w', newline='') as out_f:
        writer = csv.writer(out_f, delimiter='\t')

        writer.writerow(['url', 'title', 'publication_date', 'published_by', 'content_type', 'journal_title', 'doi', 'website', 'authors', 'email', 'language', 'location', 'download_link', 'abstract', 'keywords'])

        for article in articles:
            writer.writerow([article.url, article.title, article.publication_date, article.published_by, article.content_type, article.journal_title, article.doi, article.website, article.authors, article.email, article.language, article.location, article.download_link, article.abstract, article.keywords])
