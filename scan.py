import asyncio
from bleak import BleakScanner, BleakClient
from datetime import datetime
import logging
import functools
import struct


def stripnull(data):
    data = data.rstrip(b'\0')
    return data.decode('UTF-8')

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

    async def get_meta(self):
        return {}

    async def do_download(self):
        return

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
        dx = advertisement.manufacturer_data.get(34817, None)
        if dx:
            assert dx[0:4].hex() == 'ec000101'
            temp, humid, bat = struct.unpack("<hhb", dx[4:])
            print(f"Govee H5179 mac={self.device.address} temp={temp/100} humid={humid/100} bat={bat}%")
            self.ads.add(dx)
            return {'temp': temp/100, 'humid': humid/100, 'bat': bat}
        return {}


    async def get_meta(self):
        client = BleakClient(self.device.address, timeout=30)
        await client.connect()
        umisc = '494e5445-4c4c-495f-524f-434b535f2011'
        meta = {}
        await client.start_notify(umisc, functools.partial(self.handler_2011, meta))
        await client.write_gatt_char(umisc, bytes.fromhex("AA2000000000000000000000000000000000008A"))
        await client.write_gatt_char(umisc, bytes.fromhex("AA0D0000000000000000000000000000000000A7"))
        await asyncio.sleep(0.5)
        await client.stop_notify(umisc)
        return meta

    def handler_2011(self, meta, handle, data):
        print(f"VR < handle={handle} data={data}")
        msgtype = data[0:2]
        value = data[2:-1] # dump checksum
        if msgtype == bytes.fromhex('AA20'):
            meta['firmware'] = stripnull(value)
        elif msgtype == bytes.fromhex('AA0D'):
            meta['hwver'] = stripnull(value)
        else:
            print("!! unknown response")


    async def do_download(self):
        print('starting download')
        client = BleakClient(self.device.address, timeout=30)
        res = await client.connect()
        ureq = '494e5445-4c4c-495f-524f-434b535f2012'
        ubulk = '494e5445-4c4c-495f-524f-434b535f2013'
        event = asyncio.Event()
        print('starting download 2')

        await client.start_notify(ubulk, functools.partial(self.handler_2013, None))
        await client.start_notify(ureq, functools.partial(self.handler_2012, event))
        tfrom = 27365606
        tto   = 27366342
        await client.write_gatt_char(ureq, struct.pack('<hII', 0, tfrom, tto))
        print(f'waiting for bulk download from {tfrom} to {tto}')
        await event.wait()

        await client.stop_notify(ureq)
        await client.stop_notify(ubulk)

    def handler_2012(self, finished, handle, data):
        # print(f"VR < handle={handle} data={data}")
        v, = struct.unpack("<b", data)
        if v == 2:
            print('download finished')
            finished.set()
        elif v == 0:
            print('download accepted')
        elif v == 1:
            print('Download request failed! (lower bound too low?)')
            finished.set()
        else:
            print(f'unknown download status: {v}')

    def handler_2013(self, results, handle, data):
        # print(f"VR < handle={handle} data={data}")
        index, t1, h1, t2, h2, t3, h3, t4, h4 = struct.unpack("<ihhhhhhhh", data)
        ts = datetime.fromtimestamp(index*60)
        if t1 == -1:
            print(f' {index} {ts} --          t1={t2/100} t2={t3/100} t3={t4/100}')
        else:
            print(f' {index} {ts} t1={t1/100} t2={t2/100} t3={t3/100} t4={t4/100}')


def detection_callback(checkers, known_devices, devq, device, advertisement_data):
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
            devq.put_nowait(kd)
    # nobody accepted - block future accept() calls?


async def main():
    checkers = [Govee_H5174, Govee_H5179]
    known_devices = []
    devq = asyncio.Queue()
    scanner = BleakScanner()
    detection_cb = functools.partial(detection_callback, checkers, known_devices, devq)
    scanner.register_detection_callback(detection_cb)

    t1 = asyncio.create_task(probe_devs(devq))

    await scanner.start()
    await asyncio.sleep(10.0)
    await scanner.stop()

    print("Stopped scanning, discovered the following:")
    for d in scanner.discovered_devices:
        print(d)

    devq.put_nowait(None)
    await t1

async def probe_devs(queue):
    print('bg worker')
    while True:
        try:
            d = await queue.get()
            if d is None:
                return
            print(f"interogating {d}")

            # print(d.ads)
            print(await d.get_meta())
            queue.task_done()
            print(await d.do_download())
        except Exception:
            logging.exception("ohno")

asyncio.run(main())


