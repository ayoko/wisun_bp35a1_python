# wisun_bp35a1_python
Python library for Rohm Wi-SUN communication module BP35A1

Notice
------

This software is usable in Japan only.

Requirements
------------

   * Python 2.7 or later (not Python 3)
   * Python YAML
   * B-Route authentication information (http://www.tepco.co.jp/pg/consignment/liberalization/smartmeter-broute.html)
   * Rohm BP35A1 communication module and UART bridge to your PC (or Raspberry Pi)

Usage
-----

Change followings in power.py.

   * TTY (tty name)
   * B_ROUTE_AUTH_ID (B-Route authentication ID)
   * B_ROUTE_AUTH_PASSWD (B-Route authentication password)

Run python power.py.
