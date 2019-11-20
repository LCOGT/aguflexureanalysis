#!/bin/bash

database="sqlite:///agupinholelocations.sqlite"
ndays=3
NCPU=2

python aguanalysis/agupinholesearch.py --ndays ${ndays} -ncpu {$NCPU} --loglevel INFO --database ${database}
python aguanalysis/aguanalysis.py --database ${database} -outputpath /home/dharbeck/public_html/agupinhole
