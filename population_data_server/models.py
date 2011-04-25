from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

import numpy as np
from pymc import gp
import simplejson as json
import types

import gbd.fields
import dismod3
from dismod3.utils import MAX_AGE

class PopulationAdmin(admin.ModelAdmin):
    list_display  = ('id', 'region', 'sex', 'year',)
    list_filter   = ['sex', 'region', ]
    search_fields = ['region', 'sex', 'year',]

class Population(models.Model):
    """ Model for Population Data

    Parameters
    ----------
    region : str
    year : int
    sex : str
    params_json : str
        this is an place to store any relevant information in a
        dictionary. the dictionary is expected to contain::

            params['mesh'] = midpoints of age intervals for population size
            params['vals'] = average value for each age interval
            params['interval_start'] = left endpoint of age intervals (optional)
            params['interval_length'] = width of age intervals (optional)
    """
    region = models.CharField(max_length=200)
    year = models.IntegerField()
    sex = gbd.fields.SexField()
    params_json = models.TextField(default=json.dumps({}))

    def __init__(self, *args, **kwargs):
        super(Population, self).__init__(*args, **kwargs)
        try:
            self.params = json.loads(self.params_json)
        except ValueError:
            self.params = {}

    def cache_params(self):
        """ Store the params dict as json text

        Notes
        -----
        This must be called before population.save() to preserve any
        changes to params dict

        I do it this way, instead of automatically in the save method
        to permit direct json editing in the admin interface
        """
        self.params_json = json.dumps(self.params)

    def __unicode__(self):
        return '%s, %s, %s' % (self.region, self.year, self.get_sex_display(),)

    def get_absolute_url(self):
        return reverse('gbd.population_data_server.views.population_show', args=(self.id,))

    def interpolate(self, age_range):
        self.params['mesh'][0] = 0.0
        in_mesh = self.params['mesh'] + [ MAX_AGE ]
        values = self.params['vals'] + [ 0. ]
        out_mesh = age_range

        from scipy.interpolate import interp1d
        f = interp1d(in_mesh, values, kind='linear')
        wts = f(out_mesh)

        return wts



    def gaussian_process(self):
        """ return a PyMC Gaussian Process mean and covariance to interpolate
        the population-by-age mesh/value data
        """
        # TODO: make this evaluate the function on arange(MAX_AGE) and store the results in the db for better performance
        M, C = uninformative_prior_gp(c=0.,  diff_degree=2., amp=10., scale=200.)
        gp.observe(M, C, self.params['mesh'] + [ MAX_AGE ], self.params['vals'] + [ 0. ], 0.0)
    
        return M, C

def const_func(x, c):
     """ A constant function, f(x) = c

     To be used as a non-informative prior on a Gaussian process.

     Example
     -------
     >>> const_func([1,2,3], 17.0)
     array([ 17., 17., 17.])
     """
     return np.zeros(np.shape(x)) + c

def uninformative_prior_gp(c=-10.,  diff_degree=2., amp=100., scale=200.):
     """ Uninformative Mean and Covariance Priors
     Parameters
     ----------
     c : float, the prior mean
     diff_degree : float, the prior on differentiability (2 = twice differentiable?)
     amp : float, the prior on the amplitude of the Gaussian Process
     scale : float, the prior on the scale of the Gaussian Process

     Results
     -------
     M, C : mean and covariance objects
       this constitutes an uninformative prior on a Gaussian Process
       with a euclidean Matern covariance function
     """
     M = gp.Mean(const_func, c=c)
     C = gp.Covariance(gp.matern.euclidean, diff_degree=diff_degree,
                       amp=amp, scale=scale)

     return M,C

def calculate_age_weights(data_list):
    """ Calculate and cache age_weights vector in self.params to avoid
    repeatedly making the database queries required to compute it.        

    Parameters:
    -----------
      data_list : list
        list of data dict in that the keys country_iso3_code, age_start, age_end,
        year-start, year_end, parameter and sex are required.   
 
    Return:
    -------
      list of data dicts with added age_weights.
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

    # find year range in the data_list
    y_start = 2050
    y_end = 0
    for data_dict in data_list:
        start = int(data_dict['year_start'])
        if start < y_start:
            y_start = start
        end = int(data_dict['year_end'])
        if end > y_end:
            y_end = end

    # get a potentially useful population object list from database
    pop_list = Population.objects.filter(year__range=(y_start, y_end))

    # make a population dict
    pop_dict = {}
    for pop in pop_list:
	pop_dict['%s+%s+%d' % (pop.region, pop.sex, pop.year)] = pop

    # loop through data_list to add covariate to each data object's param
    for ii, data_dict in enumerate(data_list):

        age_start= int(data_dict['age_start'])
        age_end = int(data_dict['age_end'])

        # deal with 'missing' data at end of age interval
        if age_end == dismod3.MISSING:
            age_end = dismod3.MAX_AGE - 1

        # sanity check
        if age_end == age_start:
            # don't need to look in database for a single year
            pop_vals = [ 1. ]
        else:
            a = range(age_start, age_end + 1)

            if data_dict['parameter'].startswith('prevalence') or data_dict['parameter'].startswith('incidence'):
                # use population structure for age weights
                # SPECIAL CASE: sex == 'all' will be applied to males and females, so use pop structure for total
                if data_dict['sex'] == 'all':
                    sex = 'total'
                else:
                    sex = data_dict['sex']

                # find relevant populations for the region, sex and year range of the data dict
                relevant_populations = []
                year_start = int(data_dict['year_start'])
                year_end = int(data_dict['year_end'])
                iso3 = data_dict['country_iso3_code']
                for year in range(year_start, year_end + 1):
                    try:
                        relevant_populations.append(pop_dict['%s+%s+%d' % (iso3, sex, year)])
                    except KeyError:
                        continue

                # find total age weights for the relavant populations
                if len(relevant_populations) == 0:
                    print("WARNING: Population for %s-%d-%d-%s not found, "
                           + "using uniform distribution instead of age-weighted "
                           + "distribution (Data_id=%d)" ) % (iso3, year_start, year_end, sex, ii)
                    total = np.ones(len(a))
                else:
                    total = np.zeros(len(a))
                    for population in relevant_populations:
                        total += population.interpolate(a)

            else: # don't use population structure for age weights
                total = np.ones(len(a))
                
            pop_vals = np.maximum(dismod3.NEARLY_ZERO, total)
            pop_vals /= sum(pop_vals)

        data_dict['age_weights'] = list(pop_vals)
       
    return data_list

