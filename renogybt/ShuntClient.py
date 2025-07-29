import asyncio
import logging
import time
from .ShuntBaseClient import ShuntBaseClient
from .Utils import bytes_to_int, parse_temperature

# Read and parse Smart Shunt 300

FUNCTION = {
    3: "READ",
    6: "WRITE"
}

CHARGING_STATE = {
    0: 'deactivated',
    1: 'activated',
    2: 'mppt',
    3: 'equalizing',
    4: 'boost',
    5: 'floating',
    6: 'current limiting'
}

LOAD_STATE = {
  0: 'off',
  1: 'on'
}

BATTERY_TYPE = {
    1: 'open',
    2: 'sealed',
    3: 'gel',
    4: 'lithium',
    5: 'custom'
}


class ShuntClient(ShuntBaseClient):
    def __init__(self, config, on_data_callback=None, on_error_callback=None):
        super().__init__(config)

        self.throttleTimerLen = self.config['data'].getint('poll_interval')
        self.throttleTimer = time.perf_counter() - self.config['data'].getint('poll_interval') - 1
        self.on_data_callback = on_data_callback
        self.on_error_callback = on_error_callback
        self.data = {}
        self.sections = [
            {'register': 256, 'words': 110, 'parser': self.parse_shunt_info}
        ]
        self.set_load_params = {'function': 6, 'register': 266}

        logging.info(f'ShuntClient.__init__ {self.G_NOTIFY_CHAR_UUID} {self.G_WRITE_SERVICE_UUID} {self.G_WRITE_CHAR_UUID} {self.G_READ_TIMEOUT}')

    async def on_data_received(self, response):
        operation = bytes_to_int(response, 1, 1)
        # The Smart Shunt sends many data requests, so we need to check if the client is running 
        if self.is_running and (time.perf_counter() - self.throttleTimer) > self.throttleTimerLen:  
            logging.info(f'ShuntClient.on_data_received {operation} {self.is_running} {time.perf_counter() - self.throttleTimer}')
            self.throttleTimer = time.perf_counter()

            if operation == 6: # write operation
                self.parse_set_load_response(response)
                self.on_write_operation_complete()
                self.data = {}
            else:
                # read is handled in base class
                await super().on_data_received(response)

    def on_write_operation_complete(self):
        logging.info("on_write_operation_complete")
        if self.on_data_callback is not None:
            self.on_data_callback(self, self.data)

    def set_load(self, value = 0):
        logging.info("setting load {}".format(value))
        request = self.create_generic_read_request(self.device_id, self.set_load_params["function"], self.set_load_params["register"], value)
        asyncio.create_task(self.ble_manager.characteristic_write_value(request))

    def parse_device_info(self, bs):
        data = {}
        data['function'] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data['model'] = (bs[3:17]).decode('utf-8').strip()
        self.data.update(data)

    def parse_device_address(self, bs):
        data = {}
        data['device_id'] = bytes_to_int(bs, 4, 1)
        self.data.update(data)

    def parse_shunt_info(self, bs):
        data = {}
        #temp_unit = self.config['data']['temperature_unit']
        data['charge_battery_voltage'] = bytes_to_int(bs, 25, 3, scale = 0.001) # 0xA6 (#1)
        data['starter_battery_voltage'] = bytes_to_int(bs, 30, 2, scale = 0.001) # 0xA6 (#2)
        data['discharge_amps'] = bytes_to_int(bs, 21, 3, scale = 0.001, signed=True) # 0xA4 (#1)
        data['discharge_watts'] = round((data['charge_battery_voltage'] * data['discharge_amps']), 2)
        data['temperature_sensor_1'] = 0.00 if bytes_to_int(bs, 67, 1) == 0 else bytes_to_int(bs, 66, 3, scale = 0.001) # 0xAD (#3)
        data['temperature_sensor_2'] = 0.00 if bytes_to_int(bs, 71, 1) == 0 else bytes_to_int(bs, 70, 3, scale = 0.001) # 0xAD (#4)
        # unknown values:
        # - time_remaining
        # - discharge_duration
        # - consumed_amp_hours
        self.data.update(data)
        # logging.debug(msg=f"DATA: {self.data}")
        logging.info(f'parse_shunt_info bs hex => {bs.hex()}')
        return data
        