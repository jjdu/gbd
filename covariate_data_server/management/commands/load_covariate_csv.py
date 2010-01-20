"""
Command to load covariate data from a csv

Use from the project directory as follows::

    $ python2.5 manage.py load_covariate_csv [options] filename.csv

"""

from django.core.management.base import BaseCommand, CommandError

import csv
import re
import pylab as pl

from gbd.covariate_data_server.models import *
from gbd.dismod3.settings import gbd_regions
from gbd.dismod3.utils import clean

class Command(BaseCommand):
    help = 'Import covariate data from a .csv file.'
    args = 'filename.csv'

    def handle(self, *fnames, **options):
        if len(fnames) != 1:
            raise CommandError('a single .csv file is required as input.')
        fname = fnames[0]

        print "adding population data from %s" % fname

        csv_f = csv.DictReader(open(fname))
        data = [d for d in csv_f]
        headings = csv_f.fieldnames

        type_slug = 'GDPpc'
        type_desc = 'log(GDP per capita) - mu_log(GDPpc)'
        type, is_new = CovariateType.objects.get_or_create(slug=type_slug, defaults={'description': type_desc})

        vals = []
        for d in data:
            for key in d.keys():
                for year in re.findall('\d+', key):
                    year = int(year)
                    try:
                        value = float(d[key])
                    except ValueError:
                        continue
                    if year > 1900 and year < 2050:
                        vals += [pl.log(value)]
        mu = pl.mean(vals)
        std = pl.std(vals)
        print '%d data points, mean=%.2f, std=%.2f' % (len(vals), mu, std)
        
        added = 0
        modified = 0
        for d in data:
            iso3 = d['iso3']
            sex = 'total'
            for key in d.keys():
                for year in re.findall('\d+', key):
                    year = int(year)
                    try:
                        value = float(d[key])
                    except ValueError:
                        continue
                    if year > 1900 and year < 2050:
                        cov, is_new = Covariate.objects.get_or_create(type=type, iso3=iso3, year=year, sex=sex, defaults={'value': value})
                        cov.value = (pl.log(value) - mu) / std
                        cov.save()
                        added += is_new
                        modified += not is_new
            try:
                print str(cov), cov.value
            except:
                pass

        print 'added %d country-years of covariate data' % added
        print 'modified %d country-years of covariate data' % modified
        