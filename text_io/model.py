import dataclasses


@dataclasses.dataclass
class SectionContent:
    name: str
    text: str


@dataclasses.dataclass
class ArticleContent:
    url: str
    title: str
    publication_date: str
    published_by: str
    content_type: str
    journal_title: str
    doi: str
    website: str
    authors: str
    email: str
    language: str
    location: str
    download_link: str
    abstract: str
    keywords: [str]
