#!/bin/bash

#DATABASE="sqlite:///agupinholelocations.sqlite"

ndays=3
NCPU=1

#agupinholesearch --ndays ${ndays} --ncpu ${NCPU} --loglevel INFO --database ${DATABASE} --useaws
aguanalysis --database ${DATABASE} --outputpath /home/dharbeck/public_html/agupinhole
