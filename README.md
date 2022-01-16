
Data logger for Govee H5174 and H5179
====

Uses bleak bluetooth library to scan for and decode announcements from Govee bluetooth temperature and humidity probes.

The sensors publish an announcement periodically, and also on change.


Communication protocol - HS179
----

Three 'channels' used: `494e5445-4c4c-495f-524f-434b535f2011`, `xx2012` and `xx2013`.

Channel `494e5445-4c4c-495f-524f-434b535f2011` is used to query firmware and software versions. Client sends fixed length messages with a byte-wise XOR checksum. Replies are the same length and checksum scheme, mostly null-terminated strings:

                                                                  check byte
        WR > 3310 C693 A101 0000 0000 0000 0000 0000 0000 00D6      33^10^C6^93^A1^01 = D6
        VN < 3310 0000 0000 0000 0000 0000 0000 0000 0000 0023    ? 33^10 = 23

        WR > AA08 0000 0000 0000 0000 0000 0000 0000 0000 00A2      AA^08 = A2
        VN < AA08 5800 0000 0000 0000 0000 0000 0000 0000 00FA      AA^08^58 = FA

        WR > AA0D 0000 0000 0000 0000 0000 0000 0000 0000 00A7      AA^0D = A7
        VN < AA0D 312E 3030 2E30 3200 0000 0000 0000 0000 0094    "1.00.02"

        WR > AA0E 0000                                    00A4
        VN < AA0E 312E 3032 2E30 3030 0000 0000 0000 0000 0097    "1.02.00"

        WR > AA09                                         00A3
        VN < AA09 00FF 0000 0000 0000 0000 0000 0000 0000 005C    ?

        WR > AA21                                           8B
        VN < AA21 312E 3030 2E31 3300 0000 0000 0000 0000 00B8    "1.00.13"

        WR > AA20 0000 0000 0000 0000 0000 0000 0000 0000 008A      AA^20 = 8A
        VN < AA20 312E 3030 2E30 3100 0000 0000 0000 0000 00BA    "1.00.01" < firmware version

        WR > A103 B100 0000 0000 0000 0000 0000 0000 0000 0013
        VN < A103 B100 0000 0000 0000 0000 0000 0000 0000 0013    ?


Real-time temperature readings are send in annoucement broadcasts

Historical replay uses two channels: make requests on xx2012 and receive readings on xx2013.
Data is indexed by a timestamp, which is `UNIX timestamp / 60` with a skew of 0xA65
Most results rows have 4 entries, some have 3 with the first 4 bytes being 0xFFFFFFFF

    handle 0x002e    (xxxx2012)

        Jan 10th 2022 13:21:56 => unix timestamp
                 1641820916   61DC32F4
           /60     27363681   01A18961 !!
        byteswap              6189 A101

        msg 3310              C693 a101
                            01a193c6
                            27363681
                            27366342  difference 0xA65 => 2661 minutes = 44.35 hours = 1.84 days ?



        request channel for bulk downloads
        WR > 0x0000 E690 A101 C693 A101               start time, end time
                      E690 A101  = 27365606 (x60) = 1641936360 = Tue Jan 11 2022 21:26:00 GMT+0000
                                      -2661 (x60) = 1641776700 = Mon Jan 10 2022 01:05:00 GMT+0000
                      C693 A101  = 27366342 (x60) = 1641980520 = Wed Jan 12 2022 09:42:00 GMT+0000
                                      -2661 (x60) = 1641820860 = Mon Jan 10 2022 13:21:00 GMT+0000
        VN < 0x00 before bulk data
        VN < 0x02 once the bulk download completes


    handle 0x0031    (xxxx2013)
        govee device returns bulk data as many Value Notifications
        VN <
        ...
        VN < E190 A101 280A C210 640A 7C10 960A 6810 640A 5E10
             ^^^^ ^^^^                                             index/timestamp
                       1111 1111 2222 2222 3333 3333 4444 4444     4 data values
                       26.00     26.60     27.10     26.60         temperature (/100)
                            42.90%    42.20%    42.00%    41.90%   humidity (/100)

        VN < DE90 A101 FFFF FFFF 320A C210 F609 3A11 A609 BC11
                       ^^^^ ^^^^    this record only has 3 values



With thanks to
----

Blog post https://wimsworld.wordpress.com/2020/07/11/govee-h5075-and-h5074-bluetooth-low-energy-and-mrtg/

Data download code protype at https://github.com/wcbonner/GoveeBTTempLogger/issues/8


