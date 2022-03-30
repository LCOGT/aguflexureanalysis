import argparse
import concurrent
import faulthandler
import logging
import os
import sys
import warnings
import math
from concurrent.futures.process import ProcessPoolExecutor

import astropy.stats
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal
from astropy.io import fits
from astropy.time import Time
from scipy import ndimage

import lcogt_nres_aguanalysis.agupinholedb as agupinholedb
from lcogt_awsarchiveaccess.lco_archive_utilities import get_frames_by_identifiers, download_from_archive
from lcogt_awsarchiveaccess.lco_archive_utilities import ArchiveDiskCrawler

log = logging.getLogger(__name__)

TEMPLATE_FRAMESIZE = 50
TEMPLATE_RADIUS = 6
EXTRACT_FRAMESIZE = 60

def findPinhole(imagename, args, frameid):
    """
        Find pinhole by cross-correlation with a template
        if frameid is not none, fetch from archive
    """

    log.debug(f"Processing pinhole in {imagename} {frameid}")

    # Create a template
    y, x = np.ogrid[-TEMPLATE_FRAMESIZE:TEMPLATE_FRAMESIZE, -TEMPLATE_FRAMESIZE:TEMPLATE_FRAMESIZE]
    mask = x * x + y * y <= TEMPLATE_RADIUS * TEMPLATE_RADIUS
    array = np.ones((TEMPLATE_FRAMESIZE * 2, TEMPLATE_FRAMESIZE * 2))
    array[mask] = -1
    array = array - np.mean(array)

    # image
    if frameid is None:
        image = fits.open(imagename)
    else:
        image = download_from_archive(frameid)

    # CRPIX1/2 is an ok prior for the pinhole location within 10 pixels at least.
    CRPIX1 = int(image[1].header['CRPIX1'])
    CRPIX2 = int(image[1].header['CRPIX2'])
    az = image[1].header['AZIMUTH']
    alt = image[1].header['ALTITUDE']
    do = Time(image[1].header['DATE-OBS'], format='isot', scale='utc').datetime
    instrument = image[1].header['INSTRUME']
    foctemp = float(image[1].header['WMSTEMP'])
    site = str(image[1].header['SITEID'])
    enclosure = str(image[1].header['ENCID'])
    telescope = str(image[1].header['TELID'])

    if (alt == 'UNKNOWN') or (az == ' UNKNOWN'):
        return None

    if 'ak05' in instrument:
        # fix central hot pixel
        log.debug("Fix ak05 hot pixel")
        hpx = 716 - 1 # ds9 coordinate, 1-indexed.
        hpy = 590 - 1
        image[1].data[hpy, hpx] = 1 / 2. * (image[1].data[hpy, hpx + 1] + image[1].data[hpy, hpx - 1])
    if 'ak16' in instrument:
        # fix central hot pixel
        log.debug("Fix ak05 hot pixel")
        hpx = 609 - 1 # ds9 coordinate, 1-indexed.
        hpy = 548 - 1
        image[1].data[hpy, hpx] = 1 / 2. * (image[1].data[hpy, hpx + 1] + image[1].data[hpy, hpx - 1])

    extractdata = image[1].data[CRPIX2 - EXTRACT_FRAMESIZE: CRPIX2 + (EXTRACT_FRAMESIZE-1),
                  CRPIX1 - EXTRACT_FRAMESIZE: CRPIX1 + (EXTRACT_FRAMESIZE-1)].astype(float)

    imagebackground = np.median(image[1].data[350:-350, 350:-350])
    image.close()

    # check if pinhole is illuminated by star. if so, reject
    centerbackground = np.mean(extractdata)
    if centerbackground > imagebackground + 50:
        log.info("Elevated background - probably star contamination - ignoring\n"
                 + " background: % 8.1f  cutout: % 8.1f" % (imagebackground, centerbackground))
        return None

    # remove outliers (like hot pixels) and normalize data around window, normalize data to [-1 ... +1]
    centerbackground = np.median(extractdata)
    std = np.std (extractdata)
    extractdata[extractdata > centerbackground + 5 * std] = centerbackground
    min = np.min(extractdata)
    max = np.median(extractdata) + 3 * std
    extractdata[extractdata>max] = max

    extractdata = extractdata - min
    extractdata = extractdata / (0.5 * (max - min)) - 1

    # correlate and find centroid of correlation
    cor = scipy.signal.correlate2d(extractdata, array, boundary='symm', mode='same')
    peak_y, peak_x = np.unravel_index(np.argmax(cor), cor.shape)
    center = ndimage.measurements.center_of_mass(cor[peak_y - TEMPLATE_RADIUS*3:peak_y + TEMPLATE_RADIUS*3, peak_x - TEMPLATE_RADIUS*3: peak_x + TEMPLATE_RADIUS*3])

    xo = center[1] + (peak_x - TEMPLATE_RADIUS*3) + 1 # needed to center the coordinate. not sure why.
    yo = center[0] + (peak_y - TEMPLATE_RADIUS*3) + 1

    peak_x + peak_x + 1
    peak_y + peak_y + 1

    x =  xo + (CRPIX1 - EXTRACT_FRAMESIZE) + 1 # IRAF / FITS starts at pixel 1, and is center of pixel
    y =  yo + (CRPIX2 - EXTRACT_FRAMESIZE) + 1

    ## FITS starts stuff at 1

    if args.makepng:

        plt.imshow(cor)
        plt.plot(peak_x, peak_y, 'x', color='red')
        plt.plot(xo, yo, 'x', color='blue')
        plt.title (os.path.basename (imagename))
        plt.colorbar()
        plt.savefig(f"correlation-{os.path.basename (imagename)}.png", dpi=300)
        plt.close()

        plt.imshow(extractdata, clim=(-1, 1))
        plt.plot(xo, yo, 'o', color='red')
        plt.plot(xo, yo, 'x', color='green')

        plt.colorbar()
        plt.title (os.path.basename (imagename))
        plt.savefig(f"center-{os.path.basename (imagename)}.png", dpi=300)
        plt.close()

    measurement = agupinholedb.PinholeMeasurement(imagename=str(imagename), instrument=instrument, altitude=alt,
                                                  azimut=az, xcenter=x if math.isfinite(x) else None, ycenter=y if math.isfinite(y) else None, dateobs=do, foctemp=foctemp,
                                                  telescopeidentifier=f'{site}-{enclosure}-{telescope}', crpix1=CRPIX1, crpix2=CRPIX2)
    log.info(f"Measurement: {measurement}")
    return measurement


def findPinHoleInImages(imagelist, dbsession, args):
    results = []
    futures = []

    # TODO: This makes the out for loop give up.
    with ProcessPoolExecutor(max_workers=args.ncpu) as e:
        for image in imagelist:
            imagefilename = os.path.basename(str(image['filename']))
            imageid = int(image['frameid']) if args.useaws else None
            log.debug(f'Extracted file info: {imagefilename}  {imageid}')
            if (args.reprocess is False) and (dbsession is not None):
                # test if image has been processed already.
                if agupinholedb.doesRecordExists(dbsession, imagefilename):
                    log.debug("Image %s already has a record in database, skipping" % image)
                    continue

            futures.append(e.submit(findPinhole, imagefilename, args, imageid))

        e.shutdown(wait=True)

        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except:
                log.exception("While reading back future)")

    for datum in results:
        if datum is not None:
            log.info("Adding to database: %s " % datum)
            try:
                dbsession.merge(datum)
            except:
                log.warn (f"Could not add datum: {datum}")

    dbsession.commit()
    return None


def parseCommandLine():
    """ Read command line parameters
    """

    parser = argparse.ArgumentParser(
        description='measure pinhole location in AGU images')

    parser.add_argument('--loglevel', dest='log_level', default='INFO', choices=['DEBUG', 'INFO'],
                        help='Set the debug level')
    parser.add_argument('--database', default='sqlite:///agupinholelocations.sqlite')
    parser.add_argument('--ncpu', default=1, type=int)
    parser.add_argument('--reprocess', action='store_true')
    parser.add_argument('--makepng', action='store_true')
    parser.add_argument('--useaws', action='store_true')

    parser.add_argument('--ndays', default=3, type=int, help="How many days to look into the past")
    parser.add_argument('--cameratype', type=str, nargs='+', default=['ak??', ],
                        help='Type of cameras to parse')
    parser.add_argument('--single', default = None)
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')
    log.debug("cameratype: {} ".format(args.cameratype))
    return args


def main():
    faulthandler.enable()
    global args
    global reprocess
    args = parseCommandLine()
    reprocess = args.reprocess
    warnings.simplefilter("ignore")

    agupinholedb.create_db(args.database)
    dbsession = agupinholedb.get_session(args.database)

    c = ArchiveDiskCrawler()
    dates = c.get_last_n_days(args.ndays)
    if not args.useaws:
        cameras = c.find_cameras(sites=['lsc', 'elp', 'tlv', 'cpt'], cameras=args.cameratype)
    else:
        cameras = ['ak01', 'ak02', 'ak03', 'ak04', 'ak05', 'ak06', 'ak07', 'ak10', 'ak11', 'ak12', 'ak13', 'ak14', ]

    log.info("Found cameras: {}".format(cameras))

    if args.single is not None:
        cameras = [args.single,]
        log.info (f"Cameras is now: {cameras}")

    for camera in cameras:
        log.info(f"Crawling {camera} ")
        for date in dates:
            if args.useaws:
                files = get_frames_by_identifiers(date, camera=camera, mintexp=5, obstype='EXPERIMENTAL', rlevel=0)
            else:
                files = ArchiveDiskCrawler.findfiles_for_camera_dates(camera, date, 'raw', "*[x]00.fits*")
            log.info(f'         {camera} / {date} has {len(files) if files is not None else "None"} images.')
            if (files is not None) and (len(files) > 0):
                findPinHoleInImages(files, dbsession, args)
    dbsession.close()
    sys.exit(0)


if __name__ == '__main__':
    main()
