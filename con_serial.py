# Copyright (c) 2011
# Telecooperation Office (TecO), Universitaet Karlsruhe (TH), Germany.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
# 3. Neither the name of the Universitaet Karlsruhe (TH) nor the names
#    of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# Author(s): Philipp Scholl <scholl@teco.edu>


from serial import *
from flashutils import JennicProtocol
from struct import pack
from os import write,path
from sys import stdout,exit
from time import sleep

class SerialBootloader(JennicProtocol):
    def __init__(self, devname):
        self.DEFAULT_TIMEOUT = .2
        self.MAX_TIMEOUT     = 10
        if devname==None: devname='/dev/ttyUSB0'

        sys.stdout.write("waiting for %s.."%devname)
        sys.stdout.flush()
        while True:
            f=-1
            try: f=open("/dev/ttyACM0")
            except IOError: pass
            else: break
        sys.stdout.write("done\n")

        self.ser = Serial(devname, 38400, timeout=.01, parity=PARITY_NONE,
                           stopbits=1, bytesize=8, rtscts=0, dsrdtr=0)

        # make sure that the baudrate is set!
        self.ser.setBaudrate(115200)
        self.ser.setBaudrate(38400)

        # switch to programming mode for boards that support it, atm
        # there is the jnode and jbee platform
        self.ser.setDTR(0); sleep(.01); self.ser.setDTR(1); sleep(.2)

        # read everything that is clogging up the input buffer, until we can
        # be sure that we are in programming mode.
        sys.stdout.write("waiting until queues are emtpy..")
        sys.stdout.flush()
        while self.ser.inWaiting():
            self.ser.read(self.ser.inWaiting())
            sleep(.5)
        sys.stdout.write("done\n")

        # switch to maximum baudrate
        self.ser.write(pack("<BBBB", 3,0x27,1,self.crc([3,0x27,1],3)))
        self.ser.read(3)
        self.ser.setBaudrate(1000000)

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

        if anstype == None:
            return []

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

    def finish(self):
        """ starts the execution by resetting the jennic modules. """
        self.ser.setDTR(0); sleep(.01); self.ser.setDTR(1);
        self.ser.close()
