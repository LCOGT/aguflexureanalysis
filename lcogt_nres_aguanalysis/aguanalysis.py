"""

Script to generate appealing plots of the NRES AGU pinhole lcoation vs. time.

Datapoints are retrieved from a database and plotted. that is it.

"""
import argparse
import datetime
import io
import logging
import os
import sys

import boto3
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

import lcogt_nres_aguanalysis.agupinholedb as agupinholedb

plt.style.use('ggplot')
_logger = logging.getLogger(__name__)
logging.getLogger('matplotlib').setLevel(logging.FATAL)

available_cameras = ['ak01', 'ak02', 'ak03', 'ak04', 'ak05', 'ak06', 'ak07', 'ak10', 'ak11', 'ak12', 'ak13', 'ak14', ]

def aws_enabled():
    '''Return True if AWS support is configured'''
    access_key = os.environ.get('AWS_ACCESS_KEY_ID', None)
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY', None)
    s3_bucket = os.environ.get('AWS_S3_BUCKET', None)
    region = os.environ.get('AWS_DEFAULT_REGION', None)

    return access_key and secret_key and s3_bucket and region


def write_to_storage_backend(directory, filename, data, binary=True):
    if aws_enabled():
        # AWS S3 Bucket upload
        client = boto3.client('s3')
        bucket = os.environ.get('AWS_S3_BUCKET', None)
        try:
            with io.BytesIO(data) as fileobj:
                _logger.debug(f'Write data to AWS S3: {bucket}/{filename}')
                response = client.upload_fileobj(fileobj, bucket, filename)
                _logger.debug(f'Done writing data to AWS S3: {bucket}/{filename}')
                return response
        except:
            _logger.exception(f"While storing object {filename} into S3 backend.")
    else:
        fullpath = os.path.join(directory, filename)
        _logger.info(f'writing to file system {fullpath}')
        with open(fullpath, 'wb' if binary else 'w') as fileobj:
            fileobj.write(data)
            return True


def readPinHoles(cameraname, sql):
    dbsession = agupinholedb.get_session(sql)

    images = []
    alt = []
    az = []
    xs = []
    ys = []
    dobs = []
    foctemps = []
    crpix1 = []
    crpix2 = []

    _logger.debug (f"Working on {cameraname}")
    resultset = dbsession.query(agupinholedb.PinholeMeasurement)
    resultset = resultset.filter(agupinholedb.PinholeMeasurement.instrument == cameraname)
    # weed out vestigal bpl contamination. don't want that.
    resultset = resultset.filter(~agupinholedb.PinholeMeasurement.imagename.contains('bpl'))
    resultset = resultset.order_by (agupinholedb.PinholeMeasurement.dateobs)
    for result in resultset:
        images.append(result.imagename)
        alt.append(result.altitude)
        az.append(result.azimut)
        xs.append(result.xcenter)
        ys.append(result.ycenter)
        dobs.append(result.dateobs)
        foctemps.append(result.foctemp)
        crpix1.append (result.crpix1)
        crpix2.append (result.crpix2)

    return images, np.asarray(alt), np.asarray(az), \
           np.asarray(xs, dtype=np.float32), \
           np.asarray(ys, dtype=np.float32), \
           np.asarray(dobs), np.asanyarray(foctemps), \
           np.asarray (crpix1), np.asarray(crpix2)
    dbsession.close()


def dateformat():
    """ Utility to prettify a plot with dates.
    """
    starttime = datetime.datetime(2017, 1, 1)
    endtime = datetime.datetime.now() + datetime.timedelta(days=14)
    plt.xlim([starttime, endtime])
    plt.gcf().autofmt_xdate()
    years = mdates.YearLocator()  # every year
    months = mdates.MonthLocator(bymonth=[4, 7, 10])  # every month
    yearsFmt = mdates.DateFormatter('%Y %b')
    monthformat = mdates.DateFormatter('%b')
    plt.gca().xaxis.set_major_locator(years)
    plt.gca().xaxis.set_major_formatter(yearsFmt)
    plt.gca().xaxis.set_minor_locator(months)
    plt.gca().xaxis.set_minor_formatter(monthformat)
    plt.setp(plt.gca().xaxis.get_minorticklabels(), rotation=45)
    plt.setp(plt.gca().xaxis.get_majorticklabels(), rotation=45)
    plt.gca().grid(which='minor')



def findrecentPinhole(dobs, xs, ys):

    ## Start determining the most recent pinhole location
    recent_x = recent_y = None
    if len (dobs) > 11:
        lastdayobs = dobs[-1]
        recentindex = dobs > lastdayobs - datetime.timedelta (days=14)
        if sum(recentindex) < 7:
            _logger.info ("Not enough pinhole locations measured")
            return None, None

        recent_x = np.median(xs[recentindex])
        recent_y = np.median(ys[recentindex])
        return recent_x, recent_y
    else:
        _logger.warning("Not enough recent measurements")
        return None, None


def plotagutrends(camera='ak01', sql='sqlite:///agupinholelocations.sqlite', outputpath='.'):
    plt.style.use('ggplot')
    matplotlib.rcParams['savefig.dpi'] = 300
    matplotlib.rcParams['figure.figsize'] = (8.0,6.0)

    images, alts, az, xraw, yraw, dobs, foctemps, crpix1, crpix2 = readPinHoles(camera, sql)
    _logger.info("Found {} entries".format(len(images)))
    # Sort out bad values
    index = (np.isfinite(xraw)) & np.isfinite(yraw) & (xraw != 0)  # & (alts>89)
    xraw = xraw[index]
    yraw = yraw[index]
    dobs = dobs[index]
    alts= alts[index]
    crpix1 = crpix1[index]
    crpix2 = crpix2[index]
    foctemps = foctemps[index]
    az = az[index]

    # Median-correct to we have a nice homogeneous plotting range between camera adjustments.
    xraw_median = np.nanmedian(xraw)
    yraw_median = np.nanmedian(yraw)
    xs = xraw - xraw_median
    ys = yraw - yraw_median

    timewindow = datetime.timedelta(days=5)
    filteredy = ys * 0
    filteredx = xs * 0
    smallnumber = (np.abs(ys) < 15) & (np.abs(xs) < 15)
    recent_x, recent_y = findrecentPinhole(dobs, xraw,yraw)

    print (f"recent pinhole location: {recent_x} {recent_y}, compare to CRPix: {crpix1[-1]} {crpix2[-1]}")

    index = (np.isfinite(xs)) & np.isfinite(ys) & (xs != 0)  # & (alts>89)
    # print("Min {} Max {} ".format(dobs[index].min(), dobs[index].max()))
    plt.subplot(211)
    plt.plot(dobs, xs, '.', label="pinhole x",  markersize=1)
    if recent_x:
        plt.plot (dobs[-1], recent_x -xraw_median, 'o', color='green')
    else:
        recent_x = -1
    plt.ylim([-15, 15])
    plt.title(f"{camera} pinhole location in focus images X recent {recent_x:6.1f}, CRPIX1: {crpix1[-1]:6.1f}:")
    dateformat()

    plt.subplot(212)
    plt.plot(dobs, ys, '.', label="pinhole y",  markersize=1)
    if recent_y:
        plt.plot (dobs[-1], recent_y -yraw_median, 'o', color='green')
    else:
        recent_y = -1


    plt.ylim([-15, 15])
    plt.title(f"{camera} pinhole location in focus images Yrecent {recent_y:6.1f}, CRPIX2: {crpix2[-1]:6.1f}:")
    dateformat()
    plt.tight_layout()

    with io.BytesIO() as fileobj:
        filename = f'longtermtrend_pinhole_{camera}.png'
        plt.gcf().set_size_inches(12,6)
        plt.savefig(fileobj, format='png', bbox_inches='tight')
        plt.close()
        write_to_storage_backend(outputpath, filename, fileobj.getvalue())

    plt.figure()

    for ii in range(len(dobs)):
        filteredy[ii] = ys[ii] - np.median(
            ys[(dobs > dobs[ii] - timewindow) & (dobs < dobs[ii] + timewindow) & (smallnumber)])
        filteredx[ii] = xs[ii] - np.median(
            xs[(dobs > dobs[ii] - timewindow) & (dobs < dobs[ii] + timewindow) & (smallnumber)])

    plt.subplot(221)
    plt.plot(alts, filteredy - np.nanmedian(filteredy), '.', label="pinhole y",  markersize=2)
    plt.legend()
    plt.ylim([-15, 15])
    plt.xlabel('ALT')

    plt.subplot(222)
    plt.plot(az, filteredy - np.nanmedian(filteredy), '.', label="pinhole y",  markersize=2)
    plt.ylim([-15, 15])
    plt.legend()
    plt.xlabel('AZ')

    plt.subplot(223)
    plt.plot(alts, filteredx - np.nanmedian(filteredx), '.', label="pinhole x",  markersize=2)
    plt.ylim([-15, 15])
    plt.legend()
    plt.xlabel('ALT')

    plt.subplot(224)
    plt.plot(az, filteredx - np.nanmedian(filteredx), '.', label="pinhole x",  markersize=2)
    plt.ylim([-15, 15])
    plt.legend()
    plt.xlabel('AZ')

    plt.tight_layout()
    with io.BytesIO() as fileobj:
        filename = f'altaztrends_pinhole_{camera}.png'
        plt.savefig(fileobj, format='png', bbox_inches='tight')
        plt.close()
        write_to_storage_backend(outputpath, filename, fileobj.getvalue())

    plt.figure()
    plt.subplot(211)
    plt.title("%s pinhole location in focus images " % (camera))

    plt.plot(foctemps, xs, ".", label="pinhole x",  markersize=2)
    plt.ylabel("x-position")
    plt.xlabel("WMS temp [\deg C]")
    plt.ylim([-15, 15])
    plt.xlim([-10, 35])

    plt.subplot(212)
    plt.title("%s pinhole location in focus images " % (camera))

    plt.plot(foctemps, ys, ".", label="pinhole x",  markersize=2)
    plt.ylim([-15, 15])
    plt.xlim([-10, 35])
    plt.ylabel("x-position")
    plt.xlabel("WMS temp [\deg C]")

    with io.BytesIO() as fileobj:
        filename = f'foctemp_pinhole_{camera}.png'
        plt.savefig(fileobj, format='png', bbox_inches='tight')
        plt.close()
        write_to_storage_backend(outputpath, filename, fileobj.getvalue())


def parseCommandLine():
    """ Read command line parameters
    """

    parser = argparse.ArgumentParser(
        description='Plot pinhole location in AGU images')

    parser.add_argument('--loglevel', dest='log_level', default='INFO', choices=['DEBUG', 'INFO'],
                        help='Set the debug level')
    parser.add_argument('--database', default='sqlite:///agupinholelocations.sqlite')
    parser.add_argument('--ncpu', default=1, type=int)
    parser.add_argument('--outputpath', default="aguhistory", help="Root directory for output")
    parser.add_argument('--camera',  choices=available_cameras, help='only process single selected camera')

    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')
    return args


def renderHTMLPage(args, cameras):
    if aws_enabled():
        _logger.info("Since we are working in the context of a AWS bucket, no local index.html is generated here")
        return
    _logger.info("Now rendering output html page")

    outputfile = "%s/index.html" % (args.outputpath)

    message = """<html>
<head></head>
<body><title>LCO NRES AGU Pinhole Location Plots</title>
"""
    message += "<p/>Figures updated %s UTC <p/>\n" % (datetime.datetime.utcnow())
    message += """
<h1> Details by Camera: </h1>
"""

    for camera in cameras:
        message = message + " <h2> %s </h2>\n" % (camera)

        historyname = 'longtermtrend_pinhole_{}.png'.format(camera)
        altazfile = 'altaztrends_pinhole_{}.png'.format(camera)
        tempfilename = 'foctemp_pinhole_{}.png'.format(camera)
        line = f'<a href="{historyname}"><img src="{historyname}" height="500"/></a>  ' \
               f'<a href="{altazfile}"><img src="{altazfile}" height="500"/></a> ' \
               f'<a href="{tempfilename}"><img src="{tempfilename}" height="500"/></a><br/>  '
        message = message + line

    message = message + "</body></html>"

    with open(outputfile, 'w+') as f:
        f.write(message)
        f.close()


def main():
    args = parseCommandLine()
    cameras = available_cameras if args.camera is None else [args.camera, ]

    for camera in cameras:
        plotagutrends(camera, outputpath=args.outputpath, sql=args.database)
        #findrecentPinhole(camera, sql=args.database)
        pass
    renderHTMLPage(args, cameras)
    sys.exit(0)


if __name__ == '__main__':
    main()
