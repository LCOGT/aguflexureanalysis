import argparse
import logging
from lcogt_nres_aguanalysis import agupinholesearch

TESTDATA = {'tlv1m0XX-ak14-20210501-0127-e00.fits.fz' : {'x': 782.6, 'y': 586.5, 'error': False},
            'tlv1m0XX-ak13-20201128-1029-x00.fits.fz' : {'x': 782.5, 'y': 546.6, 'error': False },
            'cpt1m013-ak06-20210504-0092-g00.fits.fz' : {'x': 0, 'y': 0, 'error': True},
            'tlv1m0XX-ak13-20201001-0006-x00.fits.fz' : {'x': 781.4, 'y': 549.7, 'error': False}
}

TESTDATADIR = 'testing/testdata'
CENTERTOLERANCE= 2


def test_agupingholecentering(caplog):
    caplog.set_level(logging.INFO)
    args = argparse.Namespace()
    args.makepng = True

    for image in TESTDATA:
        print (image, TESTDATA[image])
        measurement = agupinholesearch.findPinhole (f'{TESTDATADIR}/{image}', args, None)

        assert (measurement == None) == TESTDATA[image]['error']

        if measurement is not None and TESTDATA[image]['error'] is False:
            x = measurement.xcenter
            y = measurement.ycenter
            print (f"{image} measured {x} / {y}  should be   {TESTDATA[image]['x']} / {TESTDATA[image]['y']}")
            assert (abs(x - TESTDATA[image]['x']) < CENTERTOLERANCE), f"X center in {image}"
            assert (abs(y - TESTDATA[image]['y']) < CENTERTOLERANCE), f"Y center in {image}"




