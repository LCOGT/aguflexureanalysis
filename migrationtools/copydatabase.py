'''
Tool to copy gain history data from one database to another, in particular to support hte migration from local sqlite to online postgress.
'''
import argparse
import logging

import lcogt_nres_aguanalysis.agupinholedb as agupinholedb


def parseCommandLine():
    parser = argparse.ArgumentParser(
    description='Copy noisegain database from A to B')

    parser.add_argument('--loglevel', dest='log_level', default='INFO', choices=['DEBUG', 'INFO', 'WARN'],
                    help='Set the debug level')

    parser.add_argument('--inputurl', type=str,  default='sqlite:///noisegain.sqlite', help="input database")
    parser.add_argument('--outputurl' ,type=str , default='sqlite:///noisegain.sqlite', help="input database")

    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                    format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')
    return args

if __name__ == '__main__':
    args = parseCommandLine()
    print (f"Copy from {args.inputurl} -> {args.outputurl}")

    input = agupinholedb.get_session (args.inputurl, Base=agupinholedb.Base_v1)
    output = agupinholedb.get_session (args.outputurl)


    q = input.query (agupinholedb.PinholeMeasurement_v1)

    print ("Found {} records to copy.".format(q.count()))
    print ("Refactoring data")
    newdata = [agupinholedb.pinholefrompinhole_v1(e) for e in q.all()]

    # now do anything in between.

    print ("Now doing bulk insert")
    output.bulk_save_objects (newdata)

    output.commit()

    input.close()
    output.close()
