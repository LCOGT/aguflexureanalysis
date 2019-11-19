#!/bin/bash

database="sqlite:///agupinholelocations.sqlite"


base=/archive/engineering
cameras="ak??"
sites="cpt lsc tlv elp"
dates="201911??"

inputselection="*-x00.fits.fz"

NCPU=20

for site in $sites; do
 for camera in $cameras; do

  sitecameras=`find ${base}/${site}  -maxdepth 1 -type d -wholename "*/$camera"`
  for sitecamera in $sitecameras; do

   directories=`find "${sitecamera}" -maxdepth 1 -type d  -wholename "*/${dates}" `

   for day in $directories; do

     searchpath=${day}/raw/${inputselection}
     searchpath=`ls $searchpath | shuf -n 400 |  xargs  echo`
     echo "Searchpath is $searchpath"
     sem  -j $NCPU python aguanalysis/agupinholesearch.py --loglevel INFO --database ${database} $searchpath

   done

  done

 done
done

sem --wait

python aguanalysis/aguanalysis.py --database ${database} --outputpath /home/dharbeck/public_html/agupinhole

