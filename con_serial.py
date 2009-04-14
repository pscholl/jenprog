from serial import *
from flashutils import JennicProtocol
from struct import pack
from os import write

class SerialBootloader(JennicProtocol):
    def __init__(self, devname):
        self.DEFAULT_TIMEOUT = .1
        self.MAX_TIMEOUT     = 2
        if devname==None: devname='/dev/ttyUSB0'
        self.ser = Serial(devname, 38400, timeout=.1, parity=PARITY_NONE,
                           stopbits=1, bytesize=8, rtscts=1, dsrdtr=0)
        self.ser.open()
        JennicProtocol.__init__(self)

    def talk(self, type, anstype, addr=None, mlen=None, data=None):
        length = 3

        if addr != None: length += 4
        if mlen != None: length += 2
        if data != None: length += len(data)

        msg  = pack('<BB', length-1, type)
        if addr != None: msg += pack('<I', addr)
        if mlen != None: msg += pack('<H', mlen)
        if data != None:
            if data.__class__ == str:
                msg += data
            else:
                msg += pack('<%is'%len(data), "".join(map(chr,data)))
        msg += pack('<B', self.crc(map(ord,msg), len(msg)))

        try:
            self.ser.timeout = self.DEFAULT_TIMEOUT
            self.ser.write(msg)
            n,ans = ord(self.ser.read(1)), ""
            while len(ans)<n: # TODO: problematic
                ans += self.ser.read(n)
        except TypeError: # thrown when self.ser.read() gets nothing
            self.ser.timeout = self.MAX_TIMEOUT
            n,ans = ord(self.ser.read(1)), ""
            while len(ans)<n:
                ans += self.ser.read(n)
        return map(ord,ans[1:-1])

