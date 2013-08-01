# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from IPython.core.display import HTML
def css_styling():
    styles = open("./styles/custom.css", "r").read()
    return HTML(styles)
css_styling()

# <headingcell level=1>

# Reading custom binaries

# <markdowncell>

# *This notebook was originally a post by Filipe Fernandes on*
# [*python4oceanographers*](http://ocefpaf.github.io/)

# <markdowncell>

# <!-- PELICAN_BEGIN_SUMMARY -->
# Every now and then we stumble upon some wierd custom binary file containing that precious piece of data.  This post show how to read the most wierd one I've see so far.
# <!-- PELICAN_END_SUMMARY -->

# <markdowncell>

# My former advisor had all his data stored in a custom binary format he called "OASP" (instead of using the wonderful, machine independent, feature-rich [netcdf](http://cf-pcmdi.llnl.gov/) with climate and forecast metadata that we all should be using!).  
# 
# His programs to read such data were not working anymore due to [endianness](http://en.wikipedia.org/wiki/Endianness) issues.  Therefore, to read that data (and hopefully graduate one day) I had workaround these issues relying heavily on numpy [fromfile](http://docs.scipy.org/doc/numpy/reference/generated/numpy.fromfile.html) function.

# <codecell>

import numpy as np

# <markdowncell>

# Let's define two quick functions to deal with the time standard used in the binary files...

# <codecell>

from netCDF4 import netcdftime
from datetime import timedelta

def jhour2datetime(jhours):
    """Convert OASP Julian hours to datetime object.
    Uses netcdftime.DateFromJulianDay
                        jhours-12
    datetime_object =  ----------- + offset
                           24.0

    OASP is offsetted by 241502 days to match netcdftime.DateFromJulianDay,
    and 12 hours are added to make it start at midnight instead of noon.

    Example
    --------
    >>> oaspy.jhour2datetime([859296, 859928])
    [datetime.datetime(1998, 1, 11, 0, 0), datetime.datetime(1998, 2, 6, 8, 0)]
    """
    offset = 2415021
    if isinstance(jhours,list):
        jhours = (np.array(jhours)-12)/24.
        jdate  = ([netcdftime.DateFromJulianDay(jhours[d]+offset) for d in
                   range(len(jhours))])
    else:
        jhours = (jhours-12)/24.
        jdate  = netcdftime.DateFromJulianDay(jhours+offset)
    return jdate


def datetime2jhour(dtimeobj):
    """Convert datetime object to OASP Julian hours using.
    Uses netcdftime.JulianDayFromDate.
    See jhour2datetime for details.

    Example
    -------
    >>> oaspy.datetime2jhour([datetime.datetime(1998, 1, 11, 0, 0), datetime.datetime(1998, 2, 6, 8, 0)])
    array([ 859296.,  859928.])
    """
    offset = 2415021

    if isinstance(dtimeobj,list):
        jhours = ([netcdftime.JulianDayFromDate(dtimeobj[d])-offset for d in
                   range(len(dtimeobj))])
    else:
        jhours = netcdftime.JulianDayFromDate(dtimeobj)-offset

    jhours = np.array(jhours)
    jhours = (jhours*24.)+12
    return jhours

# <markdowncell>

# ... and create a class akin to `netCDF4` Dataset to read the binary file.

# <codecell>

class Dataset(object):
    """Read OASP binary format and store in a object with:
        filename
        header
        data
        dates
        stats
        parameter file
    """

    def __init__(self, filename, endianess='big'):
        """Read a OASP binary file
        > means Big-endian
        c  -> character
        f8 -> float64 (double precision)
        i4 -> interger32
        f4 -> float32
        """
        self.filename = filename
        self.header = ''
        self.data = []
        self.dates = []
        self.stats = ''
        self.par = ''
        if endianess == 'big':
            en = '>'
        elif endianess == 'little':
            en = '<'
        else:
            raise ValueError("Cannot determine endianess. Try 'big' or 'little'.")

        with open(filename, 'rb') as f:
            # 38 characters for header.
            header = list(np.fromfile(f, '%sc' % en, count=38))
            # date[1] and date[3] start/end in oasp julian hours.
            jhours = np.fromfile(f, '%sf8' % en, count=4)[1::2]
            # rec[2] -> record length.
            rec = np.fromfile(f, '%si4' % en, count=3)[2]
            # inc[1] -> record time increment in hours.
            inc = np.fromfile(f, '%sf8' % en, count=2)[1]
            start = jhour2datetime(jhours[0])
            end = jhour2datetime(jhours[1])
            # From start date to record number using increment.
            self.dates = np.asanyarray([start + timedelta(hours=inc*n) for
                                        n in range(rec)])
            # Remove newline and file creation dates.
            self.header += "filename:      %s" % ''.join(header)[1:13]
            self.header += ("creation date: " + ''.join(header)[13:21] +
                            "   " + ''.join(header)[21:])
            self.header += "\n" + "start date:    " + str(self.dates[0])
            self.header += "\n" + "end date:      " + str(self.dates[-1])
            self.header += "\n" + "increment:     " + str(inc)
            self.header += "\n" + "record length  " + str(rec)
            # Data eliminating Fortran "record".
            self.data = np.fromfile(f, '%sf4' % en, count=rec*3)[2::3]
            # Basic stats.
            self.stats = "%s: %.2f" % ("Max",  self.data.max())
            self.stats += "%s: %.2f" % ("\nMin",  self.data.min())
            self.stats += "%s: %.2f" % ("\nMean", self.data.mean())
            self.stats += "%s: %.2f" % ("\nMedian", np.median(self.data))
            self.stats += "%s: %.2f" % ("\nStd", self.data.std())
            # Parameter file.
            self.par += "y\n"
            self.par += filename + ".asc\n"
            self.par += '1' + "\n"
            self.par += '1' + "\n"
            self.par += '3' + "\n"
            self.par += '0' + "\n"
            self.par += str(jhours[0])+ "\n"
            self.par += str(inc)+ "\n"
            self.par += "1," + filename + "\n"
            self.par += '0' + "\n"
            self.par += "$$"

# <codecell>

wbsst = Dataset('./data/wbsst.bin')

# <markdowncell>

# Let's checkout the file header:

# <codecell>

print(wbsst.header)

# <markdowncell>

# Some information regarding the data:

# <codecell>

print(wbsst.stats)

# <markdowncell>

# And finally let's see the data!

# <codecell>

from mpltools import style
style.use("ggplot")

fig, ax = plt.subplots(figsize=(12, 6))
_ = ax.plot(wbsst.dates, wbsst.data)
_ = ax.set_ylabel(r"Air Temperature [$^\circ$C]")

# <markdowncell>

# The class also create the original parameter file used in the create of the binary.

# <codecell>

print(wbsst.par)

# <markdowncell>

# *This post was written entirely as an IPython notebook. The full notebook can be downloaded*
# [*here*](http://ocefpaf.github.io/downloads/notebooks/custom-binaries.ipynb),
# *or viewed statically on*
# [*nbviewer*](http://nbviewer.ipython.org/url/ocefpaf.github.io/downloads/notebooks/custom-binaries.ipynb)

