import argparse
import os
from random import random
import sys
import time
from warnings import warn

import arrow
import pandas as pd

from item import *


class Zared:

    ZARED_INDEX = 'canonical_url'
    ZARED_COLUMNS = [
        'audience_segment', 'type', 'filename',
        'added', 'added_human', 'last_updated', 'last_updated_human',
        'bought', 'ignore'
    ]
    ZARED_FILENAME = 'zared.csv'

    def __init__(self):
        try:
            self.zared = pd.read_csv(self.ZARED_FILENAME, index_col=0)
        except FileNotFoundError:
            warn('No default Zared file found.')

    def to_disk(self):
        self.zared.to_csv(self.ZARED_FILENAME)

    def stock_take(self):
        """
        update the zared dataframe using what we have on disk
        """
        if getattr(self, 'zared', None) is None or self.zared is None:
            self.zared = pd.DataFrame(columns=self.ZARED_COLUMNS)
            self.zared.index.name = self.ZARED_INDEX
        for root, directories, filenames in os.walk(Item.PATH):
            filenames = [
                filename[:-5]
                for filename in filenames
                if filename.endswith('.json')
            ]
            if len(filenames) > 0:
                _, audience_segment, category_type = root.split('/')
                added_timestamps = {
                    filename: pd.read_csv(
                        root + '/price_' + filename + '.csv'
                    )['timestamp'].min()
                    for filename in filenames
                }
                last_updated_timestamps = {
                    filename: pd.read_csv(
                        root + '/price_' + filename + '.csv'
                    )['timestamp'].max()
                    for filename in filenames
                }
                metadata = {
                    filename: Item.from_disk(root, filename)
                    for filename in filenames
                }
                root_df = pd.DataFrame(
                    [
                        {
                            'audience_segment': audience_segment,
                            'type': category_type,
                            'filename': filename,
                            'added': added_timestamps[filename],
                            'added_human': arrow.get(
                                added_timestamps[filename]
                            ).to('US/Eastern'),
                            'last_updated': last_updated_timestamps[filename],
                            'last_updated_human': arrow.get(
                                last_updated_timestamps[filename]
                            ).to('US/Eastern'),
                            'bought': metadata[filename].bought,
                            'ignore': metadata[filename].ignore,
                        }
                        for filename in filenames
                    ],
                    index=[
                        metadata[filename].canonical_url
                        for filename in filenames
                    ]
                )
                root_df.index.name = self.ZARED_INDEX
                self.zared = pd.concat([self.zared, root_df], axis=0)\
                               .reset_index()\
                               .sort_values('last_updated', ascending=True)\
                               .drop_duplicates(
                                    subset='canonical_url', keep='last'
                                )\
                               .set_index('canonical_url')
        self.to_disk()

    def add_item(self, url, color=None):
        item = Item.from_url(url, color)
        self.zared = pd.concat([
            self.zared,
            pd.DataFrame({
                'audience_segment': item.category[0],
                'type': item.category[1],
                'filename': item.filename,
                'added': item.price_history['timestamp'].min(),
                'added_human': arrow.get(
                    item.price_history['timestamp'].min()
                ).to('US/Eastern'),
                'last_updated': item.price_history['timestamp'].max(),
                'last_updated_human': arrow.get(
                    item.price_history['timestamp'].max()
                ).to('US/Eastern'),
                'bought': item.bought,
                'ignore': item.ignore,
            }, index=[item.canonical_url])
        ], axis=0)
        self.to_disk()

    def update(self, zared_row):
        filepath = Item.FILEPATH.format(
            audience_segment=zared_row['audience_segment'],
            type=zared_row['type']
        )
        filename = zared_row['filename']
        item = Item.from_disk(filepath, filename)
        item.update()
        self.zared.loc[zared_row.name, 'last_updated'] = int(time.time())

    def update_all(self, ignored=False, bought=False, verbose=False):
        to_update = self.zared
        if ignored is False:
            to_update = to_update[~to_update['ignore']]
        if bought is False:
            to_update = to_update[~to_update['bought']]
        if verbose is True:
            start_time = arrow.utcnow()
            print('Update started at {utc_epoch} ({eastern})'.format(
                utc_epoch=start_time.timestamp,
                eastern=start_time.to('US/Eastern')
            ))
        self.zared.apply(self.update, axis=1)
        if verbose is True:
            end_time = arrow.utcnow()
            print('Update finished at {utc_epoch} ({eastern})'.format(
                utc_epoch=end_time.timestamp,
                eastern=end_time.to('US/Eastern')
            ))
        self.to_disk()

if __name__ == '__main__':
    z = Zared()
    parser = argparse.ArgumentParser()
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--now', action='store_true')
    parser.add_argument(
        '--url',
        help='Add an item by providing its url',
        action='store',
        type=str
    )
    parser.add_argument(
        '--color',
        help='Specify a color for --url',
        action='store',
        type=str
    )
    args = parser.parse_args()

    if args.update is True:
        if args.now is False:
            time.sleep(random() * 15 * 60)
        z.update_all()
    elif args.url is not None:
        z.add_item(args.url, args.color)

    sys.exit(0)
