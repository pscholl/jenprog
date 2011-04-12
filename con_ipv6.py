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


from socket import *
from struct import *
from time   import sleep
from sys    import stdout, stderr
from flashutils import JennicProtocol

class IPBootloader(JennicProtocol):
    def __init__(self, addr, port=2048):
        af,typ,proto,name,sa = getaddrinfo(addr,port,AF_UNSPEC,SOCK_STREAM)[0]
        self.sock = socket(af,typ,proto)
        self.sock.connect(sa)
        JennicProtocol.__init__(self)
        self.preferedblocksize=0xff
        self.addr=0x00

    def write_init(self, flash_image_size):
        self.talk( 0x2e, addr=flash_image_size )
        self.image_size = flash_image_size
        self.addr = 0

    def write2_flash(self, addr, block):
        assert self.addr==addr, "%i, %i"%(self.addr, addr)
        self.addr += self.sock.send(block)
        #sleep(.5)

        if self.addr==self.image_size and\
           unpack("BBBB", self.sock.recv(4))[1]!=47:
            raise Exception("protocol error")

    def talk(self, type, ans_type=None, addr=None, mlen=None, data=None):
        """ executes one speak-reply cycle

        type     msg type prefix
        ans_type anticipiated reply type prefix
        addr     flash address for types supporting it
        mlen     number of bytes read from addr to addr+mlen
        data     array containing data to be sent

        throws an exception if the answer type is not the anticipiated one
        """
        length = 3
        if addr != None: length += 4
        if mlen != None: length += 2
        if data != None: length += len(data)

        msg  = pack('!BB', length, type)
        if addr != None: msg += pack('!I', addr)
        if mlen != None: msg += pack('!H', mlen)
        if data != None:
            if data.__class__ == str:
                msg += data
            else:
                msg += pack('!%is'%len(data), "".join(map(chr,data)))
        msg += pack('!B', 0) #self.crc(msg, len))


        if self.isverbose: print "-> %i"%len(msg)
        self.sock.send(msg)

        if ans_type!=None:
            ans = self.sock.recv(1024)
            if self.isverbose: print "<- %i"%len(ans)
            return map(ord,ans[2:-1])
        else:
            return None

    def finish(self):
        """ send a special command which reset the remote target.
        """
        self.sock.send(pack('!BBIB', 7, 0x21, 0, 0))
        self.sock.close()
