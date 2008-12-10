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
        try:
            # Jennics usb2serial cable
            self.f.usb_open(0x0403, 0x6001)
            self.doreset = 0
        except:
            # Teco usbbridge
            self.f.usb_open(0x0403, 0xcc40)
            self.enterprogrammingmode()
            self.doreset = 1

        self.f.usb_reset()
        self.f.usb_purge_buffers()
        self.f.usb_purge_buffers()
        crap = cArray(1024)
        self.f.read_data(crap, 1024)
        self.f.set_baudrate(38400)
        self.f.set_line_property(NONE, STOP_BIT_1, BITS_8)
        self.f.setrts(1)
        self.f.setflowctrl(SIO_RTS_CTS_HS)
        self.f.setrts(0)

        self.mac_region    = range(0x00000030, 0x00000038)
        self.lic_region    = range(0x00000038, 0x00000048)
        self.mac, self.lic = None, None
        self.isverbose     = None

        self.select_flash()

    def select_flash(self):
        self.identify_flash()
        assert self.flash_jennicid in (0x00, 0x01, 0x02), "unsupported flash type"
        status = self.talk(0x2C, 0x2D, data = [self.flash_jennicid])[0]
        assert status == 0, "could not select detected flash type was: %d"%status

    def identify_flash(self):
        flash = self.talk(0x25, 0x26)
        self.flash_status       = flash[0]
        self.flash_manufacturer = flash[1]
        self.flash_type         = flash[2]

        assert self.flash_status == 0, "flash status != 0"

        if self.flash_manufacturer == 0x10 and self.flash_type == 0x10:
            self.flash_manufacturer = "ST"
            self.flash_type         = "M25P10-A"
            self.flash_jennicid     = 0x00
        elif self.flash_manufacturer == 0xBF and self.flash_type == 0x49:
            self.flash_manufacturer = "SST"
            self.flash_type         = "25VF010A"
            self.flash_jennicid     = 0x01
        elif self.flash_manufacturer == 0x1f and self.flash_type == 0x60:
            self.flash_manufacturer = "Atmel"
            self.flash_type         = "25F512"
            self.flash_jennicid     = 0x02
        else:
            self.flash_manufacturer = "unknown"
            self.flash_type         = "unknown"
            self.flash_jennicid     = 0xFF

    def enterprogrammingmode(self):
        """ uses bitbang mode to set DSR,DTR lines which are connected to the
        reset and programming pin on the jennic board.
        See http://www.ftdichip.com/Documents/AppNotes/AN232B-01_BitBang.pdf

        DTR is connected to SPIMISO (bit 4)
        DSR is connected to RESET   (bit 5)
        """
        def write(b):
            msg = cArray(1); msg[0]=b
            self.f.write_data(msg, 1)

        RESET, SPIMISO, NONE = 1<<5, 1<<4, 0x00
        self.f.enable_bitbang((RESET|SPIMISO)&0xFF)
        #write(~RESET&0xFF)
        #sleep(2)
        write(~(RESET|SPIMISO)&0xff)
        sleep(.2)
        write(~(SPIMISO)&0xff)
        sleep(.2)
        self.f.disable_bitbang()

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

        type     msg type prefix
        ans_type anticipiated reply type prefix
        addr     flash address for types supporting it
        mlen     number of bytes read from addr to addr+mlen
        data     array containing data to be sent

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

            # send the message until there is an answer
            while ans_len == 0:
                waited = 0
                self.f.write_data(msg, msg_len)

                # wait some cycles until the message will be repeated
                while waited < 150 and ans_len == 0:
                    ans_len = self.f.read_data(ans, 1)
                    waited  += 1

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

    def finish(self):
        """ depending on the connected device, do a reset.
        Switch to bitbang and toggle reset line.
        """
        if self.doreset:
            def write(b):
                msg = cArray(1); msg[0]=b
                self.f.write_data(msg, 1)

            RESET = 1<<5
            self.f.enable_bitbang((RESET)&0xFF)
            write(~(RESET)&0xff)
            sleep(.2)
            self.f.disable_bitbang()

