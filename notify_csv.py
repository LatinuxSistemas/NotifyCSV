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
import logging
from multiprocessing import Process
import os
import re
import sys
import time
import traceback

import sh  # fades.pypi
from pyinotify import (IN_CLOSE_WRITE, IN_DELETE, IN_DELETE_SELF,  # fades.pypi
                       ProcessEvent, ThreadedNotifier, WatchManager)

import erppeek  # fades.pypi

PROGNAME = 'NotifyCSV'


class OdooInstance(object):
    """
    Manages connections to the Odoo server.
    """

    def __init__(self, logger, **connection_data):
        """
        Instanciate the Odoo manager.
        @param logger: a logger instance as returned by logging.getLogger.
        @param host: the host name or ip of the Odoo server.
        @type host: str.
        @param port: the port Odoo server listens.
        @type port: int.
        @param user: Odoo user for login.
        @type user: str.
        @param password: Odoo password for login.
        @type password: str.
        @param db: Odoo db.
        @type db: str.
        """
        self.logger = logger
        self._host = connection_data.pop("host")
        self._port = connection_data.pop("port")
        self.is_connected = False
        self.connection_data = connection_data
        self.prod_obj = None
        self._default_data = {
            "sale_ok": True,
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

    def connect_to_odoo(self):
        """
        Do connect. It will try to connect 100 times with a pause of 30 seconds each 10 tries
        """
        for j in range(1, 11):
            for i in range(1, 11):
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
                    break
                except ConnectionRefusedError:
                    self.logger.warning("Connection refused... retrying %s" % i)
                    time.sleep(3)
                    self.is_connected = False
                    continue

            if self.is_connected:
                break

            wait = 30
            self.logger.warning("Connection refused 5 times retrying in %d seconds" % wait)
            time.sleep(wait)
        return self.is_connected

    def create_products(self, products_data, filename=''):
        """
        Create products.
        @param products_data: list of dicts with fields required by product.product object.
        @param filename: name of the file currently being processed. Useful just for logging.
        @type filename: str.
        """
        for data in products_data:
            products = self.prod_obj.read([
                ("name", "=", data["name"]),
                ("default_code", "=", data["default_code"])
            ])
            if not products:
                data.update(self._default_data)
                product = self.prod_obj.create(data)
                self.logger.info("(%s) New product created: [%s] %s" % (filename,
                                                                        product.default_code,
                                                                        product.name))
            else:
                product = self.prod_obj.browse(products[0]["id"])
                self.logger.info("(%s) Product found: [%s] %s" % (filename, product.default_code,
                                                                  product.name))
                new_price = float(data["list_price"])
                if round(product.list_price, 3) != new_price:
                    self.logger.info("(%s) Update price: from %s to %s" % (filename,
                                                                           product.list_price,
                                                                           new_price))
                    product.write({"list_price": new_price})
        return True


class ProcessPool(object):
    """
    Manages process. Each CLOSE_WRITE event adds an open file to the pool of processes.
    """

    pool = {}

    def __init__(self, logger, odoo):
        """
        Instanciate the pool.
        @param logger: a logger instance as returned by logging.getLogger.
        @param odoo: the Odoo instance.
        """
        self.logger = logger
        self.odoo = odoo

    def loop(self):
        """
        It will loop forever and feed the Odoo instance
        """
        while True:
            # shallow copy of the lists in the dict to avoid RuntimeError.
            temporal_pool = dict(zip(self.pool.keys(), [v.copy() for v in self.pool.values()]))
            processes = []
            for filename, datadicts in temporal_pool.items():
                self.pool[filename].clear()
                self.logger.info("Start processing file: %s" % filename)
                process = Process(target=self.odoo.create_products, args=(datadicts, filename))
                processes.append(process)
                process.start()
                if not self.pool[filename]:
                    self.pool.pop(filename)
            for process in processes:
                process.join()
            del temporal_pool, processes
            time.sleep(10)


class EventHandler(ProcessEvent):
    """
    Main event handler.
    """

    def my_init(self, odoo, logger, dir_to_watch=None, regex='.*', delimiter='\t'):
        self.logger = logger
        self.logger.info("Starting event handler")
        self.odoo = odoo
        self.regex = regex
        self.delimiter = delimiter
        self._create_dir(dir_to_watch)
        self._fieldnames = ("name", "list_price", "default_code")

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
        When file is written to disk and closed
        """
        # pathname is full path and name is the path relative to the watched dir.
        pathname = event.pathname
        name = event.name
        self.logger.info("close write on file: %s" % pathname)
        if re.match(self.regex, name):
            self.logger.info("CSV file found: %s, let's parse it!" % pathname)
            with open(pathname, newline='') as csvfile:
                csvdicts = csv.DictReader(
                    csvfile,
                    fieldnames=self.fieldnames,
                    delimiter=self.delimiter,
                )
                csvdicts = list(csvdicts)
                ProcessPool.pool.setdefault(name, []).extend(csvdicts)
        return True


def main(**options):
    """
    Main function. It will create instances of Odoo Server, EventHandler, ThreadedNotifier and
    ProcessPool.
    """
    logger = logging.getLogger(PROGNAME)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s")
    logfile = options["logfile"]
    if logfile is None:
        streamH = logging.StreamHandler(sys.stdout)
    else:
        streamH = logging.FileHandler(logfile)
    streamH.setFormatter(formatter)
    logger.addHandler(streamH)
    logger.info("Started")

    odoo = OdooInstance(
        logger,
        db=options["db"],
        user=options["user"],
        password=options["password"],
        host=options["host"],
        port=options["port"],
    )
    odoo.connect_to_odoo()
    exit_code = 0
    if odoo.is_connected:
        count = 0
        while True:
            count += 1
            try:
                event_handler = EventHandler(
                    odoo=odoo,
                    logger=logger,
                    dir_to_watch=options["dir_to_watch"],
                    regex=options["regex"],
                    delimiter=options["delimiter"],
                )
                # start loop handler
                masks = IN_CLOSE_WRITE | IN_DELETE | IN_DELETE_SELF
                wm = WatchManager()
                wm.add_watch(event_handler.dir_to_watch, masks)
                notifier = ThreadedNotifier(wm, default_proc_fun=event_handler)
                notifier.start()
                pool = ProcessPool(logger, odoo)
                pool.loop()
            except (KeyboardInterrupt, EOFError):
                logger.info("\nReceived signal to exit! Goodbye")
                break
            except:
                logger.error("ERROR! \n%s" % traceback.print_exception(*sys.exc_info()))
            finally:
                if notifier:
                    notifier.stop()
                if count >= 50:
                    logger.error("ERROR! Too many tries, aborting!")
                    break
    else:
        logger.critical("Can't connect to odoo")
        exit_code = 1
        exit(exit_code)

if __name__ == '__main__':
    from argparse import ArgumentParser

    default_dir = os.path.join(os.environ['HOME'], "csv-input")
    parser = ArgumentParser(prog=PROGNAME)

    parser.add_argument("-d", "--delimiter", help="Specify field delimiter. Default: '\\t'",
                        default='\t')
    parser.add_argument("-r", "--regex", default='.+.[Cc][Ss][Vv]',
                        help=("Use this regex to match names in watched dir. Can be any valid "
                              "Python regex. Default: '^.+\.[cC][sS][vV]$'")
                        )
    parser.add_argument("-l", "--logfile", help="Log to this file")
    parser.add_argument("-w", "--dir-to-watch", help="Dir to watch. Default: %s" % default_dir,
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

    main(
        delimiter=options.delimiter,
        regex=options.regex,
        logfile=options.logfile,
        db=options.db,
        dir_to_watch=options.dir_to_watch,
        user=options.user,
        password=options.password,
        host=options.host,
        port=options.port
    )
