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
from gbd.dismod3.settings import CSV_PATH
from django.db import transaction

class Command(BaseCommand):
    help = 'Import covariate data from a .csv file.'
    args = 'filename.csv'

    @transaction.commit_on_success
    def handle(self, *params, **options):
        """ Load a covariate file into database

        Parameters:
        -----------
          params: list of length 2
            element 1 - a .csv file containing the covariate data
            element 2 - type_slug of the covariate to load
          options: not used
        """
        if len(params) != 2:
            raise CommandError('a single .csv file amd type_slug are required as input.')

        region_only = ''
        while region_only != 'Y' and region_only != 'N':
            region_only = raw_input('Does the covariate data file have region column and no iso3 column? Y|N  ')

        # read the csv file into a list of dicts
        fname = params[0]
        type_slug = params[1]
        csv_f = csv.DictReader(open(fname))
        cov_data = [d for d in csv_f]
        
        # process the data
        if cov_data and type_slug:
            # make an iso3 list
            iso3_data = [x[1:] for x in csv.reader(open(CSV_PATH + 'country_region.csv'))]
            iso3_list = []
            for r in iso3_data:
                iso3_list += r

            # make a region list
            region_list = [x[0] for x in csv.reader(open(CSV_PATH + 'country_region.csv'))]

            # make a region_country_dict
            region_country_dict = {}
            for x in csv.reader(open(CSV_PATH + 'country_region.csv')):
                region_country_dict[x[0]] = x[1:]

            # check the cov data content
            for ii, d in enumerate(cov_data):
                try:
                    d['value'] = float(d[type_slug])
                except KeyError:
                    print('Could not find column %s (is it spelled correctly?)' % type_slug)
                    return
                except ValueError:
                    print('Could not interpret value for %s in line %d' % (type_slug, ii+2))
                    return

                if d.has_key('year'):
                    try:
                        d['year'] = int(d['year'])
                    except ValueError:
                        print('Could not interpret year in line %d' % (ii+2))
                        return
                else:
                    d['year'] = gbd.fields.ALL_YEARS
                        
                d['sex'] = d.get('sex', '')
                if not d['sex'] in ['male', 'female', 'total', '']:
                    print('Could not interpret sex in line %d' % (ii+2))
                    return

                if region_only == 'Y' and not d.has_key('region'):
                    print('Could not find column region (is it spelled correctly?)')
                    return

                if not d.has_key('iso3') and not d.has_key('region'):
                    print('Could not find either column iso3 or column region (is it spelled correctly?)')
                    return

                if d.has_key('iso3') and not d['iso3'] in iso3_list:
                    print('Could not interpret iso3 in line %d' % (ii+2))
                    return

                if d.has_key('region') and not d['region'] in region_list:
                    print('Could not interpret region in line %d' % (ii+2))
                    return

                if d.has_key('iso3') and d.has_key('region') and d['iso3'] not in region_country_dict[d['region']]:
                    print('The iso3 and the region are inconsistent in line %d' % (ii+2))
                    return
                    
                if d.has_key('age'):
                    try:
                        int(d['age'])
                    except ValueError:
                        print('Could not interpret age in line %d' % (ii+2))
                        return

            # get or create the CovariateType object
            cov_type, is_new = CovariateType.objects.get_or_create(slug=type_slug, defaults={'year_start': 0, 'year_end': 0})

            # get infomation
            uploader = ''
            while uploader == '':
                uploader = raw_input('Please enter your DisMod username.  ')
            cov_type.uploader = uploader

            source = ''
            while source == '':
                source = raw_input('Where did you get this covariate data file?  ')
            cov_type.source = source

            description = ''
            while description == '':
                description = raw_input('Please enter a description, how the data was created, and how the missing values were filled in.  ')
            cov_type.description = description

            year_start = ''
            while year_start == '':
                year_start = raw_input('Please enter the starting year of the covariate.  ')
                try:
                    int(year_start)
                except ValueError:
                    year_start = ''
            cov_type.year_start = year_start

            year_end = ''
            while year_end == '':
                year_end = raw_input('Please enter the ending year of the covariate.  ')
                try:
                    int(year_end)
                except ValueError:
                    year_end = ''
            cov_type.year_end = year_end

            if region_only == 'Y':
                cov_type.region_only = True
            else:
                cov_type.region_only = False

            # calculate mean and variance
            vals = [d['value'] for d in cov_data]
            cov_type.mean = pl.mean(vals)
            scale = pl.std(vals)
            cov_type.variance = scale * scale

            cov_type.last_modified_time = datetime.now()

            # save covariate type        
            cov_type.save()

            # add cov data to cov objects
            print "Adding covariate data from %s" % fname
            save_covariates(cov_type, cov_data)

@transaction.commit_on_success
def save_covariates(cov_type, cov_data):
    """ Save covariate data in database

        Parameters:
        -----------
          cov_type : CovariateType object
          cov_data : List of covariate data dicts
    """
    # clean up
    Covariate.objects.filter(type=cov_type).delete()

    # insert covariate data
    for d in cov_data:
        # if sex == '' add a covariate for male, female, and total
        if d['sex'] == '':
            sex_list = ['male', 'female', 'total']
        else:
            sex_list = [d['sex']]
        for sex in sex_list:
            # add a data point, save it on the data list
            if d.has_key('iso3'):
                cov = Covariate(type=cov_type, iso3=d['iso3'], year=d['year'], sex=sex, value=d['value'])
                if d.has_key('region'):
                    cov.region = d['region']
            else:
                cov = Covariate(type=cov_type, region=d['region'], year=d['year'], sex=sex, value=d['value'])
                
            if d.has_key('age'):
                cov.age = d['age']
                  
            cov.save()
