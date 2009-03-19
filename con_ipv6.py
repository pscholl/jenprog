from socket import *
from struct import *
from sys    import stdout, stderr
from flashutils import JennicProtocol

class IPBootloader(JennicProtocol):
    def __init__(self, addr, port=2048):
        af,typ,proto,name,sa = getaddrinfo(addr,port,AF_UNSPEC,SOCK_STREAM)[0]
        self.sock = socket(af,typ,proto)
        self.sock.connect(sa)
        self.preferedblocksize=0xf0
        JennicProtocol.__init__(self)

    def talk(self, type, ans_type, addr=None, mlen=None, data=None):
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
        ans = self.sock.recv(1024)
        if self.isverbose: print "<- %i"%len(ans)
        return map(ord,ans[2:-1])

    def finish(self):
        self.sock.close()
