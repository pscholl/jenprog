import sys

class JennicProtocol:
    def __init__(self):
        self.mac_region    = range(0x00000030, 0x00000038)
        self.lic_region    = range(0x00000038, 0x00000048)
        self.mac, self.lic = None, None
        self.isverbose     = None
        self.preferedblocksize = None
        self.select_flash()

    def select_flash(self):
        self.identify_flash()
        if not self.flash_jennicid in (0x00, 0x01, 0x02, 0x03):
            print "unsupported flash type"
            sys.exit(1)
        status = self.talk(0x2C, 0x2D, data = [self.flash_jennicid])[0]
        if not status == 0:
            print "could not select detected flash type was: %d"%status
            sys.exit(1)

    def identify_flash(self):
        flash = self.talk(0x25, 0x26)
        self.flash_status       = flash[0]
        self.flash_manufacturer = flash[1]
        self.flash_type         = flash[2]

        if not self.flash_status == 0:
            print "flash status != 0"
            sys.exit(0)

        if self.flash_manufacturer == 0x10 and self.flash_type == 0x10:
            self.flash_manufacturer = "ST"
            self.flash_type         = "M25P10-A"
            self.flash_jennicid     = 0x00
        elif self.flash_manufacturer == 0xBF and self.flash_type == 0x49:
            self.flash_manufacturer = "SST"
            self.flash_type         = "25VF010A"
            self.flash_jennicid     = 0x01
        elif self.flash_manufacturer == 0x1f and (self.flash_type == 0x60\
             or self.flash_type == 0x65):
            self.flash_manufacturer = "Atmel"
            self.flash_type         = "25F512"
            self.flash_jennicid     = 0x02
        elif self.flash_manufacturer == 0x12 and self.flash_type == 0x12:
            self.flash_manufacturer = "ST"
            self.flash_type         = "M25P40"
            self.flash_jennicid     = 0x03
        else:
            self.flash_manufacturer = "unknown"
            self.flash_type         = "unknown"
            self.flash_jennicid     = 0xFF

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

        if not len(self.mac)==len(self.mac_region):
            print "mac must be %i byte long"%len(self.mac_region)
            sys.exit(1)

    def set_license(self, s):
        self.lic = []

        for i in range(0, len(s), 2):
            if s[i:i+2] != "0x":
                self.lic.append( int( s[i:i+2], 16 ) )

        if not len(self.lic)==len(self.lic_region):
            print "license must be %i byte long"%len(self.lic_region)
            sys.exit(1)

    def erase_flash(self):
        """ read mac and license key prior to erasing
        """
        if not self.mac:
            self.mac = self.read_mac()
        if not self.lic:
            self.lic = self.read_license()
        #assert len(self.mac)==len(self.mac_region), "read mac addr too short"
        #assert len(self.lic)==len(self.lic_region), "read license too short"

        if not self.talk( 0x0F, 0x10, data=[0x00] )[0] == 0:
            print("disabling write protection failed")
            sys.exit(1)

        if not self.talk( 0x07, 0x08 )[0] == 0:
            print("erasing did not work")
            sys.exit(1)

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
        pass
