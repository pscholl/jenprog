%module ftdi
%{
#include "ftdi.h"
#include <usb.h>
#include <future.h>

int ftdi_debug(struct ftdi_context *c, int i)
{
  usb_set_debug(i);
  return 0;
};

%}

%include     "typemaps.i"
%include     "carrays.i"
%array_class(unsigned char, cArray);

%include ftdi.h

int ftdi_debug(struct ftdi_context *c, int i);
