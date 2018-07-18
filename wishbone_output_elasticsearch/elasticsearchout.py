#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  elasticsearchout.py
#
#  Copyright 2016 Jelle Smet <development@smetj.net>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

from wishbone.module import OutputModule
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from wishbone.event import extractBulkItems


class ElasticSearchOut(OutputModule):

    '''**Index data into Elasticsearch.**

    Submits data to Elasticsearch.

    Events are indexed one by one.

    Events can be indexed in bulk to increase throughput when incoming events
    are type <Bulk>.  Bulk objects consist out of multiple events and are
    created by the <wishbone.flow.tippingbucket> module.

    Parameters:

        - selection(str)("@data")
           |  The part of the event to submit externally.
           |  Use an empty string to refer to the complete event.

        - hosts(list)(["localhost:9200"])
           |  A list of "hostname:port" strings.

        - use_ssl(bool)(False)
           |  When enable expects SSL connectivity

        - verify_certs(bool)(False)
           |  When using SSL do certificate verification

        - index(str)("wishbone")
           |  The name of the index

        - doc_type(str)("wishbone")
           |  The document type

    Queues:

        - inbox
           |  Incoming events submitted to the outside.

    '''

    def __init__(
            self,
            actor_config,
            selection="data",
            payload=None,
            parallel_streams=1,
            native_events=False,
            hosts=["localhost:9200"],
            use_ssl=False,
            verify_certs=False,
            index="wishbone",
            doc_type="wishbone"):
        OutputModule.__init__(self, actor_config)
        self.pool.createQueue("inbox")
        self.registerConsumer(self.consume, "inbox")

    def preHook(self):
        self.elasticsearch = Elasticsearch(
            self.kwargs.hosts,
            use_ssl=self.kwargs.use_ssl,
            verify_certs=self.kwargs.verify_certs
        )

    def consume(self, event):
        if event.isBulk():
            bulk_items = []
            for e in extractBulkItems(event):
                kwargs = {
                    "_index": self.kwargs.index,
                    "_type": self.kwargs.doc_type
                }
                source = e.get(self.kwargs.selection)
                if "_id" in source:
                    kwargs["id"] = source.pop("_id")
                kwargs['_source'] = source
                bulk_items.append(kwargs)
            resp = bulk(self.elasticsearch, bulk_items)
            self.logging.debug("Indexed bulk: {}".format(resp))
        else:
            body = event.get(self.kwargs.selection)
            kwargs = {
                "index": self.kwargs.index,
                "doc_type": self.kwargs.doc_type,
            }
            if "_id" in body:
                kwargs["id"] = body.pop("_id")
            kwargs['body'] = body
            resp = self.elasticsearch.index(**kwargs)
            self.logging.debug("Idexed: {}".format(resp))
