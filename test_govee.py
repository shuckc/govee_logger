import pytest
from govee_logger import stripnull, gv_rx_chk, gv_tx_chk, Govee_H5179, Govee_H5174
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice

def test_stripnull():
    assert stripnull(b"\x00\x00") == ""
    assert stripnull(b"\x31\x32\x00\x00") == "12"
    assert stripnull(b"\x31\x32\x20\x00") == "12 "

def test_gvchk():
    # gvchk tests and returns with checksum removed, else raises ValueError
    assert gv_rx_chk(bytes.fromhex("AA0D0000000000000000000000000000000000A7")) == bytes.fromhex("AA0D0000000000000000000000000000000000")

    with pytest.raises(ValueError, match="Incorrect checksum.*"):
        gv_rx_chk(bytes.fromhex("AA0D0000000000000000000000000000000000A6"))

    with pytest.raises(ValueError, match="Incorrect checksum.*"):
        gv_rx_chk(bytes.fromhex("AA0E0000000000000000000000000000000000A7"))

    with pytest.raises(ValueError, match=".*got 19 bytes.*"):
        gv_rx_chk(bytes.fromhex("AA0D00000000000000000000000000000000A6"))

    assert gv_tx_chk(b"") == bytes.fromhex("0000000000000000000000000000000000000000")
    assert gv_tx_chk(bytes.fromhex("AA0D")) == bytes.fromhex("AA0D0000000000000000000000000000000000A7")

    with pytest.raises(ValueError, match=".*got 20 bytes.*"):
        gv_tx_chk(bytes.fromhex("AA0D0000000000000000000000000000000000A7"))


def test_h5179():
    device = BLEDevice(address='E3:32:80:C1:E0:E2', name='Govee_H5179_E0E2')
    advertisement = AdvertisementData(local_name='Govee_H5179_E0E2',
        manufacturer_data={34817: b'\xec\x00\x01\x01\xea\x06\xd6\x15X'},
        service_uuids=['0000180a-0000-1000-8000-00805f9b34fb', '0000fef5-0000-1000-8000-00805f9b34fb', '0000ec88-0000-1000-8000-00805f9b34fb'])

    assert not Govee_H5174.accept(device, advertisement)
    assert Govee_H5179.accept(device, advertisement)

    gh5179 = Govee_H5179(device, advertisement)
    assert gh5179.advertisement(advertisement) == {'bat': 88, 'humid': 55.9, 'temp': 17.7}


def test_h5174():
    device = BLEDevice(address='A4:C1:38:86:6B:E0', name='GVH5174_6BE0')
    advertisement = AdvertisementData(local_name='GVH5174_6BE0',
        manufacturer_data={1: b'\x01\x01\x02\xf7\xd6d', 76: b'\x02\x15INTELLI_ROCKS_HWPu\xf2\xff\xc2'},
        service_uuids=['0000ec88-0000-1000-8000-00805f9b34fb'])

    assert not Govee_H5179.accept(device, advertisement)
    assert Govee_H5174.accept(device, advertisement)

    gh5174 = Govee_H5174(device, advertisement)
    assert gh5174.advertisement(advertisement) == {'bat': 100, 'humid': 51.8, 'temp': 19.4}

