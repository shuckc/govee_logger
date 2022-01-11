import asyncio
from bleak import BleakScanner
import functools
import struct

class DeviceFilter():
    @staticmethod
    def accept(device, advertisement_data) -> bool:
        return False

    def advertisement(self, advertisement) -> None:
        pass

    def __init__(self, device, advertisement_data):
        self.device = device
        self.advertisement_data = advertisement_data
        self.ads = set()

    def __repr__(self):
        return f"{self.__class__}, {self.device}"

class Govee_H5174(DeviceFilter):
    # device has bluetooth
    # reads temperature and humidity
    @staticmethod
    def accept(device, advertisement_data) -> bool:
        name = advertisement_data.local_name
        return name is not None and name.startswith("GVH5174_")

    # AdvertisementData(local_name='GVH5174_6BE0',
    # manufacturer_data={1: b'\x01\x01\x02\xf7\xd6d', 76: b'\x02\x15INTELLI_ROCKS_HWPu\xf2\xff\xc2'},
    # service_uuids=['0000ec88-0000-1000-8000-00805f9b34fb'])
    def advertisement(self, advertisement):
        dx = advertisement.manufacturer_data[1]
        assert dx[0:2].hex() == '0101'
        ds, = struct.unpack(">i", b'\x00' + dx[2:5])
        temp = (ds//1000)/10
        humid = (ds%1000)/10
        print(f"Govee H5174 mac={self.device.address} temp={temp} humid={humid} bat={dx[5]}%")
        self.ads.add(dx)
        return {'temp': temp, 'humid': humid, 'bat': dx[5]}

class Govee_H5179(DeviceFilter):
    # device has Wifi, bluetooth,
    # temperature and humidity
    @staticmethod
    def accept(device, advertisement_data) -> bool:
        name = advertisement_data.local_name
        return name is not None and name.startswith("Govee_H5179_")

    # AdvertisementData(local_name='Govee_H5179_E0E2',
    # manufacturer_data={34817: b'\xec\x00\x01\x01\xea\x06\xd6\x15X'},
    # service_uuids=['0000180a-0000-1000-8000-00805f9b34fb', '0000fef5-0000-1000-8000-00805f9b34fb', '0000ec88-0000-1000-8000-00805f9b34fb'])
    def advertisement(self, advertisement):
        dx = advertisement.manufacturer_data[34817]
        assert dx[0:4].hex() == 'ec000101'
        temp, humid, bat = struct.unpack("<hhb", dx[4:])
        print(f"Govee H5179 mac={self.device.address} temp={temp/100} humid={humid/100} bat={bat}%")
        self.ads.add(dx)
        return {'temp': temp/100, 'humid': humid/100, 'bat': bat}

def detection_callback(scanner, checkers, known_devices, device, advertisement_data):
    # print(device.address, "RSSI:", device.rssi, advertisement_data)
    known_addr = set([kd.device.address for kd in known_devices])
    for kd in known_devices:
        if device.address == kd.device.address:
            kd.advertisement(advertisement_data)
            return

    for c in checkers:
        if c.accept(device, advertisement_data):
            print(device.address, "RSSI:", device.rssi, advertisement_data)

            kd = c(device, advertisement_data)
            print(kd)
            known_devices.append(kd)
            kd.advertisement(advertisement_data)
    # nobody accepted - block future accept() calls?


async def main():
    checkers = [Govee_H5174, Govee_H5179]
    known_devices = []
    scanner = BleakScanner()
    detection_cb = functools.partial(detection_callback, scanner, checkers, known_devices)
    scanner.register_detection_callback(detection_cb)

    await scanner.start()
    await asyncio.sleep(120.0)
    await scanner.stop()

    print("Stopped scanning, discovered the following:")
    for d in scanner.discovered_devices:
        print(d)

    print("listening for temperatures on the following:")
    for d in known_devices:
        print(d)
        print(d.ads)

asyncio.run(main())


