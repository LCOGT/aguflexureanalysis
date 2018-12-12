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

dbsession = None

def findPinhole (imagename):
    """
        Find pinhole by cross-correlation with a template
    """
    # Template
    radius = 7.5
    y,x = np.ogrid[-50:50, -50:50]
    mask = x*x + y*y <= radius * radius
    array = np.ones((100,100))
    array[mask] = 0
    array = array - np.mean (array)

    # image
    image = fits.open(imagename)
    background = np.median (image[1].data[350:-350,350:-350])

    extractdata = image[1].data[520:640,620:740]

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
    image.close()

    #correlate and find centroid of correlation
    cor = scipy.signal.correlate2d (extractdata, array,boundary='symm', mode='same')
    y, x = np.unravel_index(np.argmax(cor), cor.shape)
    center = ndimage.measurements.center_of_mass(cor [y-15:y+15,x-15:x+15])
    x = center[0] + x - 15
    y = center[1] + y - 15

    #     plt.figure()
    #     plt.imshow (array,clim=(-1,1))
    #     plt.figure()
    #     plt.imshow (cor)
    #     plt.figure()
    #     plt.imshow (extractdata,clim=(-1,1))
    #     plt.plot (x,y,'o')


    if dbsession is not None:
        dbsession
    return imagename, alt,az,x,y, do


def findPinHoleInImages (imagepath, dbsession = None,  ncpu = 3):
    alts=[]
    azs=[]
    xs = []
    ys = []
    images = []
    dos = []

    imagelist = glob.glob (imagepath)
    pool = mp.Pool(processes=ncpu)
    results = pool.map (findPinhole, imagelist)

    for result in results:
        image,alt,az,x,y, do = result
        alts.append(alt)
        azs.append (az)
        xs.append (x)
        ys.append (y)
        images.append (image)
        dos.append(do)

    alts=np.asarray(alts)
    azs=np.asarray(azs)
    xs=np.asarray(xs)
    ys=np.asarray(ys)
    images = np.asarray(images)
    dos = np.asarray(dos)

    az = azs
    az[az>180] =az[az>180] - 360
    return images, alts,az,xs,ys, dos


def parseCommandLine():
    """ Read command line parameters
    """

    parser = argparse.ArgumentParser(
        description='measure pinhole location in AGU images')
    parser.add_argument('--log_level', dest='log_level', default='INFO', choices=['DEBUG', 'INFO'],
                        help='Set the debug level')
    parser.add_argument('--database', default = 'sqlite:///agupinholeocations.sqlite')
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')

    return args

if __name__ == '__main__':

    args = parseCommandLine()

    agupinholedb.create_db(args.database)
    session =agupinholedb.get_session(args.database)

    sys.exit(0)

