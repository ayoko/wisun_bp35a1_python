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

def timestr():
    """Return a localtime string"""
    import time
    return time.strftime("%Y/%m/%d %H:%M:%S")

class WiSUN:
    """WiSUN Driver and Library Class"""

    DEFAULT_TIMEOUT = 10    # seconds
    CACHE_FILE_NAME = "wisun_cache.yaml"

    UDP_PORT = 3610
    EHD1 = 0x10
    EHD2 = 0x81
    EOJ_smart_meter = (0x02, 0x88, 0x01)
    EOJ_controller = (0x05, 0xff, 0x01)
    ESV_Get = 0x62
    ESV_Reply = 0x72
    
    EPC_KEISU = 0xd3
    EPC_SHUNJI_DENRYOKU = 0xe7

    def _cmd(self, s):
        """Issue a command to the module

        s -- command string to issue
        """
        self.tty.write(s + '\r')

    def _log(self, s):
        """Log message"""
        if self.logfile:
            self.logfile.write(timestr() + ' ' + s + '\n')
            self.logfile.flush()

    def _diag(self, s, logonly=False):
        """Print diagnostic message"""
        if self.verbose and not logonly:
            print '#', s
        self._log(s)

    def _expect(self, exp=None, timeout=DEFAULT_TIMEOUT):
        """
        Wait for string 'exp' from module

        timeout -- timeout in seconds (None: no-timeout)
        """
        import re
        import time

        start_time = time.time()
        while timeout == None or time.time() < start_time + timeout:
            s = self.tty.readline().rstrip()
            if len(s) > 0:
                if self.debug:
                    print '"%s"' % (s)
                    self._log('"%s"' % (s))
                m = re.match(exp, s)
                if m:
                    return m
        else:
            return None

    def _write_to_cachefile(self):
        """Write self ofject contents into YAML file"""
        import yaml
        if self.cachefile_name == None:
            return None

        s = yaml.dump(self, Dumper=yaml.Dumper)
        f = open(self.cachefile_name, 'w')
        f.write(s)
        f.close()

    def __init__(self, ttyname=None, rate_bps=115200, auth_id=None,
                 auth_pw=None, cachefile_name=CACHE_FILE_NAME,
                 verbose=False, debug=False, hide_addr=False,
                 logname=None):
        """
        Open tty for later operations

        auth_id  -- B-Route Authentication ID
        auth_pow -- B-Route Authentication Password
        """
        import re
        import serial
        import time
        self.addr = None
        self.cachefile_name = cachefile_name
        self.channel = None
        self.debug = debug
        self.hide_addr = hide_addr
        self.dest_ip = None
        self.logfile = None
        self.lqi = None
        self.my_ip = None
        self.pan_id = None
        self.verbose = verbose

        # timeout as 1 second looks good enough
        self.tty = serial.Serial(ttyname, rate_bps, timeout=1)

        if logname:
            self.logfile = open(logname, 'a')

        while True:
            self._diag('Issuing SKRESET')
            self._cmd("SKRESET")
            self._expect(r'OK')
            time.sleep(0.1)         # Fail safe (may not be required)

            self._diag('Issuing ROPT')
            self._cmd("ROPT")
            self._expect(r'ROPT')

            s = self.tty.read(5)
            self.tty.read()         # Ignore other buffered resonses

            m = re.match(r'OK (\d+)|FAIL', s)
            if m and m.group(0)[0:3] == 'OK ':
                self._diag('ROPT reply found')
                break
            time.sleep(1)
    
        if m.group(1) == '01':
            self._diag('Wi-SUN module is in ASCII mode')
        else:
            self._diag('Wi-SUN module is in BINARY mode')
            self._cmd("WOPT 01")
            self._expect(r'OK')
            self._diag('EEPROM update done')

        self._cmd("SKSETPWD %X %s" % (len(auth_pw), auth_pw))
        m = self._expect(r'OK')
        self._cmd("SKSETRBID %s" % (auth_id))
        m = self._expect(r'OK')

        return None

    def scan(self, retry=-1, gencache=True):
        """
        Scan nodes and return found node information

        retry    -- number of retries (-1: retrying forever)
        gencache -- generate cache file if True
        """
        self.channel = None

        while not self.channel:
            self._diag('Scanning nodes')
            self._cmd("SKSCAN 2 FFFFFFFF 6")
            m = self._expect(r' *Channel:(\w+)|EVENT 22', timeout=60)
            if m and m.group(0)[0:5] != 'EVENT':
                self.channel = m.group(1)
                self._diag("Channel = %s" % (self.channel))
            else:
                if retry < 0:
                    continue
                else:
                    retry -= 1
                    if retry >= 0:
                        continue
                    else:
                        return None
    
        m = self._expect(r' *Pan ID:(\w+)')
        self.pan_id = m.group(1)
        if not self.hide_addr:
            self._diag("PAN ID = %s" % (self.pan_id))

        m = self._expect(r' *Addr:(\w+)')
        self.addr = m.group(1)
        if not self.hide_addr:
            self._diag("Address = %s" % (self.addr))

        m = self._expect(r' *LQI:(\w+)')
        self.lqi = m.group(1)
        self._diag("LQI = %s" % (self.lqi))

        self._expect(r'EVENT 22')

        if gencache:
            self._write_to_cachefile()

        return self.channel, self.pan_id, self.addr, self.lqi

    def read_from_cachefile(self):
        """Read some object values from YAML file"""
        import yaml
        if self.cachefile_name == None:
            return None

        try:
            f = open(self.cachefile_name, 'r')
            d = f.read()
            f.close()
            v = yaml.load(d)
            self.channel = v.channel
            self.pan_id = v.pan_id
            self.addr = v.addr
            return self
        except:
            return None

    def connect(self):
        """
        Connect to the node and return destination IP address
        """
        if self.channel == None:
            return None

        self._cmd("SKSREG S2 %s" % (self.channel))
        self._expect(r'OK')
        self._cmd("SKSREG S3 %s" % (self.pan_id))
        self._expect(r'OK')

        self._cmd("SKLL64 %s" % (self.addr))
        m = self._expect(r'[0-9A-F:]+')
        self.dest_ip = m.group(0)
        if not self.hide_addr:
            self._diag("Dest IPv6 = %s" % (self.dest_ip))
    
        connected = False
        self._cmd("SKJOIN %s" % (self.dest_ip))
        while not connected:
            m = self._expect(r'EVENT (\w+)')
            if m.group(1) == '25':
                connected = True
            elif m.group(1) == '24':
                return None
    
        self._cmd("SKINFO")
        m = self._expect(r'EINFO *([0-9A-F:]+)')
        self.my_ip = m.group(1)
    
        if not self.hide_addr:
            self._diag("My IPv6 = %s" % (self.my_ip))

        self._diag('Wi-SUN connected')

        return self.dest_ip
    
    def echonet_send(self, tid, esv, epc):
        """
        Send a message in Echonet protocol format

        tid -- Transaction ID
        esv -- Echonet Service Code
        epc -- Echonet Property Code
        """
        import struct
        if self.dest_ip == None:
            return None
    
        tid = tid % 0x10000
        body = struct.pack('!BBHBBBBBBBBBB',
            WiSUN.EHD1,
            WiSUN.EHD2,
            tid,
            WiSUN.EOJ_controller[0],
            WiSUN.EOJ_controller[1],
            WiSUN.EOJ_controller[2],
            WiSUN.EOJ_smart_meter[0],
            WiSUN.EOJ_smart_meter[1],
            WiSUN.EOJ_smart_meter[2],
            esv,
            1,
            epc,
            0)
    
        header = 'SKSENDTO 1 %s %04X 1 %04X ' % \
                 (self.dest_ip, WiSUN.UDP_PORT, len(body))
        self.tty.write(header)
        self.tty.write(body)
        self.tty.write('\r')
    
    def echonet_recv(self, tid, esv, epc, timeout=5):
        """
        Receive a message in Echonet protocol format

        tid -- Transaction ID
        esv -- Echonet Service Code
        epc -- Echonet Property Code
        timeout -- timeout (seconds)
        """
        import re
        if self.dest_ip == None:
            return None
    
        tid = tid % 0x10000
        msg = '(%02X%02X%04X............%02X01%02X\w+)' % \
              (WiSUN.EHD1, WiSUN.EHD2, tid, esv, epc)
        expstr = r'ERXUDP %s %s %04X %04X [0-9A-F]+ 1 (\w+) %s' % \
                 (self.dest_ip, self.my_ip, WiSUN.UDP_PORT, WiSUN.UDP_PORT, msg)
        self._diag("expecting '%s'" % (expstr), logonly=True)
    
        m = self._expect(expstr, timeout)
        if m:
            return m.group(2)
        else:
            return None
