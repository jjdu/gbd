""" Script to test the integrated systems model for disease

"""

# matplotlib backend setup
import matplotlib
matplotlib.use("AGG") 


from pylab import *
import pymc as mc
import inspect
    
from dismod3.disease_json import DiseaseJson
from dismod3 import neg_binom_model
import dismod3.utils
from dismod3.settings import gbd_regions

def test_single_rate():
    """ Test fit for a single low-noise data point"""

    # load model to test fitting
    dm = DiseaseJson(file('tests/single_low_noise.json').read())

    # fit empirical priors
    neg_binom_model.fit_emp_prior(dm, 'prevalence', '/dev/null')

    # compare fit to data
    check_emp_prior_fits(dm)
                
def summarize_acorr(x):
    x = x - np.mean(x, axis=0)
    print '*********************', inspect.stack()[1][3]
    for a in np.arange(0,101,10):
        acorr5 = dot(x[5:, a], x[:-5, a]) / dot(x[5:, a], x[5:, a])
        acorr10 = dot(x[10:, a], x[:-10, a]) / dot(x[10:, a], x[10:, a])
        print 'a: %d, c5: %.2f, c10: %.2f' % (a, acorr5*100, acorr10*100)
    print '*********************'    

def test_simulated_disease():
    """ Test fit for simulated disease data"""

    # load model to test fitting
    dm = DiseaseJson(file('tests/test_disease_1.json').read())

    # filter and noise up data
    cov = .5
    
    data = []
    for d in dm.data:
        d['truth'] = d['value']
        if dismod3.utils.clean(d['gbd_region']) == 'north_america_high_income':
            if d['data_type'] == 'all-cause mortality data':
                data.append(d)
            else:
                se = (cov * d['value'])
                d['value'] = mc.rtruncnorm(d['truth'], se**-2, 0, np.inf)
                d['age_start'] -= 5
                d['age_end'] = d['age_start']+9
                d['age_weights'] = np.ones(d['age_end']-d['age_start']+1)
                d['age_weights'] /= float(len(d['age_weights']))

                d['standard_error'] = se

                data.append(d)

    dm.data = data
    
    # fit empirical priors and compare fit to data
    from dismod3 import neg_binom_model
    for rate_type in 'prevalence incidence remission excess-mortality'.split():
        neg_binom_model.fit_emp_prior(dm, rate_type, '/dev/null')
        check_emp_prior_fits(dm)


    # fit posterior
    delattr(dm, 'vars')  # remove vars so that gbd_disease_model creates its own version
    from dismod3 import gbd_disease_model
    keys = dismod3.utils.gbd_keys(region_list=['north_america_high_income'],
                                  year_list=[1990], sex_list=['male'])
    gbd_disease_model.fit(dm, method='map', keys=keys, verbose=1)     ## first generate decent initial conditions
    gbd_disease_model.fit(dm, method='mcmc', keys=keys, iter=1000, thin=5, burn=5000, verbose=1, dbname='/dev/null')     ## then sample the posterior via MCMC


    print 'error compared to the noisy data (coefficient of variation = %.2f)' % cov
    check_posterior_fits(dm)


    for d in dm.data:
        d['value'] = d['truth']
        d['age_start'] += 5
        d['age_end'] = d['age_start']
        d['age_weights'] = np.ones(d['age_end']-d['age_start']+1)
        d['age_weights'] /= float(len(d['age_weights']))

    print 'error compared to the truth'
    check_posterior_fits(dm)

    return dm

def test_mesh_refinement():
    """ Compare fit for coarse and fine age mesh"""

    # load model and fit it
    dm1 = DiseaseJson(file('tests/single_low_noise.json').read())
    dm1.set_param_age_mesh(arange(0,101,20))
    from dismod3 import neg_binom_model
    neg_binom_model.fit_emp_prior(dm1, 'prevalence', '/dev/null')

    # load another copy and fit it with a finer age mesh
    dm2 = DiseaseJson(file('tests/single_low_noise.json').read())
    dm2.set_param_age_mesh(arange(0,101,5))
    from dismod3 import neg_binom_model
    neg_binom_model.fit_emp_prior(dm2, 'prevalence', '/dev/null')

    # compare fits
    p1 = dm1.get_mcmc('emp_prior_mean', dismod3.utils.gbd_key_for('prevalence', 'asia_southeast', 1990, 'male'))
    p2 = dm2.get_mcmc('emp_prior_mean', dismod3.utils.gbd_key_for('prevalence', 'asia_southeast', 1990, 'male'))
    print p1[::20]
    print p2[::20]
    assert np.all(abs(p1[::20] / p2[::20] - 1.) < .05), 'Prediction should be closer to data'


def test_linear_pattern():
    """ Test fit for empirical prior to data showing a linearly increasing age pattern"""

    # load model to test fitting
    dm = DiseaseJson(file('tests/single_low_noise.json').read())

    # create linear age pattern data
    import copy
    d = dm.data.pop()
    for a in range(10, 100, 20):
        d = copy.copy(d)
        d['age_start'] = a
        d['age_end'] = a
        d['parameter_value'] = .01*a
        d['value'] = .01*a
        dm.data.append(d)

    # fit empirical priors
    from dismod3 import neg_binom_model
    neg_binom_model.fit_emp_prior(dm, 'prevalence', '/dev/null')

    # compare fit to data
    check_emp_prior_fits(dm)


def test_increasing_prior():
    """ Test fit for empirical prior to data showing a linearly increasing age pattern with a fine age mesh"""

    # load model to test fitting
    dm = DiseaseJson(file('tests/single_low_noise.json').read())

    dm.params['global_priors']['increasing']['incidence']['age_end'] = 100

    # create linear age pattern data
    import copy
    d = dm.data.pop()
    for a in range(10, 100, 10):
        d = copy.copy(d)
        d['age_start'] = a
        d['age_end'] = a
        d['parameter_value'] = .01*a
        d['value'] = .01*a
        dm.data.append(d)

    # fit empirical priors
    from dismod3 import neg_binom_model
    neg_binom_model.fit_emp_prior(dm, 'prevalence', '/dev/null')

    # compare fit to data, and check that it is increasing
    check_emp_prior_fits(dm)
    assert np.all(np.diff(dm.get_mcmc('emp_prior_mean', dismod3.utils.gbd_key_for('prevalence', 'asia_southeast', 1990, 'male'))) >= 0), 'expert prior says increasing'

def test_triangle_pattern():
    """ Test fit for empirical prior to data showing a linearly increasing age pattern"""

    # load model to test fitting
    dm = DiseaseJson(file('tests/single_low_noise.json').read())

    # create linear age pattern data
    import copy
    d = dm.data.pop()
    for a in range(10, 100, 20):
        d = copy.copy(d)
        d['age_start'] = a
        d['age_end'] = a
        d['parameter_value'] = .01*min(a, 100-a)
        d['value'] = .01*min(a, 100-a)
        dm.data.append(d)

    # fit empirical priors
    from dismod3 import neg_binom_model
    neg_binom_model.fit_emp_prior(dm, 'prevalence', '/dev/null')

    # compare fit to data
    check_emp_prior_fits(dm)

    # fit posterior
    delattr(dm, 'vars')  # remove vars so that gbd_disease_model creates its own version
    from dismod3 import gbd_disease_model
    keys = dismod3.utils.gbd_keys(region_list=['asia_southeast'],
                                  year_list=[1990], sex_list=['male'])
    gbd_disease_model.fit(dm, method='map', keys=keys, verbose=1)     ## first generate decent initial conditions
    gbd_disease_model.fit(dm, method='mcmc', keys=keys, iter=1000, thin=5, burn=5000, verbose=1, dbname='/dev/null')     ## then sample the posterior via MCMC

    # compare fit to data
    check_posterior_fits(dm)


def test_dismoditis():
    """ Test fit for simple example"""

    # load model to test fitting
    dm = DiseaseJson(file('tests/dismoditis.json').read())
    for d in dm.data:
        d['standard_error'] = .01
    # fit empirical priors
    neg_binom_model.fit_emp_prior(dm, 'prevalence', '/dev/null')
    check_emp_prior_fits(dm)
    neg_binom_model.fit_emp_prior(dm, 'incidence', '/dev/null')
    check_emp_prior_fits(dm)
    neg_binom_model.fit_emp_prior(dm, 'excess-mortality', '/dev/null')
    check_emp_prior_fits(dm)

    # fit posterior where there is no data
    delattr(dm, 'vars')  # remove vars so that gbd_disease_model creates its own version
    from dismod3 import gbd_disease_model
    keys = dismod3.utils.gbd_keys(region_list=['north_america_high_income'],
                                  year_list=[1990], sex_list=['male'])
    gbd_disease_model.fit(dm, method='map', keys=keys, verbose=1)     ## first generate decent initial conditions
    gbd_disease_model.fit(dm, method='mcmc', keys=keys, iter=1000, thin=5, burn=5000, verbose=1, dbname='/dev/null')     ## then sample the posterior via MCMC
    check_posterior_fits(dm)
    
    # check that prevalence is smooth near age zero
    prediction = dm.get_mcmc('mean', 'prevalence+north_america_high_income+1990+male')
    assert prediction[1]-prediction[0] < .01, 'prediction should be smooth near zero'

def test_hep_c():
    """ Test fit for subset of hep_c data

    data is filtered to include only prevalence with
    region == 'europe_western' and sex == 'all'
    """

    # load model to test fitting
    dm = DiseaseJson(file('tests/hep_c_europe_western.json').read())

    # fit empirical priors
    neg_binom_model.fit_emp_prior(dm, 'prevalence', '/dev/null')

    # fit posterior
    delattr(dm, 'vars')  # remove vars so that gbd_disease_model creates its own version
    from dismod3 import gbd_disease_model
    keys = dismod3.utils.gbd_keys(region_list=['europe_western'],
                                  year_list=[1990], sex_list=['male'])
    gbd_disease_model.fit(dm, method='map', keys=keys, verbose=1)     ## first generate decent initial conditions
    gbd_disease_model.fit(dm, method='mcmc', keys=keys, iter=1000, thin=5, burn=5000, verbose=1, dbname='/dev/null')     ## then sample the posterior via MCMC

    # check that prevalence is smooth near age zero
    prediction = dm.get_mcmc('mean', 'prevalence+europe_western+1990+male')
    print prediction
    return dm
    assert prediction[100] < .1, 'prediction should not shoot up in oldest ages'

def test_opi():
    """ Test fit for subset of opi_dep data

    data is filtered to include only data for
    region == 'europe_central' and sex == 'male'
    """

    # load model to test fitting
    dm = DiseaseJson(file('tests/opi.json').read())

    dm.params['global_priors']['decreasing']['prevalence']['age_start'] = 60
    dm.params['global_priors']['decreasing']['prevalence']['age_end'] = 100

    fit_model(dm, 'europe_central', 1990, 'male')

    # check that prevalence is smooth near age zero
    prediction = dm.get_mcmc('mean', 'prevalence+europe_central+1990+male')
    print prediction
    assert prediction[80] > prediction[100], 'prediction should decrease at oldest ages'

    return dm

def test_ihd():
    """ Test fit for subset of ihd data

    data is filtered to include only data for
    region == 'europe_western' and sex == 'male'
    """

    # load model to test fitting
    dm = DiseaseJson(file('tests/ihd.json').read())

    fit_model(dm, 'europe_western', 1990, 'male')

    # check that prevalence is smooth around age 90
    prediction = dm.get_mcmc('mean', 'prevalence+europe_western+1990+male')
    print prediction
    assert prediction[89]/prediction[90] < .05, 'prediction should not change greatly at age 90'

    return dm

def fit_model(dm, region, year, sex):
    """ Fit the empirical priors, and the posterior for a specific region/year/sex
    """
    
    # fit empirical priors
    for rate_type in 'prevalence incidence remission excess-mortality'.split():
        neg_binom_model.fit_emp_prior(dm, rate_type, '/dev/null')

    # fit posterior
    delattr(dm, 'vars')  # remove vars so that gbd_disease_model creates its own version
    from dismod3 import gbd_disease_model
    keys = dismod3.utils.gbd_keys(region_list=[region],
                                  year_list=[year], sex_list=[sex])
    gbd_disease_model.fit(dm, method='map', keys=keys, verbose=1)     ## first generate decent initial conditions
    gbd_disease_model.fit(dm, method='mcmc', keys=keys, iter=1000, thin=5, burn=5000, verbose=1, dbname='/dev/null')     ## then sample the posterior via MCMC



def test_dismoditis_w_high_quality_data():
    """ Test fit for simple example"""

    # load model to test fitting
    dm = DiseaseJson(file('tests/dismoditis.json').read())

    # fit empirical priors
    neg_binom_model.fit_emp_prior(dm, 'prevalence', '/dev/null')
    check_emp_prior_fits(dm)
    neg_binom_model.fit_emp_prior(dm, 'incidence', '/dev/null')
    check_emp_prior_fits(dm)
    neg_binom_model.fit_emp_prior(dm, 'excess-mortality', '/dev/null')
    check_emp_prior_fits(dm)

    # fit posterior where there is data
    delattr(dm, 'vars')  # remove vars so that gbd_disease_model creates its own version
    from dismod3 import gbd_disease_model
    keys = dismod3.utils.gbd_keys(region_list=['asia_southeast'],
                                  year_list=[1990], sex_list=['male'])
    gbd_disease_model.fit(dm, method='map', keys=keys, verbose=1)     ## first generate decent initial conditions
    gbd_disease_model.fit(dm, method='mcmc', keys=keys, iter=1000, thin=5, burn=5000, verbose=1, dbname='/dev/null')     ## then sample the posterior via MCMC

    # compare fit to data
    check_posterior_fits(dm)

    return dm
    


def test_dismoditis_wo_prevalence():
    """ Test fit for simple example"""

    # load model to test fitting
    dm = DiseaseJson(file('tests/dismoditis.json').read())

    # remove all prevalence data
    dm.data = [d for d in dm.data if d['parameter'] != 'prevalence data']

    # fit empirical priors
    neg_binom_model.fit_emp_prior(dm, 'incidence', '/dev/null')
    check_emp_prior_fits(dm)
    neg_binom_model.fit_emp_prior(dm, 'excess-mortality', '/dev/null')
    check_emp_prior_fits(dm)

    # fit posterior
    delattr(dm, 'vars')  # remove vars so that gbd_disease_model creates its own version
    from dismod3 import gbd_disease_model
    keys = dismod3.utils.gbd_keys(region_list=['asia_southeast'],
                                  year_list=[1990], sex_list=['male'])
    #gbd_disease_model.fit(dm, method='map', keys=keys, verbose=1)     ## first generate decent initial conditions
    gbd_disease_model.fit(dm, method='mcmc', keys=keys, iter=1000, thin=5, burn=5000, verbose=1, dbname='/dev/null')     ## then sample the posterior via MCMC

    # compare fit to data
    check_posterior_fits(dm)


def check_posterior_fits(dm):
    are = []
    coverage = []
    print '*********************', inspect.stack()[1][3]
    for d in dm.data:
        data_prediction = []

        type = d['data_type'].replace(' data', '')
        key = dismod3.utils.gbd_key_for(type, d['gbd_region'], d['year_start'], d['sex'])
        covariates_dict = dm.get_covariates()
        model_vars = dm.vars.get(key)
        if not model_vars:
            continue
        alpha = model_vars['region_coeffs']
        beta = model_vars['study_coeffs']
        for gamma in model_vars['age_coeffs'].trace():
            mu = neg_binom_model.predict_region_rate(key, alpha, beta, gamma, covariates_dict, model_vars['bounds_func'], dm.get_estimate_age_mesh())

            data_prediction.append(dismod3.utils.rate_for_range(mu,
                                                                arange(d['age_start'], d['age_end']+1),
                                                                d['age_weights']))
        
        # test distance of predicted data value from observed data value
        are.append(abs(100 * (mean(data_prediction) / dm.value_per_1(d) - 1.)))

        # coverage interval type:
        cov_interval_pct = .95
        lb, ub = mc.utils.hpd(array(data_prediction), 1-cov_interval_pct)
        coverage.append((dm.value_per_1(d) >= lb) and (dm.value_per_1(d) <= ub))
        print type, d['age_start'], dm.value_per_1(d), mean(data_prediction), are[-1], coverage[-1]
        #assert abs((.01 + data_prediction) / (.01 + dm.value_per_1(d)) - 1.) < 1., 'Prediction should be closer to data'
    print '*********************\n\n\n\n\n'
    return are, coverage


def check_emp_prior_fits(dm):
    are = []
    # compare fit to data
    print '*********************', inspect.stack()[1][3]
    for d in dm.vars['data']:
        type = d['data_type'].replace(' data', '')
        prior = dm.get_empirical_prior(type)
        prediction = neg_binom_model.predict_country_rate(dismod3.utils.gbd_key_for(type, d['gbd_region'],
                                                                                    (d['year_start'] < 1997) and 1990 or 2005, d['sex']),
                                                          d['country_iso3_code'],
                                                          prior['alpha'], prior['beta'], prior['gamma'], dm.get_covariates(), lambda f, age: f, arange(101))
        data_prediction = dismod3.utils.rate_for_range(prediction,
                                                       arange(d['age_start'], d['age_end']+1),
                                                       d['age_weights'])

        # test distance of predicted data value from observed data value
        are.append(abs(100 * (data_prediction / dm.value_per_1(d) - 1.)))
        print type, d['age_start'], dm.value_per_1(d), data_prediction, are[-1]
        #assert abs((.001 + data_prediction) / (.001 + dm.value_per_1(d)) - 1.) < .05, 'Prediction should be closer to data'
    print 'median absolue relative error:', median(are)
    print '*********************\n\n\n\n\n'
    return are

def test_save_country_level_posterior():
    """ Test exporting country level posterior output """
    # load model to test fitting
    dm = DiseaseJson(file('tests/dismoditis.json').read())

    # fit posterior where there is data
    from dismod3 import gbd_disease_model
    keys = dismod3.utils.gbd_keys(region_list=['asia_southeast'],
                                  year_list=[1990], sex_list=['male'])
    gbd_disease_model.fit(dm, method='map', keys=keys, verbose=1)     ## first generate decent initial conditions
    gbd_disease_model.fit(dm, method='mcmc', keys=keys, iter=100, thin=1, burn=0, verbose=1, dbname='/dev/null')     ## then sample the posterior via MCMC

    # make a rate_type_list
    rate_type_list = ['incidence', 'prevalence', 'remission', 'excess-mortality']

    # job working directory
    job_wd = dismod3.settings.JOB_WORKING_DIR % dm.id

    # directory to save the file
    dir = job_wd + '/posterior/country_level_posterior_dm-' + str(dm.id) + '/'
    import os
    from shutil import rmtree
    if os.path.exists(dir):
        rmtree(dir)
    os.makedirs(dir)

    # save country level posterior in csv file
    from fit_posterior import save_country_level_posterior
    save_country_level_posterior(dm, 'asia_southeast', '1990', 'male', rate_type_list)

    # zip the csv file
    from upload_fits import zip_country_level_posterior_files
    zip_country_level_posterior_files(dm.id)

def test_covariates():
    """ test function covariates() in neg_binom_model """
    d = {'parameter': 'Prevalence',
         'gbd_region': 'Asia, Southeast',
         'year_start': '1990',
         'year_end': '2005',
         'sex': 'male',
         'self_report': 0.5,
         'gdp': 0.8}
    
    covariates_dict = {'Study_level': {'Self report': {'rate': {'value': 1}, 'value': {'value': 0.5}, 'types': {'value': ['prevalence']}}},
                       'Country_level': {'GDP': {'rate': {'value': 1}, 'value': {'value': 0.8}, 'types': {'value': ['prevalence', 'incidence']}},
                                         '%_urban': {'rate': {'value': 1}, 'value': {'value': 0.6}, 'types': {'value': ['incidence', 'remission']}}}}

    Xa, Xb = neg_binom_model.covariates(d, covariates_dict)

    ok = 0
    if len(Xa) != len(gbd_regions) + 2:
        ok += 1
        print 'Xa length is wrong'

    for ii, r in enumerate(gbd_regions):
        if dismod3.utils.clean(d['gbd_region']) == dismod3.utils.clean(r):
            if Xa[ii] != 1.:
                ok += 1
                print 'Xa for specified region is not 1'
        else:
            if Xa[ii] != 0.:
                ok += 1
                print 'Xa for non-specified region is not 0'

    if Xa[ii + 1] != .1 * (.5 * (float('1990') + float('2005')) - 1997):
        ok += 1
        print 'Xa for year is incorrect'

    if Xa[ii + 2] != 0.5:
        ok += 1
        print 'Xa for sex is incorrect'

    if len(Xb) != 2:
        ok += 1
        print 'Xb length is wrong'

    if Xb[0] != d['self_report']:
        ok += 1
        print 'Xb for study level covariate is incorrect'
    if Xb[1] != d['gdp']:
        ok += 1
        print 'Xb for country level covariate is incorrect'

    print str(ok) + ' errors were found in neg_binom_model.covariates'

if __name__ == '__main__':
    for test in [
        test_opi,
        test_hep_c,
        test_dismoditis,
        test_dismoditis_w_high_quality_data,
        test_mesh_refinement,
        test_increasing_prior,
        test_dismoditis_wo_prevalence,
        test_triangle_pattern,
        test_linear_pattern,
        test_single_rate,
        test_save_country_level_posterior,
        test_covariates,
        ]:
        try:
            test()
        except AssertionError, e:
            print 'TEST FAILED', test
            print e
