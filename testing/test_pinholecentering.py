import argparse
from lcogt_nres_aguanalysis import agupinholesearch


TESTDATA = {'tlv1m0XX-ak14-20210501-0127-e00.fits.fz' : {'x': 782.6, 'y': 586.5, 'error': None},
}

TESTDATADIR = 'testing/testdata'
CENTERTOLERANCE= 2

args = argparse.Namespace()
args.makepng = True

for image in TESTDATA:
    print (image, TESTDATA[image])
    measurement = agupinholesearch.findPinhole (f'{TESTDATADIR}/{image}', args, None)
    x = measurement.xcenter
    y = measurement.ycenter
    print (f"{image} measured {x} / {y}  should be   {TESTDATA[image]['x']} / {TESTDATA[image]['y']}")
    assert (abs(x - TESTDATA[image]['x']) < CENTERTOLERANCE)
    assert (abs(y - TESTDATA[image]['y']) < CENTERTOLERANCE)


