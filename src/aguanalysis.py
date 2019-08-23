import datetime
import matplotlib.pyplot as plt
import numpy as np
import sys
import agupinholedb
import matplotlib.dates as mdates
plt.style.use('ggplot')


def readPinHoles (cameraname, sql):

    dbsession =agupinholedb.get_session(sql)

    images = []
    alt= []
    az = []
    xs = []
    ys=[]
    dobs=[]
    foctemps = []

    print (cameraname)
    resultset = dbsession.query (agupinholedb.PinholeMeasurement)
    resultset = resultset.filter(agupinholedb.PinholeMeasurement.instrument==cameraname)
    for result in resultset:
        images.append (result.imagename)
        alt.append (result.altitude)
        az.append (result.azimut)
        xs.append (result.xcenter)
        ys.append (result.ycenter)
        dobs.append (result.dateobs)
        foctemps.append (result.foctemp)

    return images, np.asarray(alt),np.asarray(az),np.asarray(xs,dtype=np.float32),np.asarray(ys, dtype=np.float32),np.asarray(dobs), np.asanyarray(foctemps)
    dbsession.close()

def dateformat ():
    """ Utility to prettify a plot with dates.
    """
    starttime = datetime.datetime(2017, 6, 1)
    endtime = datetime.datetime.now() + datetime.timedelta(days=7)
    plt.xlim([starttime, endtime])
    plt.gcf().autofmt_xdate()
    years = mdates.YearLocator()   # every year
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


def plotagutrends (camera='ak01', sql='sqlite:///agupinholelocations.sqlite'):



    images,alts,az,xs,ys, dobs, foctemps = readPinHoles (camera,sql)
    print ("Found {} entries".format(len(images)))
    index = (np.isfinite(xs)) & np.isfinite (ys)  & (xs != 0)# & (alts>89)
    xs = xs - np.nanmedian (xs[index])
    ys = ys - np.nanmedian (ys[index])

    timewindow = datetime.timedelta(days=5)
    filteredy = ys * 0
    filteredx = xs * 0
    smallnumber = (np.abs (ys)<15) & (np.abs (xs)<15)
    for ii in range (len(dobs)):
        filteredy[ii] = ys[ii]  -np.median (ys[ (dobs > dobs[ii] - timewindow) & (dobs < dobs[ii] + timewindow) & (smallnumber)])
        filteredx[ii] = xs[ii]  -np.median (xs[ (dobs > dobs[ii] - timewindow) & (dobs < dobs[ii] + timewindow) & (smallnumber)])

    index = (np.isfinite(xs)) & np.isfinite (ys)  & (xs != 0)# & (alts>89)
    print ("Min {} Max {} ".format(dobs[index].min(), dobs[index].max()))
    plt.subplot (211)
    plt.plot (dobs[index], xs[index], ',', label="pinhole x")
    plt.ylim([-15,15])
    plt.title("%s pinhole location in focus images X" % (camera))
    dateformat()

    plt.subplot (212)
    plt.plot (dobs[index], ys[index] , ',', label="pinhole y")
    plt.ylim([-15,15])
    plt.title("%s pinhole location in focus images Y" % (camera))
    dateformat()
    plt.tight_layout()
    plt.savefig ('longtermtrend_pinhole_%s.png' % (camera))
    plt.close()


    plt.figure()
    plt.subplot (221)
    plt.plot (alts[index], filteredy[index] - np.nanmedian (filteredy[index]), ',', label="pinhole y")
    plt.legend()
    plt.ylim([-15,15])
    plt.xlabel ('ALT')

    plt.subplot (222)
    plt.plot (az[index], filteredy[index] - np.nanmedian (filteredy[index]), ',', label="pinhole y")
    plt.ylim([-15,15])
    plt.legend()
    plt.xlabel ('AZ')

    plt.subplot (223)
    plt.plot (alts[index], filteredx[index] - np.nanmedian (filteredx[index]), ',', label="pinhole x")
    plt.ylim([-15,15])
    plt.legend()
    plt.xlabel ('ALT')

    plt.subplot (224)
    plt.plot (az[index], filteredx[index] - np.nanmedian (filteredx[index]), ',', label="pinhole x")
    plt.ylim([-15,15])
    plt.legend()
    plt.xlabel ('AZ')

    plt.tight_layout()
    plt.savefig ('altaztrends_pinhole_%s.png' % (camera))
    plt.close()

    plt.figure()
    plt.subplot (211)
    plt.plot (foctemps[index], xs[index], ",", label="pinhole x")
    plt.ylim([-15,15])
    plt.xlim([-10,35])

    plt.subplot (212)
    plt.plot (foctemps[index], ys[index], ",", label="pinhole x")
    plt.ylim([-15,15])
    plt.xlim([-10,35])

    plt.savefig ("foctemp_pinhole_{}.png".format (camera))
    plt.close()


if __name__ == '__main__':

    plotagutrends ('ak01')
    plotagutrends ('ak02')
    plotagutrends ('ak06')
    plotagutrends ('ak05')

    plotagutrends ('ak10')
    sys.exit(0)


