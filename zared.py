import argparse
import os
from random import random
import time

import arrow

from item import *


class Zared:

    ZARED_INDEX = 'canonical_url'
    ZARED_COLUMNS = [
        'audience_segment', 'type', 'filename',
        'added', 'last_updated', 'bought', 'ignored'
    ]
    FILEPATH = 'item/{audience_segment}/{type}'

    def __init__(self):
        pass

    def to_disk(self):
        # dump zared dataframe to memory
        pass

    def stock_take(self):
        """
        update the zared dataframe using what we have on disk
        """
        

    def update(self, zared_row):
        filepath = self.FILEPATH.format(
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
            to_update = to_update[~to_update['ignored']]
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--now', action='store_true')
    args = parser.parse_args()
    # call update all
