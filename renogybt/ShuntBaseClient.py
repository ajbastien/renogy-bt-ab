import asyncio
import configparser
import logging
import traceback
from .BaseClient import BaseClient
from .BLEManager import BLEManager
from .Utils import bytes_to_int, crc16_modbus, int_to_bytes

# Base class that works with all Renogy family devices
# Should be extended by each client with its own parsers and section definitions
# Section example: {'register': 5000, 'words': 8, 'parser': self.parser_func}

class ShuntBaseClient(BaseClient):
    def __init__(self, config):
        super().__init__(config)
        
        self.G_NOTIFY_CHAR_UUID = "0000c411-0000-1000-8000-00805f9b34fb"
        self.G_WRITE_SERVICE_UUID = ""  # RMTShunt sends all data over notify to any connected device
        self.G_WRITE_CHAR_UUID = ""  # RMTShunt sends all data over notify to any connected device
        self.G_READ_TIMEOUT = 30 # (seconds)

    async def on_data_received(self, response):
        if self.read_timeout and not self.read_timeout.cancelled(): self.read_timeout.cancel()
        operation = bytes_to_int(response, 1, 1)

        if operation == 87: # notify operation for Shunt300
            #logging.info(f"ShuntBaseClient.on_data_received: response for notify operation {self.section_index} {len(self.sections)}")
            if (self.section_index < len(self.sections) and
                self.sections[self.section_index]['parser'] != None and
                self.sections[self.section_index]['words'] == len(response)):
                # parse and update data
                self.data = self.sections[self.section_index]['parser'](response)
                self.__safe_callback(self.on_data_callback, self.data, self.config)
        else:
            logging.warning("on_data_received: unknown operation={}".format(operation))

    def __safe_callback(self, calback, param, param2=None):
        if calback is not None:
            try:
                if param2 is None:
                    # If only one parameter is passed, call the callback with just that parameter
                    calback(self, param)
                else:
                    # If two parameters are passed, call the callback with both
                    calback(self, param, param2)
            except Exception as e:
                logging.error(f"__safe_callback => exception in callback! {e}")
                traceback.print_exc()
