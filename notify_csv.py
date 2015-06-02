#!/usr/bin/env fades
# -*- coding: utf-8 -*-
##############################################################################
#
#    NotifyCSV script, watch a directory and parse its .csv files
#    Copyright (C) 2015 Latinux S.A. (<http://www.latinux.com.ar>)
#
#    This file is a part of NotifyCSV
#
#    NotifyCSV is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    NotifyCSV is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import csv
import multiprocessing
import os
import re
import sys
import time
# from multiprocessing.pool import Pool

import erppeek  # fades.pypi
import sh  # fades.pypi
from pyinotify import (IN_CLOSE_WRITE, IN_DELETE, IN_DELETE_SELF,  # fades.pypi
                       Notifier, ProcessEvent, WatchManager)


class OdooInstance(object):

    def __init__(self, logger, **connection_data):
        self.logger = logger
        self._host = connection_data.pop("host")
        self._port = connection_data.pop("port")
        self.is_connected = False
        self.connection_data = connection_data
        self.prod_obj = None
        self._default_data = {
            "sale_ok": True,
            "purchase_ok": True,
            "active": True,
            "categ_id": 1,
            "uom_id": 1,
        }
        # self.client = False
        # self.analytic_obj = None
        # self.user_obj = None
        # self.partner_obj = None
        # self.resource_obj = None
        # self.employee_obj = None
        # self.groups_obj = None
        # self._new_columns = {}
        # self._old_columns = {}
        # self.relevant_fields = ("n_proyecto", "nombre", "id_cliente", "estado",
        #                         "id_resp", "fec_ini", "fec_cierre")

    def __feed(self, data):
        """This will work in bkg"""
        pass

    def feed(self, data):
        """Use data to create or update a product"""
        p = multiprocessing.Process(target=self.__feed, args=(data,))
        p.start()

    def connect_to_odoo(self):
        """
        keyword args:
            @param db:
            @param user:
            @param password:
            @param host:
            @param port:
        """
        for j in range(1, 6):
            for i in range(1, 6):
                try:
                    host_port = "http://%s:%s" % (self._host, self._port)
                    self.logger.info("Creating connection with host: %s" % host_port)
                    self.client = erppeek.Client(host_port, **self.connection_data)
                    self.prod_obj = self.client.model("product.product")
                    # self.analytic_obj = self.client.model("account.analytic.account")
                    # self.user_obj = self.client.model("res.users")
                    # self.partner_obj = self.client.model("res.partner")
                    # self.groups_obj = self.client.model("res.groups")
                    # self.employee_obj = self.client.model("hr.employee")
                    # self.resource_obj = self.client.model("resource.resource")
                    self.is_connected = True
                    return True
                except ConnectionRefusedError:
                    self.logger.warning("Connection refused... retrying %s" % i)
                    time.sleep(3)
                    self.is_connected = False
                    continue

            if self.is_connected:
                break

            self.logger.warning("Connection refused 5 times retrying in 150 seconds")
            time.sleep(150)
        return False

    def create_product(self, product_data):
        products = self.prod_obj.read([
            ("name", "=", product_data["name"]),
            ("default_code", "=", product_data["default_code"])
        ])
        if not products:
            product_data.update(self._default_data)
            product = self.prod_obj.create(product_data)
            self.logger.info("New product created: [%s] %s" % (product.default_code, product.name))
        else:
            product = self.prod_obj.browse(products[0]["id"])
            self.logger.info("Product found: [%s] %s" % (product.default_code, product.name))
            new_price = float(product_data["list_price"])
            if product.list_price != new_price:
                self.logger.info("Update price: from %s to %s" % (product.list_price, new_price))
                product.write({"list_price": new_price})
        return product


class EventHandler(ProcessEvent):

    def my_init(self, odoo, logger, dir_to_watch=None, masks=None, regex='.*', delimiter='\t'):
        self.logger = logger
        self.odoo = odoo
        self.logger.info("Starting event handler")
        self.regex = regex
        self.count = 0
        self.delimiter = delimiter
        self._create_dir(dir_to_watch)
        self._fieldnames = ("name", "list_price", "default_code")
        if masks is None:
            self.masks = IN_CLOSE_WRITE | IN_DELETE | IN_DELETE_SELF
        else:
            self.masks = masks
        wm = WatchManager()
        wm.add_watch(self.dir_to_watch, self.masks)
        notifier = Notifier(wm, self)
        self.notifier = notifier

    @property
    def regex(self):
        return self._regex

    @regex.setter
    def regex(self, regex):
        self._regex = re.compile(regex)

    @property
    def fieldnames(self):
        return self._fieldnames

    @fieldnames.setter
    def fieldnames(self, values):
        self._fieldnames = values

    def _create_dir(self, dir_to_watch):
        if not os.path.exists(dir_to_watch):
            self.logger.info("Creating dir to watch: %s" % dir_to_watch)
            sh.mkdir(dir_to_watch)
        self.dir_to_watch = dir_to_watch

    def process_IN_DELETE_SELF(self, event):
        self.logger.warning("Someone removed %s, we re-create it." % event.pathname)
        self._create_dir(event.pathname)

    def process_IN_DELETE(self, event):
        """
        Write log info when file is deleted
        """
        self.logger.info("Deleted file: %s" % event.pathname)

    def process_IN_CLOSE_WRITE(self, event):
        """
        When file is written
        """
        pathname = event.pathname
        self.logger.info("close write on file: %s" % pathname)
        if re.match(self.regex, os.path.split(pathname)[-1]):
            logger.info("CSV file found: %s, let's parse it!" % pathname)
            with open(pathname, newline='') as csvfile:
                csvdict = csv.DictReader(
                    csvfile,
                    fieldnames=self.fieldnames,
                    delimiter=self.delimiter,
                )
                for line in csvdict:
                    self.odoo.create_product(line)
            #     jobs = []
            #     for data in csvdict:
            #         self.count += 1
            #         job = multiprocessing.Process(
            #             name="Process-%s" % self.count,
            #             target=self.odoo.create_product,
            #             args=(data,)
            #         )
            #         jobs.append(job)
            #         job.start()
            # for job in jobs:
            #     job.join()
        return True

if __name__ == '__main__':
    import logging
    from argparse import ArgumentParser

    prog_name = 'NotifyCSV'
    default_dir = os.path.join(os.environ['HOME'], "csv-input")
    logger = logging.getLogger(prog_name)
    parser = ArgumentParser(prog=prog_name)

    parser.add_argument("-d", "--delimiter", help="Specify field delimiter. Default: '\\t'",
                        default='\t')
    parser.add_argument("-r", "--regex", default='.+.[Cc][Ss][Vv]',
                        help=("Use this regex to match names in watched dir. Can be any valid "
                              "Python regex. Default: '^.+\.[cC][sS][vV]$'")
                        )
    parser.add_argument("-l", "--logfile", help="Log to this file")
    parser.add_argument("-w", "--watch-dir", help="Dir to watch. Default: %s" % default_dir,
                        default=default_dir)
    parser.add_argument("-u", "--user", help="OpenERP/Odoo user. Default: admin", default="admin")
    parser.add_argument("-p", "--password", help="OpenERP/Odoo user password. Default: admin",
                        default="admin")
    parser.add_argument("-s", "--host", help="OpenERP/Odoo host. Default: localhost",
                        default="localhost")
    parser.add_argument("-P", "--port", help="Port OpenERP/Odoo is listening. Default: 8069",
                        default=8069)
    parser.add_argument("-b", "--db", help="OpenERP/Odoo database to use. Required!",
                        required=True)

    options = parser.parse_args()

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s")
    logfile = options.logfile
    if logfile is None:
        streamH = logging.StreamHandler(sys.stdout)
    else:
        streamH = logging.FileHandler(logfile)
    streamH.setFormatter(formatter)
    logger.addHandler(streamH)
    logger.info("Started")

    odoo = OdooInstance(
        logger,
        db=options.db,
        user=options.user,
        password=options.password,
        host=options.host,
        port=options.port,
    )
    odoo.connect_to_odoo()

    if odoo.is_connected:
        event_handler = EventHandler(
            odoo=odoo,
            logger=logger,
            dir_to_watch=options.watch_dir,
            regex=options.regex,
            delimiter=options.delimiter,
        )
        # start handler loop
        event_handler.notifier.loop()
    else:
        logger.critical("Can't connect to odoo")
        exit(1)
