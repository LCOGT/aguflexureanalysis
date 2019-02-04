import multiprocessing as mp
import glob
import numpy as np
import scipy.signal
from scipy import ndimage
from astropy.io import fits
from astropy.time import Time
import sys
import logging
import agupinholedb
import argparse

log = logging.getLogger(__name__)

dbsession = None
reprocess = False
def findPinhole (imagename):
    """
        Find pinhole by cross-correlation with a template
    """

    if (reprocess is False) and (dbsession is not None):
        # test if image has been processed already.
        if agupinholedb.doesRecordExists(dbsession, imagename):
            log.debug ("Image %s already has a record in database, skipping" % imagename)
            return

    # Template
    radius = 7.5
    y,x = np.ogrid[-50:50, -50:50]
    mask = x*x + y*y <= radius * radius
    array = np.ones((100,100))
    array[mask] = 0
    array = array - np.mean (array)

    # image
    image = fits.open(imagename)

    CRPIX1 = int(image[1].header['CRPIX1'])
    CRPIX2 = int(image[1].header['CRPIX2'])

    background = np.median (image[1].data[350:-350,350:-350])

    extractdata = image[1].data[CRPIX2 - 60: CRPIX2 + 59, CRPIX1-60 : CRPIX1+59]

    centerbackground = np.median (extractdata)

    if centerbackground > background + 200:
        #         print ("Elevated background - probably star contamination - ignoring\n"
        #               + " background: % 8.1f  cutout: % 8.1f" % (background, centerbackground))
        return imagename, 0,0,0,0,0

    extractdata = extractdata - np.min (extractdata)
    extractdata = extractdata / np.median (extractdata)
    extractdata = extractdata - np.mean (extractdata)
    az  = image[1].header['AZIMUTH']
    alt = image[1].header['ALTITUDE']
    do = Time(image[1].header['DATE-OBS'], format='isot', scale='utc').datetime
    instrument = image[1].header['INSTRUME']

    image.close()

    #correlate and find centroid of correlation
    cor = scipy.signal.correlate2d (extractdata, array,boundary='symm', mode='same')
    y, x = np.unravel_index(np.argmax(cor), cor.shape)
    center = ndimage.measurements.center_of_mass(cor [y-15:y+15,x-15:x+15])
    x = center[0] + x - 15 + CRPIX1
    y = center[1] + y - 15 + CRPIX2

    #     plt.figure()
    #     plt.imshow (array,clim=(-1,1))
    #     plt.figure()
    #     plt.imshow (cor)
    #     plt.figure()
    #     plt.imshow (extractdata,clim=(-1,1))
    #     plt.plot (x,y,'o')


    if dbsession is not None:
        measurement = agupinholedb.PinholeMeasurement (imagename = imagename, instrument=instrument, altitude=alt, azimut=az, xcenter=x,ycenter=y,dateobs=do)
        dbsession.merge (measurement)
        dbsession.commit()
        log.info ("Adding to database: %s " % measurement)
    return


def findPinHoleInImages (imagelist,  ncpu = 3):
    alts=[]
    azs=[]
    xs = []
    ys = []
    images = []
    dos = []

    #imagelist = glob.glob (imagepath)
    pool = mp.Pool(processes=ncpu)
    pool.map (findPinhole, imagelist)




def parseCommandLine():
    """ Read command line parameters
    """

    parser = argparse.ArgumentParser(
        description='measure pinhole location in AGU images')
    parser.add_argument('inputfiles', type = str, nargs='+',)
    parser.add_argument('--log_level', dest='log_level', default='INFO', choices=['DEBUG', 'INFO'],
                        help='Set the debug level')
    parser.add_argument('--database', default = 'sqlite:///agupinholelocations.sqlite')
    parser.add_argument('--ncpu', default = 1, type=int)
    parser.add_argument('--reprocess', action='store_true')

    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')


    return args

if __name__ == '__main__':

    args = parseCommandLine()

    agupinholedb.create_db(args.database)
    dbsession =agupinholedb.get_session(args.database)

    findPinHoleInImages(args.inputfiles, ncpu= args.ncpu)


    sys.exit(0)

