from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from datetime import datetime
import numpy as np
import gbd.fields
import types
import math
import pylab as pl

class CovariateType(models.Model):
    slug = models.CharField(max_length=50)
    uploader = models.CharField(max_length=30)
    upload_time = models.DateTimeField(default=datetime.now)
    source = models.TextField()
    last_modified_time = models.DateTimeField(default=datetime.now)
    description = models.TextField()
    year_start = models.IntegerField()
    year_end = models.IntegerField()
    region_only = models.BooleanField()
    mean = models.FloatField()
    variance = models.FloatField()

    def __unicode__(self):
        return self.slug

    def get_absolute_url(self):
        return reverse('gbd.covariate_data_server.views.covariate_type_show', args=[self.id])

    def calculate_covariates(self, data_list, transform_list):
        """ Calculate and cache specified covariate and a list of transforms in data.params
            to avoid repeatedly making the database queries required to compute it.
            If the covariate is not found, an empty str is used.

        Parameters:
        -----------
          data_list : list
            list of data dict in that the keys year_start, year_end and sex are required
            and if region_only of the CovariateType object is True the key region is required
            otherwise the key country_iso3_code is required.   
          transform_list : list
            list of strs each representing the transformation scheme: original, log, logit,
            squared, cubed, normalized, quantized

        Return:
        -------
          list of data dicts with added covariates, e.g. data_list[0][self.slug] = covariate.value
          note: data_list[0] is a dict that matches dismod_data_server.models.Data.params.
        """
        return self._calculate_covariates(data_list, transform_list)

    def calculate_covariates_lag(self, data_list, lag_year):
        """ Calculate and cache specified covariate with lag years in data.params
            to avoid repeatedly making the database queries required to compute it.
            If the covariate is not found, an empty str is used.

        Parameters:
        -----------
          data_list : list
            list of data dict in that the keys year_start, year_end and sex are required
            and if region_only of the CovariateType object is True the key region is required
            otherwise the key country_iso3_code is required.
          lag_year : int
            number of lage years.

        Return:
        -------
          list of data dicts with added covariates, e.g. data_list[0][self.slug] = covariate.value
          note: data_list[0] is a dict that matches dismod_data_server.models.Data.params.
        """
        return self._calculate_covariates(data_list, None, lag_year)

    def _calculate_covariates(self, data_list, transform_list, lag_year = 0):
        """ Calculate and cache specified covariate and a list of transforms in data.params
            to avoid repeatedly making the database queries required to compute it.
            If the covariate is not found, an empty str is used.

        Parameters:
        -----------
          data_list : list
            list of data dict in that the keys year_start, year_end and sex are required
            and if region_only of the CovariateType object is True the key region is required
            otherwise the key country_iso3_code is required.   
          transform_list : list
            list of strs each representing the transformation scheme: original, log, logit,
            squared, cubed, normalized, quantized, or None for lag on original
          lag_year : int
            number of lag years. not used if transform_list is not None

        Return:
        -------
          list of data dicts with added covariates, e.g. data_list[0][self.slug] = covariate.value
          note: data_list[0] is a dict that matches dismod_data_server.models.Data.params.
        """
        # check the input data_list
        if data_list == None:
            raise Exception('data_list is mising')

        if not isinstance(data_list, types.ListType):
            raise Exception('data_list is not a python list')

        if len(data_list) == 0:
            raise Exception('data_list is empty')

        if not isinstance(data_list[0], types.DictType):
            raise Exception('data_list is not a list of python dicts')

        # check the input transform_list and the lag_year
        if transform_list != None:
            if not isinstance(transform_list, types.ListType):
                raise Exception('transform_list is not a python list')

            for transform_str in transform_list:
                if not transform_str in ['original', 'log', 'logit', 'squared', 'cubed',
                                         'normalized', 'quantized']:
                    raise Exception('cannot understand transform_str: ' + transform_str)
        else:
            if not isinstance(lag_year, types.IntType):
                raise Exception('lag_year is not an int')

        # find year range in the data_list
        y_start = self.year_end
        y_end = 0
        if transform_list != None:
            for data_dict in data_list:
                start = int(data_dict['year_start'])
                if start < y_start:
                    y_start = start
                end = int(data_dict['year_end'])
                if end > y_end:
                    y_end = end
        else:
            for data_dict in data_list:
                start = int(data_dict['year_start']) - lag_year
                if start < y_start:
                    y_start = start
                end = int(data_dict['year_end']) - lag_year
                if end > y_end:
                    y_end = end

        # get covariate object list from database
        cov_list = Covariate.objects.filter(type=self, year__range=(y_start, y_end))

        # make a covariate dict
	cov_dict = {}
        if self.region_only:
	    for cov in cov_list:
	        cov_dict['%s+%s+%d' % (cov.region, cov.sex, cov.year)] = cov.value
        else:
	    for cov in cov_list:
	        cov_dict['%s+%s+%d' % (cov.iso3, cov.sex, cov.year)] = cov.value

        # make a list of the covariate values for the data dicts in the data_list
        cov_val_list = []

        # loop through data_list to add covariate to each data object's param
        missing = False
        for ii, data in enumerate(data_list):
            # check region or country
            if self.region_only:
                try:
                    region = data['region']
                except KeyError:
                    raise Exception('region is missing for region_only covariate in data row %d' % ii)
            else:
                try:
                    iso3 = data['country_iso3_code']
                except KeyError:
                    raise Exception('country_iso3_code is missing in data row %d' % ii)

            # check year start
            try:
                year_start = int(data['year_start'])
            except KeyError:
                raise Exception('year_start is missing in data dict %d' % ii)
            except ValueError:
                raise Exception('year_start is not an integer in data dict %d' % ii)

            # check year end
            try:
                year_end = int(data['year_end'])
            except KeyError:
                raise Exception('year_end is missing in data dict %d' % ii)
            except ValueError:
                raise Exception('year_end is not an integer in data dict %d' % ii)

            # add lag
            if transform_list == None:
                year_start = year_start - lag_year
                year_end = year_end  - lag_year

            # check sex
            try:
                sex = data['sex']
            except KeyError:
                raise Exception('sex is missing in data dict %d' % ii)
            if sex == 'all': 
                sex = 'total'  # if data is applied to males and females using sex == 'all',
                               # take the covariate value for sex == 'total'
            
            # make a list of the covariate values for the country/region, sex and year range of the data dict
            n = 0
            val = 0.
            if self.region_only:
                for year in range(year_start, year_end + 1):
                    try:
                        val = val + cov_dict['%s+%s+%d' % (region, sex, year)]
                    except KeyError:
                        continue
                    n = n + 1
            else:
                for year in range(year_start, year_end + 1):
                    try:
                        val = val + cov_dict['%s+%s+%d' % (iso3, sex, year)]
                    except KeyError:
                        continue
                    n = n + 1
            if n > 0:
                cov_val_list.append(val / n)
            else:
                cov_val_list.append('')
                print('covariate is not found for data dict %d' % ii)
                missing = True
            
        # assign the covariate to each data dict in the data list with transformation
        if transform_list == None:
            lag = str(lag_year)

            # loop through the data list
            for data, cov in zip(data_list, cov_val_list):
                data['lag-' + lag + '_' + self.slug] = cov
        else:
            # calculate shift and scale for normalized transformation
            if 'normalized' in transform_list:
                if self.variance == 0:
                    raise Exception('transform normalized failed due to variance is 0')
                shift = self.mean
                scale = math.sqrt(self.variance)
            
            # loop through the data list
            for data, cov in zip(data_list, cov_val_list):
                for transform_str in transform_list:
                    # handle original
                    if transform_str == 'original':
                        if cov == '':
                            data[self.slug] = ''
                        else:
                            data[self.slug] = cov

                    # handle log transform
                    if transform_str == 'log':
                        if cov == '':
                            data['log_' + self.slug] = ''
                        else:
                            if cov > 0:
                                data['log_' + self.slug] = math.log(cov)
                            else:
                                raise Exception('covariate value is not positive')

                    # handle logit transform
                    elif transform_str == 'logit':
                        if cov == '':
                            data['logit_' + self.slug] = ''
                        else:
                            if cov > 0 and cov < 1:
                                data['logit_' + self.slug] = math.log(cov / (1 - cov))
                            else:
                                raise Exception('covariate value is out of range (0, 1)')

                    # handle squared transform
                    elif transform_str == 'squared':
                        if cov == '':
                            data['squared_' + self.slug] = ''
                        else:
                            data['squared_' + self.slug] = cov * cov

                    # handle cubed transform
                    elif transform_str == 'cubed':
                        if cov == '':
                            data['cubed_' + self.slug] = ''
                        else:
                            data['cubed_' + self.slug] = cov * cov * cov

                    # handle normalized transform
                    elif transform_str == 'normalized':
                        if cov == '':
                            data['normalized_' + self.slug] = ''
                        else:
                            data['normalized_' + self.slug] = (cov - shift) / scale

        return data_list

class CovariateTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'uploader', 'upload_time', 'source', 'last_modified_time', 'description')

class CovariateAdmin(admin.ModelAdmin):
    list_display  = ('id', 'type', 'iso3', 'region', 'sex', 'age', 'year', 'value')
    list_filter   = ['sex', 'type',]
    search_fields = ['type', 'iso3', 'year',]

class Covariate(models.Model):
    """ Model for Covariate Data
    """
    type = models.ForeignKey(CovariateType)
    iso3 = models.CharField(max_length=3)
    year = models.IntegerField()
    sex = gbd.fields.SexField()
    country_year = models.CharField(max_length=8)
    value = models.FloatField()
    age = models.CharField(default='all',max_length=3)
    region = models.CharField(default='',max_length=28)

    def save(self, *args, **kwargs):
        self.country_year = '%s-%d' % (self.iso3, self.year)
        super(Covariate, self).save(*args, **kwargs)

    def __unicode__(self):
        return '%s: %s, %s, %s' % (self.type, self.iso3, self.year, self.get_sex_display(),)

    def get_absolute_url(self):
        return reverse('gbd.covariate_data_server.views.covariate_show', args=[self.type, self.iso3, self.sex, 'png'])
    

    def to_dict(self):
        return dict(type=self.type, iso3=self.iso3, year=self.year, sex=self.sex, value=self.value)

