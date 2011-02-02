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

from spyder.core.constants import *
from spyder.core.frontier import *
from spyder.core.messages import serialize_date_time, deserialize_date_time
from spyder.core.prioritizer import SimpleTimestampPrioritizer
from spyder.core.settings import Settings
from spyder.core.sqlitequeues import SQLiteSingleHostUriQueue
from spyder.thrift.gen.ttypes import CrawlUri


class BaseFrontierTest(unittest.TestCase):

    def test_adding_uri_works(self):

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        next_crawl_date = now + timedelta(days=1)

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        curi = CrawlUri("http://localhost")
        curi.rep_header = { "Etag" : "123", "Date" : serialize_date_time(now) }
        curi.current_priority = 2

        frontier = AbstractBaseFrontier(s,
                SQLiteSingleHostUriQueue(s.FRONTIER_STATE_FILE),
                SimpleTimestampPrioritizer(s))
        frontier.add_uri(curi)

        for uri in frontier._front_end_queues.queue_head():
            (url, etag, mod_date, queue, next_date) = uri
            self.assertEqual("http://localhost", url)
            self.assertEqual("123", etag)
            self.assertEqual(now, datetime.fromtimestamp(mod_date))
            self.assertTrue(next_crawl_date<datetime.fromtimestamp(next_date))
            frontier._current_uris[url] = uri

    def test_crawluri_from_uri(self):

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        now_timestamp = time.mktime(now.timetuple())
        next_crawl_date = now + timedelta(days=1)
        next_crawl_date_timestamp = time.mktime(next_crawl_date.timetuple())

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = AbstractBaseFrontier(s,
                SQLiteSingleHostUriQueue(s.FRONTIER_STATE_FILE),
                SimpleTimestampPrioritizer(s))

        uri = ("http://localhost", "123", now_timestamp, 1,
                next_crawl_date_timestamp)

        curi = frontier._crawluri_from_uri(uri)

        self.assertEqual("http://localhost", curi.url)
        self.assertEqual("123", curi.req_header["Etag"])
        self.assertEqual(serialize_date_time(now), curi.req_header["Last-Modified"])

    def test_crawluri_from_uri_with_credentials(self):

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        now_timestamp = time.mktime(now.timetuple())
        next_crawl_date = now + timedelta(days=1)
        next_crawl_date_timestamp = time.mktime(next_crawl_date.timetuple())

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = AbstractBaseFrontier(s,
                SQLiteSingleHostUriQueue(s.FRONTIER_STATE_FILE),
                SimpleTimestampPrioritizer(s))

        uri = ("http://user:passwd@localhost", "123", now_timestamp, 1,
            next_crawl_date_timestamp)

        curi = frontier._crawluri_from_uri(uri)

        self.assertEqual("http://user:passwd@localhost", curi.url)
        self.assertEqual("123", curi.req_header["Etag"])
        self.assertEqual(serialize_date_time(now),
            curi.req_header["Last-Modified"])
        self.assertEqual("user", curi.optional_vars[CURI_SITE_USERNAME])
        self.assertEqual("passwd", curi.optional_vars[CURI_SITE_PASSWORD])


class SingleHostFrontierTest(unittest.TestCase):

    def test_that_updating_heap_works(self):

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = SingleHostFrontier(s)

        q1 = []
        q2 = []

        now = datetime(*datetime.fromtimestamp(
            time.time()).timetuple()[0:6]) - timedelta(days=2)

        for i in range(1, 20):
            curi = CrawlUri("http://localhost/test/%s" % i)
            curi.current_priority = (i % 2 + 1)
            curi.rep_header = { "Etag" : "123%s" % i, "Date" : serialize_date_time(now) }

            frontier.add_uri(curi)

            if i % 2 == 0:
                (url, etag, mod_date, next_date, prio) = frontier._uri_from_curi(curi)
                next_date = next_date - 1000 * 60 * 5
                frontier._front_end_queues.update_uri((url, etag, mod_date,
                            next_date, prio))
                q2.append(curi.url)
            else:
                q1.append(curi.url)

        self.assertRaises(Empty, frontier._heap.get_nowait)

        frontier._update_heap()

        for i in range(1, 10):
            candidate_uri = frontier._heap.get_nowait()
            (nd, (url, etag, mod_date, next_date, prio)) = candidate_uri

            if url in q1:
                self.assertTrue(url in q1)
                q1.remove(url)
            elif url in q2:
                self.assertTrue(url in q2)
                q2.remove(url)

        self.assertEqual(10, len(q1))
        self.assertEqual(0, len(q2))


if __name__ == '__main__':
    unittest.main()
