import multiprocessing as mp
import glob
import numpy as np
import scipy.signal
from scipy import ndimage
from astropy.io import fits
from astropy.time import Time

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


    return imagename, alt,az,x,y, do


def findPinHoleInImages (imagepath):
    alts=[]
    azs=[]
    xs = []
    ys = []
    images = []
    dos = []

    imagelist = glob.glob (imagepath)
    pool = mp.Pool(processes=3)
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



