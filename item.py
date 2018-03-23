from functools import reduce
import json
import os
import pickle
import re
import requests
from unidecode import unidecode
from urllib.parse import quote, urlparse
from warnings import warn

import arrow
from bs4 import BeautifulSoup
import pandas as pd

with open('stores.json', 'r') as f:
    STORE_IDS = {
        store['id']: ' '.join(store['addressLines'])
        for store in json.load(f)
    }


class Item:
    """
    Attributes:
        reference_id (str)
        part_number (str)
        canonical_url (str)
        image_url (str)
        name (str)
        color (str)
        description (str)
        dimensions (str)
        composition (dict)
        care (str)
        category ((audience_segment, type))
        price_history
            (pd.DataFrame((timestamp, human_timestamp, price)))
        availability
            (pd.DataFrame((
                timestamp, human_timestamp, location, size, available
            )))
        bought (bool)
        ignore (bool)
        filename (str)
    """

    PATH = 'items/'
    FILEPATH = 'items/{audience_segment}/{type}'
    PRICE_HISTORY_COLUMNS = [
        'timestamp', 'human_timestamp', 'price'
    ]
    AVAILABILITY_COLUMNS = [
        'timestamp', 'human_timestamp', 'location', 'store_id',
        'size', 'size_id', 'available', 'quantity'
    ]
    STORE_AVAILABILITY_URL = (
        'https://itxrest.inditex.com/LOMOServiciosRESTCommerce-ws/'
        'common/1/stock/campaign/V{year}/product/part-number/'
        '{part_number}?physicalStoreId={store_ids}&ajax=true'
    )
    COLOR_ANCHOR = '#selectedColor={color_id}'

    def __init__(self, **kwargs):
        assert 'canonical_url' in kwargs, 'item url not provided'
        self.__dict__.update(kwargs)

    def filename_prefixes(self):
        return (
            'bought_' if self.bought is True else ''
        ) + (
            'ignore_' if self.ignore is True else ''
        )

    def json_filename(self):
        return self.filename + '.json'

    def availability_filename(self):
        return (
            self.filename_prefixes() +
            'availability_' +
            self.filename +
            '.csv'
        )

    def price_filename(self):
        return self.filename_prefixes() + 'price_' + self.filename + '.csv'

    def to_disk(self):
        self.filepath = self.FILEPATH.format(
            audience_segment=self.category[0].lower(),
            type=self.category[1].lower()
        )
        os.makedirs(self.filepath, exist_ok=True)
        self.filename = unidecode(
            self.name.lower().replace(' ', '_')
        )
        if self.json_filename() in os.listdir(self.filepath):
            self.filename = (
                self.filename +
                '_{time}'.format(time=arrow.now().timestamp)
            )

        to_archive = self.__dict__.copy()
        to_archive.pop('price_history')\
                  .to_csv(
                      self.filepath + '/' + self.price_filename(), index=False
                  )
        to_archive.pop('availability')\
                  .to_csv(
                      self.filepath + '/' + self.availability_filename(),
                      index=False
                  )
        with open(self.filepath + '/' + self.json_filename(), 'w') as f:
            print(json.dumps(to_archive), file=f)

    @staticmethod
    def from_disk(filepath, filename):
        with open(filepath + '/' + filename + '.json', 'r') as f:
            item = Item(**json.load(f))
        item.price_history = pd.read_csv(
            filepath + '/price_' + filename + '.csv'
        ).reindex(columns=Item.PRICE_HISTORY_COLUMNS)
        item.availability = pd.read_csv(
            filepath + '/availability_' + filename + '.csv'
        ).reindex(columns=Item.AVAILABILITY_COLUMNS)
        return item

    @staticmethod
    def get_soup(url, color=None):
        color_id = None
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')
        if color is not None:
            data = Item.get_data_layer(soup)
            colors = {
                color['name'].lower(): color['id']
                for color in data['product']['detail']['colors']
            }
            if color.lower() in colors:
                color_id = colors.get(color.lower())
                url += Item.COLOR_ANCHOR.format(color_id=color_id)
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'lxml')
            else:
                color = None
        return soup, color, color_id

    @staticmethod
    def get_data_layer(soup):
        return json.loads(re.match(
            r'.*window\.zara\.dataLayer = (\{.*\});.*',
            [
                script
                for script in soup.find_all(
                    'script', {'type': 'text/javascript'}
                )
                if 'window.zara.appConfig' in script.text
            ][0].text
        ).group(1))

    @staticmethod
    def get_reference_id(soup):
        return soup.find(class_='reference').text

    @staticmethod
    def get_part_number(soup):
        return re.search(
            r'"zara:///1/products\?partNumber=(\d+)"',
            soup.text
        ).groups(1)[0]

    @staticmethod
    def get_canonical_url(soup, color_id=None):
        return soup.find('link', {'rel': 'canonical'})['href'] + (
            Item.COLOR_ANCHOR.format(color_id=color_id)
            if color_id is not None else ''
        )

    @staticmethod
    def get_image_url(soup):
        return urlparse(
            soup.find(class_='_seoImg')['href']
        )._replace(scheme='https', query='').geturl()

    @staticmethod
    def get_name(soup, color):
        return soup.find('h1', {'class': 'product-name'}).contents[0] + (
            ' ' + color.upper() if color is not None else ''
        )

    @staticmethod
    def get_color(soup):
        return soup.find(class_='_colorName').text

    @staticmethod
    def get_description(soup):
        return soup.find(class_='description').text

    @staticmethod
    def get_composition(data_layer):
        return data_layer['product']['detail']['detailedComposition']

    @staticmethod
    def get_composition_str(composition_dict):
        if len(composition_dict.keys() - {'exceptions', 'parts'}) > 0:
            warn('Unexpected field / type encountered in composition.')
        if len({
                type(exception)
                for exception in composition_dict['exceptions']
        } - {str}) > 0:
            warn('Unexpected field / type encountered in composition.')
        if len(
                reduce(
                    lambda a, b: a | b,
                    (part.keys() for part in composition_dict['parts'])
                ) -
                {
                    'areas',
                    'components',
                    'description',
                    'microcontents',
                    'reinforcements'
                }
        ) > 0:
            warn('Unexpected field / type encountered in composition.')
        if len(
                reduce(
                    lambda a, b: a | b,
                    (
                        area.keys()
                        for part in composition_dict['parts']
                        for area in part['areas']
                    )
                ) - {
                    'components', 'description'
                }
        ) > 0:
            warn('Unexpected field / type encountered in composition.')
        if len(
                reduce(
                    lambda a, b: a | b,
                    (
                        component.keys()
                        for part in composition_dict['parts']
                        for component in part['components']
                    )
                ) - {
                    'material', 'percentage'
                }
        ) > 0:
            warn('Unexpected field / type encountered in composition.')
        if len(
                reduce(
                    lambda a, b: a | b,
                    (
                        {
                            type(microcontent)
                            for microcontent in part['microcontents']
                        } | {
                            type(reinforcement)
                            for reinforcement in part['reinforcements']
                        } | {
                            type(part['description'])
                        }
                        for part in composition_dict['parts']
                    )
                ) - {str}
        ) > 0:
            warn('Unexpected field / type encountered in composition.')
        composition_str = ''
        for part in composition_dict['parts']:
            composition_str += part['description'] + '\n'
            for component in part['components']:
                composition_str += (
                    '\t' +
                    component['percentage'] +
                    ' ' +
                    component['material'] +
                    '\n'
                )
            for area in part['areas']:
                composition_str += '\t' + area['description'] + '\n'
                for component in area['components']:
                    composition_str += (
                        '\t\t' +
                        component['percentage'] +
                        ' ' +
                        component['material'] +
                        '\n'
                    )
            if len(part['microcontents']) > 0:
                composition_str += '\t' + 'MICROCONTENTS' + '\n'
                for microcontent in part['microcontents']:
                    composition_str += '\t\t' + microcontent + '\n'
            if len(part['reinforcements']) > 0:
                composition_str += '\t' + 'REINFORCEMENTS' + '\n'
                for reinforcement in part['reinforcements']:
                    composition_str += '\t\t' + reinforcement + '\n'
        if len(composition_dict['exceptions']) > 0:
            composition_str += 'EXCEPTIONS' + '\n'
            for exception in composition_dict['exceptions']:
                composition_str += '\t' + exception + '\n'

        return composition_str

    @staticmethod
    def get_care(data_layer):
        return data_layer['product']['detail']['care']

    @staticmethod
    def get_care_str(care_dict):
        return '. '.join([
            instruction['description']
            for instruction in care_dict
        ]) + '.'

    @staticmethod
    def get_category(soup):
        breadcrumbs = soup.find('div', class_='breadcrumbs')\
                          .find('ul')\
                          .contents
        return (
            breadcrumbs[1].find('a').text,
            breadcrumbs[2].find('a').text
        )

    @staticmethod
    def get_price(data_layer):
        prices = {
            size_info['price']
            for size_info in data_layer['productMetaData']
        }
        assert len(prices) == 1, 'more than one price found for this item'
        return float(prices.pop())

    @staticmethod
    def price_to_DataFrame(timestamp, human_timestamp, price):
        return pd.DataFrame([{
            'timestamp': timestamp,
            'human_timestamp': human_timestamp,
            'price': price
        }], columns=Item.PRICE_HISTORY_COLUMNS)

    @staticmethod
    def get_size_availabilities(soup, data, color_id=None):
        response = requests.get(
            Item.STORE_AVAILABILITY_URL.format(
                year=arrow.now().year,
                part_number=Item.get_part_number(soup),
                store_ids=quote(','.join(map(str, STORE_IDS.keys())))
            )
        )
        stocks = json.loads(response.text).get('stocks') or []
        sizes = [
            color
            for color in data['product']['detail']['colors']
            if color['id'] == color_id
        ][0]['sizes'] if color_id is not None else (
            data['product']['detail']['colors'][0]['sizes']
        )
        size_ids_to_names = {size['id']: size['name'] for size in sizes}
        return [
            # online store stock
            {
                'location': 'online',
                'store_id': None,
                'size': size['name'],
                'size_id': size['id'],
                'available': size['availability'] is 'in_stock',
                'quantity': None
            }
            for size in sizes
        ] + [
            # physical store stock
            {
                'location': STORE_IDS[store['physicalStoreId']],
                'store_id': store['physicalStoreId'],
                'size': size_ids_to_names[size['sizeId']],
                'size_id': size['sizeId'],
                'available': size['quantity'] > 0,
                'quantity': size['quantity']
            }
            for store in stocks
            for size in store['sizeStocks']
        ]

    @staticmethod
    def availability_to_DataFrame(
            timestamp,
            human_timestamp,
            size_availabilities
    ):
        df = pd.DataFrame(size_availabilities)
        df['timestamp'] = timestamp
        df['human_timestamp'] = human_timestamp
        return df.reindex(columns=Item.AVAILABILITY_COLUMNS)

    @staticmethod
    def from_url(url, color=None):
        now_human = arrow.now()
        now = now_human.timestamp
        soup, color, color_id = Item.get_soup(url, color)
        data_layer = Item.get_data_layer(soup)
        item = Item(
            reference_id=Item.get_reference_id(soup),
            part_number=Item.get_part_number(soup),
            canonical_url=Item.get_canonical_url(soup, color_id),
            image_url=Item.get_image_url(soup),
            name=Item.get_name(soup, color),
            color=(color or Item.get_color(soup)),
            color_id=color_id,
            description=Item.get_description(soup),
            dimensions=None,
            composition=Item.get_composition(data_layer),
            care=Item.get_care(data_layer),
            category=Item.get_category(soup),
            price_history=Item.price_to_DataFrame(
                timestamp=now,
                human_timestamp=now_human,
                price=Item.get_price(data_layer)
            ),
            availability=Item.availability_to_DataFrame(
                timestamp=now,
                human_timestamp=now_human,
                size_availabilities=Item.get_size_availabilities(
                    soup, data_layer, color_id=color_id
                )
            ),
            bought=False,
            ignore=False
        )
        item.to_disk()
        return item

    def update(self, in_memory_update=True, on_disk_update=True):
        now_human = arrow.now()
        now = now_human.timestamp
        soup, color, color_id = self.get_soup(self.canonical_url, self.color)
        data_layer = self.get_data_layer(soup)
        price = self.get_price(data_layer)
        size_availabilities = self.get_size_availabilities(
            soup, data_layer, color_id=self.color_id
        )
        new_price_history = self.price_to_DataFrame(
            timestamp=now,
            human_timestamp=now_human,
            price=price
        )
        new_availability = self.availability_to_DataFrame(
            timestamp=now,
            human_timestamp=now_human,
            size_availabilities=size_availabilities
        )
        if in_memory_update is True:
            self.price_history = pd.concat((
                self.price_history,
                new_price_history
            ), axis=0)
            self.availability = pd.concat((
                self.availability,
                new_availability
            ), axis=0)
        if on_disk_update is True:
            new_price_history.reindex(
                columns=self.PRICE_HISTORY_COLUMNS
            ).to_csv(
                self.filepath + '/' + self.price_filename(),
                mode='a',
                index=None,
                header=None
            )
            new_availability.reindex(
                columns=self.AVAILABILITY_COLUMNS
            ).to_csv(
                self.filepath + '/' + self.availability_filename(),
                mode='a',
                index=None,
                header=None
            )
