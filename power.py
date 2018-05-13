# Python library for Rohm Wi-SUN communication module BP35A1
#
# Copyright (c) 2016, Atsushi Yokoyama, Firmlogics (http://flogics.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the <organization> nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT
# HOLDER> BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

TTY = '/dev/ttyUSB0'
# TTY = '/dev/tty.usbserial-XXXXXXXX'
B_ROUTE_AUTH_ID = '00000000000000000000000000000000'
B_ROUTE_AUTH_PASSWD = 'SECRETSECRET'
HIDE_ADDR = False

DEBUG = False

def init():
    from wisun import WiSUN

    w = WiSUN(ttyname=TTY, rate_bps=115200, auth_id=B_ROUTE_AUTH_ID,
              auth_pw=B_ROUTE_AUTH_PASSWD, verbose=True, debug=True,
              hide_addr=HIDE_ADDR, logname="log.txt")

    if w.read_from_cachefile():
        print "Cache file found."
    else:
        print "Cache file not found.  Scanning nodes."
        w.scan(retry=-1)

    if w.connect() == None:
        print "Cache file may be out-of-date.  Re-scanning nodes."
        w.scan(retry=-1)
        w.connect()

    return w

def main():
    import os
    import sys
    import time
    from wisun import WiSUN

    w = init()

    ct_noreply = 0
    tid = 0
    while True:
        w.echonet_send(tid, WiSUN.ESV_Get, WiSUN.EPC_SHUNJI_DENRYOKU)
        s = w.echonet_recv(tid, WiSUN.ESV_Reply, WiSUN.EPC_SHUNJI_DENRYOKU)
        if s:
            ct_noreply = 0
            power = s[-8:]
            print "%s: Power = %d [W]" % (time.strftime("%Y/%m/%d %H:%M:%S"),
                                          int(power, 16))
            sys.stdout.flush()
            os.system("rrdtool update $HOME/wisun/db/wisun_2.rrd N:%f" % \
                      int(power, 16))
            time.sleep(1)
        else:
            print "No reply"
            ct_noreply += 1
            if ct_noreply >= 10:
                w = init()
                ct_noreply = 0

        tid += 1
        if (tid > 0xffff):
            tid = 0

if __name__ == "__main__":
    main()
