#!/bin/bash

ndays=4
NCPU=1

agupinholesearch --ndays ${ndays} --ncpu ${NCPU} --loglevel INFO --database ${DATABASE} --useaws
aguanalysis --database ${DATABASE} --outputpath agupinhole_html
