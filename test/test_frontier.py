#
# Copyright (c) 2010 Daniel Truemper truemped@googlemail.com
#
# test_frontier.py 27-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# under the License.
# All programs in this directory and
# subdirectories are published under the GNU General Public License as
# described below.
#
#

import time
from datetime import datetime, timedelta
import unittest

from sqlite3 import IntegrityError

from spyder.core.frontier import *
from spyder.core.messages import serialize_date_time, deserialize_date_time
from spyder.core.settings import Settings
from spyder.thrift.gen.ttypes import CrawlUri


class BaseFrontierTest(unittest.TestCase):

    def test_adding_uri_works(self):

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        next_crawl_date = now + timedelta(days=1)

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        curi = CrawlUri("http://localhost")
        curi.rep_header = { "Etag" : "123", "Date" : serialize_date_time(now) }

        frontier = AbstractBaseFrontier(s)
        frontier.add_uri(curi, next_crawl_date)

        # This should really not happen in production because of the
        # UniqueUriFilter
        self.assertRaises(IntegrityError, frontier.add_uri, curi,
            next_crawl_date)

        for uri in frontier._front_end_queues.queue_head(1):
            (url, etag, mod_date, queue, next_date) = uri
            self.assertEqual("http://localhost", url)
            self.assertEqual("123", etag)
            self.assertEqual(now, datetime.fromtimestamp(mod_date))
            self.assertEqual(next_crawl_date,
                    datetime.fromtimestamp(next_date))
            frontier._current_uris.append(url)

        self.assertRaises(AssertionError, frontier.add_uri, curi,
            next_crawl_date)

    def test_crawluri_from_uri(self):

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        now_timestamp = time.mktime(now.timetuple())
        next_crawl_date = now + timedelta(days=1)
        next_crawl_date_timestamp = time.mktime(next_crawl_date.timetuple())

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = AbstractBaseFrontier(s)

        uri = ("http://localhost", "123", now_timestamp, 1,
                next_crawl_date_timestamp)

        curi = frontier._crawluri_from_uri(uri)

        self.assertEqual("http://localhost", curi.url)
        self.assertEqual("123", curi.req_header["Etag"])
        self.assertEqual(serialize_date_time(now), curi.req_header["Last-Modified"])

if __name__ == '__main__':
    unittest.main()
