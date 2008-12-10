#!/usr/bin/env python

from flashutils import *
from optparse import *
from sys import stdout, stderr

parser = OptionParser()
parser.add_option("-a", "--address", dest="addr", type="int",
                  help="start reading at address", metavar="ADDR", default=0x00000000)
parser.add_option("-l", "--len", dest="len", type="int",
                  help="number of bytes to read", metavar="LEN", default=192000)
parser.add_option("-m", "--mac", dest="mac",
                  help="reset the mac addr")
parser.add_option("-k", "--key", dest="key",
                  help="reset the license key")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                  help="print send and received packets")
parser.add_option("-y", "--verify", action="store_true", dest="verify",
                  help="also verify after writing")
parser.add_option("-s", "--show", dest="show", action="store_true",
                  help="show mac address and license key")
parser.add_option("-e", "--erase", dest="erase", action="store_true",
                  help="erasing the flash after reading mac and license key")

(options, args) = parser.parse_args()

bl = Bootloader()

if options.verbose:
    bl.verbose()

#
# Select the actions:
#
if options.show or options.erase:
    stdout.write("flash: %s %s\n"%(bl.flash_manufacturer, bl.flash_type))
    stdout.write("mac: 0x")
    for b in bl.read_mac():
        stdout.write("%02x"%b)
    stdout.write(" license: 0x")
    for b in bl.read_license():
        stdout.write("%02x"%b)
    stdout.write("\n")

    if options.erase:
        bl.erase_flash()
elif options.mac or options.key:
    if options.mac:
        bl.set_mac(options.mac)
        bl.write_mac()
    if options.key:
        bl.set_license(options.key)
        bl.write_license()
elif len(args)!=1:
    block = 0x80
    for addr in xrange(options.addr, options.addr+options.len, block):
        for byte in bl.read_flash(addr, block):
            stdout.write("%c"%byte)

    stderr.write("need file argument for write")
else:
    file = open(args[0], "rb")

    # read the file size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0, 0)

    # start reading the file
    data = file.read(0x80)
    addr = 0x00000000

    # output information
    stat = "0x%x 0x%x" % (addr, size)
    stdout.write(stat)
    stdout.flush()

    # erase_flash gets the mac and license key prior to doing
    # its opertation.
    bl.erase_flash()

    while len(data) != 0:
        bl.write_flash(addr, data)
        addr += len(data)
        data  = file.read(0x80)

        # update status information
        for i in range(0, len(stat)):
            stdout.write('\b')
        stat = "0x%x/0x%x" % (addr, size)
        stdout.write(stat)
        stdout.flush()

    if options.verify:
        raise Exception, "not implemented"

    bl.write_mac()
    bl.write_license()
    bl.finish()
