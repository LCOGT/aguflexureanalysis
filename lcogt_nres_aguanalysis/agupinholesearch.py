import argparse
import concurrent
import faulthandler
import logging
import sys
import warnings
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


def findPinhole(imagename, args, frameid):
    """
        Find pinhole by cross-correlation with a template
        if frameid is not none, fetch from archive
    """

    log.debug(f"Processing pinhole in {imagename} {frameid}")

    # Template
    radius = 7.5
    y, x = np.ogrid[-50:50, -50:50]
    mask = x * x + y * y <= radius * radius
    array = np.ones((100, 100))
    array[mask] = 0
    array = array - np.mean(array)

    # image
    if frameid is None:
        image = fits.open(imagename)
    else:
        image = download_from_archive(frameid)

    CRPIX1 = int(image[1].header['CRPIX1'])
    CRPIX2 = int(image[1].header['CRPIX2'])
    az = image[1].header['AZIMUTH']
    alt = image[1].header['ALTITUDE']
    do = Time(image[1].header['DATE-OBS'], format='isot', scale='utc').datetime
    instrument = image[1].header['INSTRUME']
    foctemp = float(image[1].header['WMSTEMP'])
    if 'ak05' in instrument:
        # fix central hot pixel
        print("Fix hot pixel")
        hpx = 716 - 1
        hpy = 590 - 1
        image[1].data[hpy, hpx] = 1 / 2. * (image[1].data[hpy, hpx + 1] + image[1].data[hpy, hpx - 1])

    extractdata = image[1].data[CRPIX2 - 60: CRPIX2 + 59, CRPIX1 - 60: CRPIX1 + 59].astype(float)

    image.close()

    # check if pinhole is iluminated by star. if so, reject
    background = np.median(image[1].data[350:-350, 350:-350])
    centerbackground = np.median(extractdata)
    if centerbackground > background + 2000:
        log.info("Elevated background - probably star contamination - ignoring\n"
                 + " background: % 8.1f  cutout: % 8.1f" % (background, centerbackground))
        return None

    # normalize data around window

    med = astropy.stats.sigma_clip(extractdata, cenfunc='median')
    min = np.min(extractdata)
    max = np.max(extractdata)

    extractdata = extractdata - background
    extractdata = extractdata / (max - min)
    # extractdata = extractdata / astropy.stats.sigma_clip(extractdata, cenfunc='median')
    # extractdata = extractdata - astropy.stats.sigma_clip(extractdata, cenfunc='mean')

    # correlate and find centroid of correlation
    cor = scipy.signal.correlate2d(extractdata, array, boundary='symm', mode='same')
    y, x = np.unravel_index(np.argmax(cor), cor.shape)
    center = ndimage.measurements.center_of_mass(cor[y - 15:y + 15, x - 15:x + 15])
    xo = center[0] + x - 15
    yo = center[1] + x - 15
    x = center[0] + x - 15 + CRPIX1
    y = center[1] + y - 15 + CRPIX2

    if args.makepng:
        plt.figure()
        plt.imshow(extractdata, clim=(-1, 1))
        plt.colorbar()
        plt.savefig("rawimage.png")
        plt.imshow(cor)
        plt.savefig("correlation")
        plt.imshow(extractdata, clim=(-1, 1))
        plt.plot(xo, yo, 'o')
        plt.savefig("center.png")
        plt.close()

    measurement = agupinholedb.PinholeMeasurement(imagename=str(imagename), instrument=instrument, altitude=alt,
                                                  azimut=az, xcenter=x, ycenter=y, dateobs=do, foctemp=foctemp)
    log.info(f"Measurement: {measurement}")
    return measurement


def findPinHoleInImages(imagelist, dbsession, args):
    results = []
    futures = []

    # TODO: This makes the out for loop give up.
    with ProcessPoolExecutor(max_workers=args.ncpu) as e:
        for image in imagelist:
            imagefilename = str(image['filename'])
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
            dbsession.merge(datum)

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
        cameras = ['ak01', 'ak02', 'ak05', 'ak06', 'ak10', 'ak11', 'ak12']

    log.info("Found cameras: {}".format(cameras))

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
