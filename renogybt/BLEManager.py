import asyncio
import sys
from bleak import BleakClient, BleakScanner, BLEDevice
from logger_config import logger


DISCOVERY_TIMEOUT = 5 # max wait time to complete the bluetooth scanning (seconds)

class BLEManager:
    def __init__(self, mac_address, alias, on_data, on_connect_fail, write_service_uuid, notify_char_uuid, write_char_uuid):
        self.mac_address = mac_address
        self.device_alias = alias
        self.data_callback = on_data
        self.connect_fail_callback = on_connect_fail
        self.write_service_uuid = write_service_uuid
        self.notify_char_uuid = notify_char_uuid
        self.write_char_uuid = write_char_uuid
        self.write_char_handle = None
        self.device: BLEDevice = None
        self.client: BleakClient = None
        self.discovered_devices = []

    async def discover(self):
        mac_address = self.mac_address.upper()
        logger.info("Starting discovery...")
        self.discovered_devices = await BleakScanner.discover(timeout=DISCOVERY_TIMEOUT)
        logger.info("Devices found: %s", len(self.discovered_devices))

        for dev in self.discovered_devices:
            if dev.address != None and (dev.address.upper() == mac_address or (dev.name and dev.name.strip() == self.device_alias)):
                logger.info(f"Found matching device {dev.name} => {dev.address}")
                self.device = dev

    async def connect(self):
        if not self.device: return logger.error("No device connected!")

        logger.info(f'BLEManager.connect {self.notify_char_uuid} {self.write_service_uuid} {self.write_char_uuid}')

        self.client = BleakClient(self.device)
        try:
            await self.client.connect()
            logger.info(f"Client connection: {self.client.is_connected}")
            if not self.client.is_connected: return logger.error("Unable to connect")

            for service in self.client.services:
                for characteristic in service.characteristics:
                    if characteristic.uuid == self.notify_char_uuid:
                        logger.info(f"subscribing to notification {characteristic.uuid}")
                        await self.client.start_notify(characteristic,  self.notification_callback)
                    if self.write_char_uuid != "" and characteristic.uuid == self.write_char_uuid and service.uuid == self.write_service_uuid:
                        self.write_char_handle = characteristic.handle
                        logger.info(f"found write characteristic {characteristic.uuid}, service {service.uuid}")

        except Exception as e:
            logger.error(f"Error connecting to device {e}")
            self.connect_fail_callback(sys.exc_info())

    async def notification_callback(self, characteristic, data: bytearray):
        #logger.info("notification_callback")
        await self.data_callback(data)

    async def characteristic_write_value(self, data):
        if self.write_char_handle is not None:
            try:
                logger.info(f'writing to {self.write_char_uuid} {data}')
                await self.client.write_gatt_char(self.write_char_handle, bytearray(data), response=False)
                logger.info('characteristic_write_value succeeded')
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.info(f'characteristic_write_value failed {e}')
        else:
            logger.error(f'characteristic_write_value not called since write_char_handle is None')

    async def disconnect(self):
        if self.client and self.client.is_connected:
            logger.info(f"Exit: Disconnecting device: {self.device.name} {self.device.address}")
            await self.client.disconnect()
