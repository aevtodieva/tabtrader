import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import re
import json
from bs4 import BeautifulSoup

# Получаем данные из микпенела
url = "https://eu.mixpanel.com/api/query/insights?project_id=2786851&bookmark_id=55080435"

headers = {
    "accept": "application/json",
    "authorization": CODE # add authorization code
}

response_text = requests.get(url, headers=headers)
mixpanel_data = json.loads(response_text.text)

# Получение данных статей из страпи
url = "https://content2.tabtrader.com/graphql"
query = """
query {
  academyArticles(
    locale: "en"
    pagination: { limit: -1 }
  ) {
    meta {
      pagination {
        total
        page
        pageSize
        pageCount
      }
    }
    data {
      id
      attributes {
        title
        locale
        slug
        content_reader
        publishedAt
        updatedAt
        reading_time
        content {
          __typename
          ... on ComponentSectionsTitle {
            id
            title
            level
          }
          ... on ComponentSectionsParagraph {
            id
            content
          }
          ... on ComponentSectionsList {
            id
            style
            list_item {
              id
              content
            }
          }
          ... on ComponentSectionsTable {
            id
            column {
              id
              title
              cell {
                id
                cell_text
                background
                style
              }
            }
          }
          ... on ComponentSectionsVideo {
            id
            embedded_code
            description
            video_file {
              data {
                attributes {
                  name
                  url
                  formats
                  mime
                  ext
                  previewUrl
                  caption
                  width
                  height
                  size
                }
              }
            }
          }
          ... on ComponentSectionsImage {
            id
            description
            image_link
            image_file {
              data {
                attributes {
                  name
                  url
                  formats
                  previewUrl
                  caption
                  width
                  height
                  size
                }
              }
            }
          }
          ... on ComponentSectionsSeparator {
            id
            style_separator
          }
          ... on ComponentSectionsQuote {
            id
            quote
          }
          ... on ComponentSectionsSocialContacts {
            id
            show
          }
          ... on ComponentSectionsFaq {
            id
            faq_items {
              id
              question
              answer
            }
          }
        }
      }
    }
  }
}

"""
response = requests.post(url, json={'query': query})
articles = response.json()['data']['academyArticles']['data']


def count_words(text):
    cleaned_text = re.sub(r'[^\w\s]', '', text)  # Удаляем специальные символы
    words = re.findall(r'\b\w+\b', cleaned_text)  # Находим все слова
    return len(words)

# Подключение к Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
gc = gspread.authorize(credentials)
sheet_id = SHEET ID # add sheet id
spreadsheet_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}'
worksheet = gc.open_by_url(spreadsheet_url).worksheet("academy")

# Запись данных и количества слов в Google Sheets
data = []
for article in articles:
    title = article['attributes']['title']
    reading_time = article['attributes']['reading_time']
    article_slug = article['attributes']['slug']
    publishedAt = article['attributes']['publishedAt'].split('T')[0]
    content_reader = article['attributes'].get('content_reader', None)
    # Уникальные просмотры
    unique_views = mixpanel_data['series']['A. Article Opened - Unique'].get(article_slug, {}).get('all', 0)
    # Общее количество просмотров
    total_views = mixpanel_data['series']['B. Article Opened - Total'].get(article_slug, {}).get('all', 0)

    if content_reader:
        # Десериализация JSON и обработка
        content_text = json.loads(content_reader)
        text = " ".join(block['data']['text'] for block in content_text['blocks'] if block['type'] == 'paragraph')
    else:

        # Обработка заголовков и параграфов из content
        text = ""
        print(article)
        for component in article['attributes']['content']:
            if component['__typename'] == 'ComponentSectionsTitle':
                if component['title']:
                    text += component['title'] + " "

            elif component['__typename'] == 'ComponentSectionsParagraph':
                if component['content']:
                    text += component['content'] + " "

    word_count = count_words(text)
    data.append([title, reading_time, publishedAt, word_count, unique_views, total_views])

# Обновляем данные начиная со второй строки
start_row = 2  # Предполагается, что первая строка содержит заголовки
worksheet.update(range_name=f'A{start_row}:F{start_row + len(data) - 1}', values=data)

print("Data has been written to the sheet.")

