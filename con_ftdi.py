from ftdi import *
from time import sleep
from flashutils import JennicProtocol
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

class FtdiBootloader(JennicProtocol):
    def __init__(self):
        self.f = Ftdi()

        try:
            # Teco usbbridge
            self.f.usb_open(0x0403, 0xcc40)

            # clear crap
            self.f.usb_reset()
            self.f.usb_purge_buffers()
            self.f.usb_purge_buffers()
            crap = cArray(1024)
            self.f.read_data(crap, 1024)

            self.enterprogrammingmode()
            self.doreset = 1

            # clear crap
            self.f.usb_reset()
            self.f.usb_purge_buffers()
            self.f.usb_purge_buffers()
            crap = cArray(1024)
            self.f.read_data(crap, 1024)

        except:
            # Jennics usb2serial cable
            self.f.usb_open(0x0403, 0x6001)
            self.doreset = 0

        # clear crap
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

        JennicProtocol.__init__(self)

    def enterprogrammingmode(self):
        """ uses bitbang mode to set DSR,DTR lines which are connected to the
        reset and programming pin on the jennic board.
        See http://www.ftdichip.com/Documents/AppNotes/AN232B-01_BitBang.pdf

        DTR is connected to SPIMISO (bit 4)
        DSR is connected to RESET   (bit 5)
        """
        RESET, SPIMISO, NONE = 1<<5, 1<<4, 0x00

        def write(b):
            msg = cArray(1); msg[0]=b;
            self.f.write_data(msg, 1)

        self.f.enable_bitbang(SPIMISO|RESET)
        write(0x00)
        sleep(.1)
        self.f.disable_bitbang()
        self.f.enable_bitbang(SPIMISO)
        write(0x00)
        sleep(.1)
        self.f.disable_bitbang()

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

    def finish(self):
        """ depending on the connected device, do a reset.
        Switch to bitbang and toggle reset line.
        """
        if self.doreset:
            def write(b):
                msg = cArray(1); msg[0]=b
                self.f.write_data(msg, 1)

            RESET, NONE = 1<<5, 0x00
            self.f.enable_bitbang(RESET)
            write(0x00)
            sleep(.1)
            self.f.disable_bitbang()
        self.usb_close()

