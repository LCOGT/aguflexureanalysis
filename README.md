# Las Cumbres Observatory - NRES AGU pinhole location crawler

This is a way to monitor the change in the NRES AGU pinhole location.

Workflow is:
####agupinholesearch
  * Query AGU focus iamges (*.x00) images via elasticsearch fits index.
  * Detect pin hole location in those images, and write location plus meta information in the database backend

####aguanalysis
  * Query database, and crate timeline /flexure plots for each ak?? camera. 
  * Plots are either written into an output directory or into S3 bucket if ENV variables define a bucket
 
#### webapp
 * for use in production envirnment (kubernetes): serve the plots via a web page out of the S3 buckets  









### Usefull development commands:
* Create a local postgress server:

   ```docker run -p 5432:5432 --name aguflexureanalysis -e POSTGRES_PASSWORD=test123 -e POSTGRES_USER=aguflexureanalysis -d postgres```

