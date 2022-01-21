
Data logger for Govee H5174 and H5179
====

Uses [bleak bluetooth](https://bleak.readthedocs.io/en/latest/) library to scan for and decode announcements from [Govee bluetooth temperature and humidity](https://uk.govee.com/collections/thermo-hydrometer) probes.

The sensors publish an announcement periodically, and also on change.


Communication protocol - HS179
----

Three 'channels' used: `494e5445-4c4c-495f-524f-434b535f2011`, `xx2012` and `xx2013`.

Channel `494e5445-4c4c-495f-524f-434b535f2011` is used to query firmware and software versions. Client sends fixed length messages with a byte-wise XOR checksum. Replies are the same length and checksum scheme, mostly null-terminated strings:

    Jan 12 09:42:58                                                                  check byte
        WR > 3310 C693 A101 0000 0000 0000 0000 0000 0000 00D6    set clock?  33^10^C6^93^A1^01 = D6
        VN < 3310 0000 0000 0000 0000 0000 0000 0000 0000 0023    set ok.     33^10 = 23

        WR > AA08 0000 0000 0000 0000 0000 0000 0000 0000 00A2    ?  AA^08 = A2
        VN < AA08 5800 0000 0000 0000 0000 0000 0000 0000 00FA    ?  AA^08^58 = FA

        WR > AA0D 0000 0000 0000 0000 0000 0000 0000 0000 00A7      AA^0D = A7
        VN < AA0D 312E 3030 2E30 3200 0000 0000 0000 0000 0094    "1.00.02" hardware version

        WR > AA0E 0000                                    00A4
        VN < AA0E 312E 3032 2E30 3030 0000 0000 0000 0000 0097    "1.02.00" firmware version

        WR > AA09                                         00A3
        VN < AA09 00FF 0000 0000 0000 0000 0000 0000 0000 005C    ?

        WR > AA21                                           8B
        VN < AA21 312E 3030 2E31 3300 0000 0000 0000 0000 00B8    "1.00.13" < ? version

        WR > AA20 0000 0000 0000 0000 0000 0000 0000 0000 008A      AA^20 = 8A
        VN < AA20 312E 3030 2E30 3100 0000 0000 0000 0000 00BA    "1.00.01" < ? version

        WR > A103 B100 0000 0000 0000 0000 0000 0000 0000 0013
        VN < A103 B100 0000 0000 0000 0000 0000 0000 0000 0013    ?


Real-time temperature readings are send in annoucement broadcasts

Historical replay uses two channels: make requests on xx2012 and receive readings on xx2013.
Data is indexed by a timestamp, which is `UNIX timestamp / 60`.
Most results rows have 4 entries, some have 3 with the first 4 bytes being 0xFFFFFFFF

    handle 0x002e    (xxxx2012)

        Jan 12th 2022 09:42:58 => unix timestamp
                 1641980578   61DEA2A2
           /60     27366342   01A193C6
        byteswap              C693a101 - matches


        request channel for bulk downloads
        WR > 0x0000 E690 A101 C693 A101               start time, end time
                      E690 A101  = 27365606 (x60) = 1641936360 = Tue Jan 11 2022 21:26:00 GMT+0000
                      C693 A101  = 27366342 (x60) = 1641980520 = Wed Jan 12 2022 09:42:00 GMT+0000

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

Communication protocol - H5174
----

Setting clock:


    Jan 12th 2022 09:42:58
        WR > 0x3310 C693 A101 ...
        VN < 0x3310 ....

    Jan 12th 2022 09:43:00
        WR > 0x3310 C793 A101 0000 0000 0000 0000 0000 0000 00D7
        VN < 0x3310 0000

        WR > 0xAA08 0000
        VN < 0xAA08 6400 0000   different to H5179, unsure meaning

        AA0D - same
        AA0E - same



Write request to `xx2012`:

        WR > 0xAA01 0000 0000 0000 0000 0000 0000 0000 0000 00AB   ??
        VN < 0xAA01 0792 1292 6400 0000 0000 0000 0000 0000 00CA

        WR > 0x3302 0000 ...    unsure meaning, all zero
        VN < 0x3302 0000 ....

        WR > 0x3301 1c9b 0000 0000 0000 0000 0000 0000 0000 00B5   request index from 1c9b to 0000
        VN < 0x3301 0000 0000 0000 0000 0000 0000 0000 0000 0032   download starting

Sometimes the index range end is non-zero (7081-0001):

        WR > 0x3301 7081 0001 0000 0000 0000 0000 0000 0000 00c2


Bulk VNs recieved on `xx2013`, then:

        VN < 0xEE01 04C5 0000 0000 0000 0000 0000 0000 0000 00xx   download complete

    another time:
        VN < 0xee01 0d8b 0000 0000 0000 0000 0000 0000 0000 0069   download complete


     later 09:43:04
        WR > 0xAA01 0000 0000 0000 0000 0000 0000 0000 0000 00AB   ?
        VN < 0xAA01 0791 1282 6400 0000 0000 0000 0000 0000 00C9
                       ^   ^                                        changed
     later 09:43:06
        WR > 0xAA01 0000 0000 0000 0000 0000 0000 0000 0000 00AB
        VN < 0xAA01 0792 1279 6400 0000 0000 0000 0000 0000 00      ? current reading maybe

     later 09:43:10
        WR > 0xAA01 0000 0000 0000 0000 0000 0000 0000 0000 00AB
        VN < 0xAA01 0790 1280 6400 0000 0000 0000 0000 0000 00      ? current reading maybe

Bulk data

        VN < 0x1C2F 02D8 6402 D864 02D8 6402 d864 02d8 6402 d864    index + 6 data readings
                    1111 1122 2222 3333 3344 4444 5555 5566 6666
        VN < 0x1C29                                                 index now 6 previous

Usually payload rows have 6 entries, very rarely 0xFFFFFF values occur for multiple readings and the index
moves by fewer than expected. Suspected FIFO buffer underun in the device:

    index 3-byte temp/humidity values (humidity=t%1000, temp=t/1000)
    20838 t0=190473 t1=189473 t2=189474 t3=189474 t4=189474 t5=189475
    20832 t0=189475 t1=188475 t2=188476 t3=188476 t4=188476 t5=188477
    20826 t0=188477 t1=188477 t2=187477 t3=187478 t4=187478 t5=186479
    20820 t0=186479 t1=186479 t2=186479 t3=186480 t4=186480 t5=185480
    20814 t0=185481 t1=16777215 t2=16777215 t3=16777215 t4=16777215 t5=16777215  <== values skipped
    20813 t0=185481 t1=185481 t2=184481 t3=184482 t4=184482 t5=184482
    20807 t0=184483 t1=184483 t2=183483 t3=183484 t4=183484 t5=183486
    20801 t0=183487 t1=183486 t2=183488 t3=183487 t4=182487 t5=182488
    20795 t0=182488 t1=182488 t2=182488 t3=182488 t4=181488 t5=181488


The end of a download can skip values too, ie:

       18 t0=189433 t1=189434 t2=189434 t3=189435 t4=189435 t5=189436
       12 t0=188437 t1=188437 t2=188437 t3=188437 t4=188438 t5=188438
        6 t0=188439 t1=188439 t2=188439 t3=188439 t4=188440 t5=188440
        0 t0=188440 t1=16777215 t2=16777215 t3=16777215 t4=16777215 t5=16777215
    VR < handle=20 data=ee010709000000000000000000000000000000e1
    Download complete


With thanks to
----

Blog post https://wimsworld.wordpress.com/2020/07/11/govee-h5075-and-h5074-bluetooth-low-energy-and-mrtg/

Data download code protype at https://github.com/wcbonner/GoveeBTTempLogger/issues/8


