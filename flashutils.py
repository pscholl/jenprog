from ftdi import *
from time import sleep
import sys

class Closure:
    def __init__(self, arg, func):
        self.arg = arg
        self.func = func

    def __call__(self, *args):
        val = self.func(self.arg, *args)
        if val < 0:
            raise Exception, "%s: %d"%(ftdi_get_error_string(self.arg), val)
        else:
            return val

class Ftdi:
    def __init__(self):
        self.context = ftdi_context()
        ftdi_init(self.context)

    def __call__(self, *args):
        print args

    def __getattr__(self, name):
        return Closure(self.context, eval("ftdi_%s"%name))

class Bootloader:
    def __init__(self):
        self.f = Ftdi()
        self.f.usb_open(0x0403, 0x6001)
        self.f.usb_reset()
        self.f.set_baudrate(38400)
        self.f.set_line_property(NONE, STOP_BIT_1, BITS_8)
        self.f.usb_purge_buffers()
        self.f.setrts(1)

        self.mac_region    = range(0x00000030, 0x00000038)
        self.lic_region    = range(0x00000038, 0x00000048)
        self.mac, self.lic = None, None
        self.isverbose     = None

    def verbose(self):
        self.isverbose = True

    def crc(self, arr, len):
        """ calculates the crc
        """
        crc = 0
        for i in range(0,len):
            crc ^= arr[i]
        return crc

    def set_mac(self, s):
        self.mac = []

        for i in range(0, len(s), 2):
            if s[i:i+2] != "0x":
                self.mac.append( int( s[i:i+2], 16 ) )

        assert len(self.mac)==len(self.mac_region),\
         "mac must be %i byte long"%len(self.mac_region)

    def set_license(self, s):
        self.lic = []

        for i in range(0, len(s), 2):
            if s[i:i+2] != "0x":
                self.lic.append( int( s[i:i+2], 16 ) )

        assert len(self.lic)==len(self.lic_region),\
         "license must be %i byte long"%len(self.lic_region)

    def talk(self, type, ans_type, addr=None, mlen=None, data=None):
        """ executes one speak-reply cycle
        type is message type sent to the chip
        *args is a list of optional arguments to the message
        ans is the anticipated answer type, if None returns immediatly after the message
        has been sent.

        throws an exception if the answer type is not the anticipiated one
        """
        msg_len = 3          # default len if no args are supplied

        if addr != None:
            msg_len += 4
        if mlen != None:
            msg_len += 2
        if data != None:
            msg_len += len(data)

        assert msg_len < 0xFF, "oversized msg, max is 256 bytes, yours is %i"%msg_len

        # pack optional args in
        msg    = cArray(msg_len)
        msg[0] = msg_len-1
        msg[1] = type
        i      = 2

        if addr != None:
            msg[i]   =  addr& 0x000000FF
            msg[i+1] = (addr& 0x0000FF00)>>8
            msg[i+2] = (addr& 0x00FF0000)>>16
            msg[i+3] =  addr>> 24
            i       += 4
        if mlen != None:
            msg[i]   =  mlen & 0x00FF
            msg[i+1] = (mlen & 0xFF00)>>8
            i       += 2
        if data != None:
            for d in data:
                try:
                    msg[i] = d
                except TypeError:
                    msg[i] = ord(d)
                i     += 1

        # add crc
        msg[i] = self.crc(msg, msg_len-1)
        assert msg[i] == self.crc(msg, msg_len-1), "%i != %i"%(msg[i], self.crc(msg, msg_len))

        str = ""
        for i in range(0,msg_len):
            str += "0x%x "%msg[i]

        if self.isverbose:
            sys.stderr.write(str)
            sys.stderr.write("\n")

        # construct answer storage
        if ans_type != None:
            ans_len = 0
            ans     = cArray(1)

            # send two times
            self.f.write_data(msg, msg_len)

            for i in (1,):
                while ans_len == 0:
                    ans_len = self.f.read_data(ans, 1)

                # okay we received the first byte of the answer,
                # which contains the length of the answer
                ans_len = ans[0]
                ans     = cArray(ans_len)

                # now read the answer
                read_len = self.f.read_data(ans, ans_len)
                assert read_len == ans_len, "%i != %i" % (read_len, ans_len)
                assert ans[0] == ans_type, "recvd: 0x%x, anticipiated: 0x%x" %( ans[0], ans_type )

                arr = []
                for i in range(1, ans_len-1): # skip length and crc field
                    arr.append( ans[i] )
                ans_len=0


            return arr

        else:
                self.f.write_data(msg, msg_len)

    def erase_flash(self):
        """ read mac and license key prior to erasing
        """
        if not self.mac:
            self.mac = self.read_mac()
        if not self.lic:
            self.lic = self.read_license()
        assert len(self.mac)==len(self.mac_region), "read mac addr too short"
        assert len(self.lic)==len(self.lic_region), "read license too short"

        assert self.talk( 0x07, 0x08 )[0] == 0, "erasing did not work"

    def read_mac(self):
        return self.read_flash(self.mac_region[0], len(self.mac_region))

    def read_license(self):
        return self.read_flash(self.lic_region[0], len(self.lic_region))

    def write_license(self):
        self.write_flash(self.lic_region[0], self.lic)

    def write_mac(self):
        self.write_flash(self.mac_region[0], self.mac)

    def write_flash(self, addr, list):
        status = self.talk( 0x09, 0x0A, addr, data=list)

        if status[0] != 0:
            raise Exception, "writing failed for addr %i status=%i len=%i"%(addr, status[0], len(status))

    def read_flash(self, addr, len):
        """ reads len bytes starting at address addr from
        flash memory.
        """
        return self.talk( 0x0B, 0x0C, addr, len )[1:] # strip command status

    def read_ram(self, addr, len):
        """ reads len bytes starting at address addr from
        ram.
        """
        return self.talk( 0x1F, 0x20, addr, len )[1:] # strip command status
