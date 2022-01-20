import pytest
from govee_logger import stripnull, gvchk


def test_stripnull():
	assert stripnull(b"\x00\x00") == ""
	assert stripnull(b"\x31\x32\x00\x00") == "12"
	assert stripnull(b"\x31\x32\x20\x00") == "12 "

def test_gvchk():
	# gvchk tests and returns with checksum removed, else raises ValueError
	assert gvchk(bytes.fromhex("AA0D0000000000000000000000000000000000A7")) == bytes.fromhex("AA0D0000000000000000000000000000000000")

	with pytest.raises(ValueError, match="Incorrect checksum.*"):
		gvchk(bytes.fromhex("AA0D0000000000000000000000000000000000A6"))

	with pytest.raises(ValueError, match="Incorrect checksum.*"):
		gvchk(bytes.fromhex("AA0E0000000000000000000000000000000000A7"))

	with pytest.raises(ValueError, match=".*got 19 bytes.*"):
		gvchk(bytes.fromhex("AA0D00000000000000000000000000000000A6"))

