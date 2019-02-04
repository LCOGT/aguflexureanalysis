import matplotlib.pyplot as plt
import numpy as np
import sys
import agupinholedb
import matplotlib.dates as mdates
plt.rcParams["figure.figsize"] = (20,12)
plt.style.use('ggplot')


def readPinHoles (cameraname, sql):

    dbsession =agupinholedb.get_session(sql)

    images = []
    alt= []
    az = []
    xs = []
    ys=[]
    dobs=[]

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

    return images, np.asarray(alt),np.asarray(az),np.asarray(xs,dtype=np.float32),np.asarray(ys, dtype=np.float32),np.asarray(dobs)
    dbsession.close()

def dateformat ():
    """ Utility to prettify a plot with dates.
    """

    #plt.xlim([starttime, endtime])
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


    images,alts,az,xs,ys, dobs = readPinHoles (camera,sql)
    print ("Found {} entries".format(len(images)))
    plt.figure()

    index = (np.isfinite(xs)) & np.isfinite (ys)  & (xs != 0)# & (alts>89)

    plt.plot (dobs[index], xs[index] - np.nanmedian (xs[index]), '.', label="pinhole x")
    plt.ylim([-20,20])
    plt.legend()
    plt.title("%s pinhole location in focus images X" % (camera))
    dateformat()
    plt.savefig ('longtermtrend_pinhole_%s-x.png' % (camera))


    plt.figure()
    plt.plot (dobs[index], ys[index] - np.nanmedian (ys[index]), '.', label="pinhole y")
    plt.ylim([-20,20])
    plt.legend()
    plt.title("%s pinhole location in focus images Y" % (camera))
    dateformat()
    plt.savefig ('longtermtrend_pinhole_%s-y.png' % (camera))



if __name__ == '__main__':

    #plotagutrends ('ak01')
    #plotagutrends ('ak06')
    #plotagutrends ('ak08')
    plotagutrends ('ak10')
sys.exit(0)


