""" Script to fit the North America High Income Hep C data for 1990

"""

# matplotlib backend setup
import matplotlib
matplotlib.use("AGG") 


from pylab import *
import pymc as mc
    
from dismod3.disease_json import DiseaseJson
from dismod3 import neg_binom_model
import dismod3.utils
import test_model
import dismod3

def hep_c_fit(regions, prediction_years, data_year_start=-inf, data_year_end=inf, egypt_flag=False):
    """ Fit prevalence for regions and years specified """
    print '\n***************************\nfitting %s for %s (using data from years %f to %f)' % (regions, prediction_years, data_year_start, data_year_end)
    
    ## load model to fit
    #dm = DiseaseJson(file('tests/hep_c.json').read())
    dm = dismod3.get_disease_model(8021)
    ## adjust the expert priors
    dm.params['global_priors']['heterogeneity']['prevalence'] = 'Very'
    dm.params['global_priors']['smoothness']['prevalence']['amount'] = 'Slightly'
    # TODO: construct examples of adjusting other covariates
    # ipdb> dm.params['global_priors'].keys()
    # [u'increasing', u'unimodal', u'level_bounds', u'y_maximum', u'note', u'level_value', u'decreasing', u'parameter_age_mesh', u'heterogeneity', u'smoothness']
    #ipdb> dm.params['global_priors']['smoothness']['prevalence']
    #{u'age_start': 0, u'amount': u'Moderately', u'age_end': 100}

    # include a study-level covariate for 'bias'
    covariates_dict = dm.get_covariates()
    covariates_dict['Study_level']['bias']['rate']['value'] = 1
    # TODO: construct additional examples of adjusting covariates

    ## select relevant prevalence data
    # TODO: streamline data selection functions
    if egypt_flag:
        dm.data = [d for d in dm.data if d['country_iso3_code'] == 'EGY']
    else:
        dm.data = [d for d in dm.data if
                   dismod3.utils.clean(d['gbd_region']) in regions
                   and float(d['year_end']) >= data_year_start
                   and float(d['year_start']) <= data_year_end
                   and d['country_iso3_code'] != 'EGY']

    ## create, fit, and save rate model
    dm.vars = {}

    keys = dismod3.utils.gbd_keys(type_list=['prevalence'],
                                  region_list=regions,
                                  year_list=prediction_years)
    # TODO: consider how to do this for models that use the complete disease model
    # TODO: consider adding hierarchical similarity priors for the male and female models
    k0 = keys[0]  # looks like k0='prevalence+asia_south+1990+male'
    dm.vars[k0] = neg_binom_model.setup(dm, k0, dm.data)

    dm.mcmc = mc.MCMC(dm.vars)
    dm.mcmc.sample(iter=50000, burn=25000, thin=50, verbose=1)

    # make map object so we can compute AIC and BIC
    dm.map = mc.MAP(dm.vars)
    dm.map.fit()

    for k in keys:
        # save the results in the disease model
        dm.vars[k] = dm.vars[k0]
        if egypt_flag:
            neg_binom_model.countries_for['egypt'] = ['EGY']  # HACK: to treat egypt as its own region

        neg_binom_model.store_mcmc_fit(dm, k, dm.vars[k])

        # check autocorrelation to confirm chain has mixed
        test_model.summarize_acorr(dm.vars[k]['rate_stoch'].trace())

        # generate plots of results
        dismod3.tile_plot_disease_model(dm, [k], defaults={'ymax':.15, 'alpha': .5})
        dm.savefig('dm-%d-posterior-%s.%f.png' % (dm.id, k, random()))

    # summarize fit quality graphically, as well as parameter posteriors
    dismod3.plotting.plot_posterior_predicted_checks(dm, k0)
    dm.savefig('dm-%d-check-%s.%f.png' % (dm.id, k0, random()))
    dismod3.post_disease_model(dm)
    return dm

if __name__ == '__main__':
    dm = hep_c_fit(['egypt'], [1990, 2005], egypt_flag=True)

    dm = hep_c_fit('caribbean latin_america_tropical latin_america_andean latin_america_central latin_america_southern'.split(), [1990, 2005])
    dm = hep_c_fit('sub-saharan_africa_central sub-saharan_africa_southern sub-saharan_africa_west'.split(), [1990, 2005])
    dm = hep_c_fit('europe_eastern europe_central asia_central'.split(), [1990, 2005])
    
    for r in 'north_africa_middle_east asia_east asia_south asia_southeast australasia oceania sub-saharan_africa_east asia_pacific_high_income'.split():
        dm = hep_c_fit([r], [1990, 2005])

    for r in 'north_america_high_income europe_western '.split():
        dm = hep_c_fit([r], [1990], data_year_end=1997)
        dm = hep_c_fit([r], [2005], data_year_start=1997)
