import struct

# <class '__main__.Govee_H5174'>, A4:C1:38:86:6B:E0: GVH5174_6BE0
bs = [
    b"\x01\x01\x032Sd",
    b"\x01\x01\x032Vd",
    b"\x01\x01\x032Od",
    b"\x01\x01\x032Td",
    b"\x01\x01\x03.hd",
    b"\x01\x01\x032Rd",
    b"\x01\x01\x032Qd",
    b"\x01\x01\x032Zd",
    b"\x01\x01\x032Xd",
    b"\x01\x01\x032\\d",
    b"\x01\x01\x03.gd",
    b"\x01\x01\x032Pd",
]


def print_bs(bs):
    print("bs values are")
    for b in bs:
        assert b[0:2].hex() == "0101"
        (ds,) = struct.unpack(">i", b"\x00" + b[2:5])
        temp = (ds // 1000) / 10
        humid = (ds % 1000) / 10
        print(f" temp={temp} humid={humid} bat={b[5]}%")


print_bs(bs)
