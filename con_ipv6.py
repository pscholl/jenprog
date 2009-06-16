from socket import *
from struct import *
from sys    import stdout, stderr
from flashutils import JennicProtocol

class IPBootloader(JennicProtocol):
    def __init__(self, addr, port=2048):
        af,typ,proto,name,sa = getaddrinfo(addr,port,AF_UNSPEC,SOCK_STREAM)[0]
        self.sock = socket(af,typ,proto)
        self.sock.connect(sa)
        JennicProtocol.__init__(self)
        self.preferedblocksize=0x1f0
        self.addr=0x00

    def write_init(self, flash_image_size):
        self.talk( 0x2e, addr=flash_image_size )
        self.image_size = flash_image_size
        self.addr = 0
        print flash_image_size

    def write2_flash(self, addr, block):
        assert self.addr==addr, "%i, %i"%(self.addr, addr)
        self.addr += self.sock.send(block)

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
