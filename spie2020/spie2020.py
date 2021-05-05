import argparse
import datetime
import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import sys
import lcogt_nres_aguanalysis.agupinholedb as agupinholedb
import matplotlib.dates as mdates
import lcogt_nres_aguanalysis.aguanalysis as aguanalysis

plt.style.use('ggplot')
_logger = logging.getLogger(__name__)


def pertelescopeplot(cameras, database, sitename, starttime=None, endtime=None, ):
    for camera in cameras:
        images, alts, az, xs, ys, dobs, foctemps, crpix1, crpix2 = aguanalysis.readPinHoles(camera, database)

        index = (np.isfinite(xs)) & np.isfinite(ys) & (xs != 0)  # & (alts>89)
        medianxs = np.nanmedian(xs[index])
        xs = xs - medianxs
        ys = ys - np.nanmedian(ys[index])

        index = (np.isfinite(xs)) & np.isfinite(ys) & (xs != 0)  # & (alts>89)
        # print("Min {} Max {} ".format(dobs[index].min(), dobs[index].max()))
        plt.subplot(211)
        plt.plot(dobs[index], xs[index], ',', label=f"{camera}")


        plt.plot ( dobs[index], crpix1[index] - np.median( crpix1[crpix1 > 0]), ',', color='orange', label='Assumed location')
        plt.ylim([-15, 15])
        plt.title(f"Pinhole location in focus images {sitename}")
        plt.ylabel("rel. center X")
        aguanalysis.dateformat()
        if starttime is not None:
                plt.xlim([starttime, endtime])

        plt.subplot(212)
        plt.plot(dobs[index], ys[index], ',', label=f"{camera}")
        plt.plot (dobs[index], crpix2[index] - np.median( crpix2[crpix2 > 0]), ',', color='orange', label='Assumed location')

        plt.ylim([-15, 15])
        plt.ylabel("rel. center Y")
        aguanalysis.dateformat()
        if starttime is not None:
            plt.xlim([starttime, endtime])

    #plt.subplot(211)
    # plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
    #            ncol=2, mode="expand", borderaxespad=0.)
    plt.tight_layout()
    plt.savefig(f'{sitename.replace(" ", "-")}_longerm.png', dpi=300)
    plt.close()


if __name__ == '__main__':
    database = os.getenv('DATABASE')
    print(f'Database is {database}')
    # tlvhistory
    pertelescopeplot(['ak03', 'ak10', 'ak12', 'ak13', 'ak14'], database, "tlv doma", starttime=datetime.datetime(2018, 6, 1),
                     endtime=datetime.datetime.now() + datetime.timedelta(days=7))

    #pertelescopeplot(['ak04', 'ak11'], database, "elp doma")
