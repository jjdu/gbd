""" Negative Binomial Model for a generic epidemological parameter

The Negative Binomial Model represents data for age-specific rates
according to the following formula::

    Y_i ~ NegativeBinomial(\mu_i N_i, \delta_i) / N_i
    \mu_i ~ \sum _{a = a_{i0}} ^{a_{i1}} w(a) \mu_{i, a}
    \log \mu_{i, a} = \alpha_{r_i} + \alpha_{s_i} + \alpha_{y_i} + \gamma_a + \beta^T X_i

Here Y_i, \N_i, a_{i0}, a_{i1}, r_i, s_i, y_i, and X_i are the
value, effective sample size, age range, region, sex, year,
and study-level covariates corresponding to a single age-range value
from a single study.  \alpha, \beta, \gamma, and \delta are parameters
(fixed effects and over-dispersion) that will be estimated from the
data.
"""

import numpy as np
import pymc as mc
import sys

import dismod3
from dismod3.utils import debug, interpolate, rate_for_range, indices_for_range, generate_prior_potentials, gbd_regions, clean, type_region_year_sex_from_key
from dismod3.settings import MISSING, NEARLY_ZERO, MAX_AGE


def fit_emp_prior(dm, param_type):
    """ Generate an empirical prior distribution for a single disease parameter

    Parameters
    ----------
    dm : dismod3.DiseaseModel
      The object containing all the data, (hyper)-priors, and additional
      information (like input and output age-mesh).

    param_type : str, one of 'incidence', 'prevalence', 'remission', 'excess-mortality'
      The disease parameter to work with

    Notes
    -----
    The results of this fit are stored in the disease model's params
    hash for use when fitting multiple paramter types together

    Example
    -------
    $ python2.5 gbd_fit.py 231 -t incidence
    """

    data = [d for d in dm.data if clean(d['data_type']).find(param_type) != -1 and not d.get('ignore')]
    dm.calc_effective_sample_size(data)

    dm.clear_empirical_prior()
    dm.fit_initial_estimate(param_type, data)

    dm.vars = setup(dm, param_type, data)

    # don't do anything if there is no data for this parameter type
    if len(dm.vars['data']) == 0:
        return

    debug('i: %s' % ', '.join(['%.2f' % x for x in dm.get_initial_value(param_type)[::10]]))
    sys.stdout.flush()
    
    # fit the model
    dm.na = mc.NormApprox(dm.vars)

    dm.na.fit(method='fmin_powell', iterlim=20, tol=.001, verbose=1)
    dm.na.sample(1000, verbose=1)

#     dm.map = mc.MAP(dm.vars)
#     try:
#         dm.map.fit(method='fmin_powell', iterlim=500, tol=.1, verbose=1)
#     except KeyboardInterrupt:
#         debug('User halted optimization routine before optimal value found')
#     sys.stdout.flush()

#     # make pymc warnings go to stdout
#     mc.warnings.warn = sys.stdout.write
#     dm.mcmc = mc.MCMC(dm.vars)
#     dm.mcmc.sample(10000, burn=5000, thin=5, verbose=1)

    dm.vars['region_coeffs'].value = dm.vars['region_coeffs'].stats()['mean']
    dm.vars['study_coeffs'].value = dm.vars['study_coeffs'].stats()['mean']
    dm.vars['age_coeffs_mesh'].value = dm.vars['age_coeffs_mesh'].stats()['mean']
    dm.vars['log_dispersion'].value = dm.vars['log_dispersion'].stats()['mean']

    alpha = dm.vars['region_coeffs'].stats()['mean']
    beta = dm.vars['study_coeffs'].stats()['mean']
    gamma_mesh = dm.vars['age_coeffs_mesh'].stats()['mean']
    debug('a: %s' % ', '.join(['%.2f' % x for x in alpha]))
    debug('b: %s' % ', '.join(['%.2f' % x for x in beta]))
    debug('g: %s' % ', '.join(['%.2f' % x for x in gamma_mesh]))
    debug('d: %.2f' % dm.vars['dispersion'].stats()['mean'])
    debug('m: %s' % ', '.join(['%.2f' % x for x in dm.vars['rate_stoch'].stats()['mean'][::10]]))
    covariates_dict = dm.get_covariates()
    X = covariates(data[0], covariates_dict)
    debug('p: %s' % ', '.join(['%.2f' % x for x in predict_rate(X, alpha, beta, gamma_mesh)]))
    # save the results in the param_hash
    prior_vals = dict(
        alpha=list(dm.vars['region_coeffs'].stats()['mean']),
        beta=list(dm.vars['study_coeffs'].stats()['mean']),
        gamma=list(dm.vars['age_coeffs'].stats()['mean']),
        delta=float(dm.vars['dispersion'].stats()['mean']))

    prior_vals.update(
        sigma_alpha=list(dm.vars['region_coeffs'].stats()['standard deviation']),
        sigma_beta=list(dm.vars['study_coeffs'].stats()['standard deviation']),
        sigma_gamma=list(dm.vars['age_coeffs'].stats()['standard deviation']),
        sigma_delta=float(dm.vars['dispersion'].stats()['standard deviation']))
    dm.set_empirical_prior(param_type, prior_vals)

    dispersion = prior_vals['delta']
    median_sample_size = np.median([values_from(dm, d)[3] for d in dm.vars['data']] + [1000])
    debug('median effective sample size: %.1f' % median_sample_size)
    for r in dismod3.gbd_regions:
        for y in dismod3.gbd_years:
            for s in dismod3.gbd_sexes:
                key = dismod3.gbd_key_for(param_type, r, y, s)
                mu = predict_region_rate(key,
                                         alpha=prior_vals['alpha'],
                                         beta=prior_vals['beta'],
                                         gamma=prior_vals['gamma'],
                                         covariates_dict=covariates_dict)
                dm.set_initial_value(key, mu)
                dm.set_mcmc('emp_prior_mean', key, mu)

def store_mcmc_fit(dm, key, rate_stoch):
    """ Store the parameter estimates generated by an MCMC fit of the
    beta-binomial model in the disease_model object, keyed by key
    
    Parameters
    ----------
    dm : dismod3.DiseaseModel
      the object containing all the data, priors, and additional
      information (like input and output age-mesh)

    key : str

    rate_stoch : PyMC stochastic or deterministic variable

    Results
    -------
    Save a sketch of the distribution of rate_stoch keyed by key.

    Notes
    -----
    This method will be used by other models that have beta binomial
    parts as building blocks, so don't simplify the parameters, at
    least not without thinking about where else the function might
    need to be used
    """
    rate = rate_stoch.trace()
    trace_len = len(rate)
    age_len = len(dm.get_estimate_age_mesh())
    
    sr = []
    # TODO: use rate_stoch.stats() to get these statistics, instead of roll-me-own
    # TODO: predict at the country level, and then average for regional value
    for ii in xrange(age_len):
        sr.append(sorted(rate[:,ii]))
    dm.set_mcmc('lower_ui', key, [sr[ii][int(.025*trace_len)] for ii in xrange(age_len)])
    dm.set_mcmc('median', key, [sr[ii][int(.5*trace_len)] for ii in xrange(age_len)])
    dm.set_mcmc('upper_ui', key, [sr[ii][int(.975*trace_len)] for ii in xrange(age_len)])
    dm.set_mcmc('mean', key, np.mean(rate, 0))

    if dm.vars[key].has_key('dispersion'):
        dm.set_mcmc('dispersion', key, dm.vars[key]['dispersion'].stats()['quantiles'].values())

def covariates(d, covariates_dict):
    """ extract the covariates from a data point as a vector;

    Xa represents region-level covariates:
      Xa[0],...,Xa[21] = region indicators
      Xa[22] = .1*(year-1997)
      Xa[23] = .5 if sex == 'male', -.5 if sex == 'female'
    Xb represents study-level covariates, according to the covariates_dict
      
    """
    Xa = np.zeros(len(gbd_regions) + 2)
    for ii, r in enumerate(gbd_regions):
        if clean(d['gbd_region']) == clean(r):
            Xa[ii] = 1.

    Xa[ii+1] = .1 * (.5 * (float(d['year_start']) + float(d['year_end'])) - 1997)

    if clean(d['sex']) == 'male':
        Xa[ii+2] = .5
    elif clean(d['sex']) == 'female':
        Xa[ii+2] = -.5
    else:
        Xa[ii+2] = 0.

    Xb = []
    for level in ['Study_level', 'Country_level']:
        for k in sorted(covariates_dict[level]):
            if covariates_dict[level][k]['rate']['value'] == 1:
                Xb.append(float(d.get(clean(k), 0.)))
    if Xb == []:
        Xb = [0.]
    return Xa, Xb


from dismod3.utils import clean
import csv
import settings
countries_for = dict(
    [[clean(x[0]), x[1:]] for x in csv.reader(open(settings.CSV_PATH + 'country_region.csv'))]
    )
population_by_age = dict(
    [[(d['Country Code'], d['Year'], d['Sex']),
      [float(d['Age %d Population' % i]) for i in range(MAX_AGE)]] for d in csv.DictReader(open(settings.CSV_PATH + 'population.csv'))
     if len(d['Country Code']) == 3]
    )

def regional_average(value_dict, region):
    """ handle region = iso3 code or region = clean(gbd_region)"""
    # TODO: make regional average weighted by population
    return np.mean([value_dict[iso3] for iso3 in countries_for[region] if value_dict.has_key(iso3)])

def regional_covariates(key, covariates_dict):
    """ form the covariates for a gbd key"""
    t,r,y,s = type_region_year_sex_from_key(key)

    d = {'gbd_region': r,
         'year_start': y,
         'year_end': y,
         'sex': s}
    for level in ['Study_level', 'Country_level']:
        for k in covariates_dict[level]:
            if k == 'none':
                continue
            d[clean(k)] = covariates_dict[level][k]['value']['value']
            if d[clean(k)] == 'Country Specific Value':
                d[clean(k)] = regional_average(covariates_dict[level][k]['defaults'], r)
            else:
                d[clean(k)] == float(d[clean(k)] or 0.)

    return covariates(d, covariates_dict)

def country_covariates(key, iso3, covariates_dict):
    """ form the covariates for a gbd key"""
    t,r,y,s = type_region_year_sex_from_key(key)

    d = {'gbd_region': r,
         'year_start': y,
         'year_end': y,
         'sex': s}
    for level in ['Study_level', 'Country_level']:
        for k in covariates_dict[level]:
            if k == 'none':
                continue
            d[clean(k)] = covariates_dict[level][k]['value']['value']
            if d[clean(k)] == 'Country Specific Value':
                d[clean(k)] = covariates_dict[level][k]['defaults'].get(iso3, 0.)
            else:
                d[clean(k)] = float(d[clean(k)] or 0.)

    return covariates(d, covariates_dict)

def predict_rate(X, alpha, beta, gamma):
    """ Calculate logit(Y) = gamma + X * beta"""
    Xa, Xb = X
    return np.exp(np.dot(Xa, alpha) + np.dot(Xb, beta) + gamma)

def predict_country_rate(key, iso3, alpha, beta, gamma, covariates_dict):
    return predict_rate(country_covariates(key, iso3, covariates_dict), alpha, beta, gamma)

def predict_region_rate(key, alpha, beta, gamma, covariates_dict):
    t,r,y,s = type_region_year_sex_from_key(key)
    region_rate = np.zeros(len(gamma))
    total_pop = np.zeros(len(gamma))
    for iso3 in countries_for[r]:
        region_rate += predict_country_rate(key, iso3, alpha, beta, gamma, covariates_dict) * population_by_age.get((iso3,y,s), 1.)
        total_pop += population_by_age.get((iso3, y, s), 1.)
    return region_rate / total_pop
    
def setup(dm, key, data_list, rate_stoch=None, emp_prior={}):
    """ Generate the PyMC variables for a negative-binomial model of
    a single rate function

    Parameters
    ----------
    dm : dismod3.DiseaseModel
      the object containing all the data, priors, and additional
      information (like input and output age-mesh)
      
    key : str
      the name of the key for everything about this model (priors,
      initial values, estimations)

    data_list : list of data dicts
      the observed data to use in the negative binomial liklihood function

    rate_stoch : pymc.Stochastic, optional
      a PyMC stochastic (or deterministic) object, with
      len(rate_stoch.value) == len(dm.get_estimation_age_mesh()).
      This is used to link rate stochs into a larger model,
      for example.

    emp_prior : dict, optional
      the empirical prior dictionary, retrieved from the disease model
      if appropriate by::

          >>> t, r, y, s = type_region_year_sex_from_key(key)
          >>> emp_prior = dm.get_empirical_prior(t)

    Results
    -------
    vars : dict
      Return a dictionary of all the relevant PyMC objects for the
      rate model.  vars['rate_stoch'] is of particular
      relevance; this is what is used to link the rate model
      into more complicated models, like the generic disease model.
    """
    vars = {}
    est_mesh = dm.get_estimate_age_mesh()
    param_mesh = dm.get_param_age_mesh()

    if np.any(np.diff(est_mesh) != 1):
        raise ValueError, 'ERROR: Gaps in estimation age mesh must all equal 1'

    dm.calc_effective_sample_size(data_list)

    # for debugging
    #if key == 'incidence+asia_southeast+1990+female':

    # generate regional covariates
    covariate_dict = dm.get_covariates()
    X_region, X_study = regional_covariates(key, covariate_dict)

    # use confidence prior from prior_str
    mu_delta = 100.
    sigma_delta = 1.
    from dismod3.settings import PRIOR_SEP_STR
    for line in dm.get_priors(key).split(PRIOR_SEP_STR):
        prior = line.strip().split()
        if len(prior) == 0:
            continue
        if prior[0] == 'heterogeneity':
            mu_delta = float(prior[1])
            sigma_delta = float(prior[2])

    # use the empirical prior mean if it is available
    if len(set(emp_prior.keys()) & set(['alpha', 'beta', 'gamma'])) == 3:
        mu_alpha = np.array(emp_prior['alpha'])
        sigma_alpha = max([.1] + emp_prior['sigma_alpha'])
        alpha = np.array(emp_prior['alpha'])
        vars.update(region_coeffs=alpha)

        beta = np.array(emp_prior['beta'])
        sigma_beta = max([.1] + emp_prior['sigma_beta'])
        vars.update(study_coeffs=beta)

        mu_gamma = np.array(emp_prior['gamma'])
        sigma_gamma = max([.1] + emp_prior['sigma_gamma'])

        mu_delta = emp_prior['delta']
        sigma_delta = emp_prior['sigma_delta']

    else:
        mu_alpha = np.zeros(len(X_region))
        sigma_alpha = .5
        alpha = mc.Normal('region_coeffs_%s' % key, mu=mu_alpha, tau=sigma_alpha**-2., value=mu_alpha)
        vars.update(region_coeffs=alpha)

        mu_beta = np.zeros(len(X_study))
        sigma_beta = .05
        beta = mc.Normal('study_coeffs_%s' % key, mu=mu_beta, tau=sigma_beta**-2., value=mu_beta)
        vars.update(study_coeffs=beta)

        mu_gamma = -5.*np.ones(len(est_mesh))
        sigma_gamma = 5.

    if mu_delta != 0.:
        log_delta = mc.Uninformative('log_dispersion_%s' % key, value=np.log(mu_delta-1))
        delta = mc.Lambda('dispersion_%s' % key, lambda x=log_delta: 1. + np.exp(x))
        @mc.potential(name='potential_dispersion_%s' % key)
        def delta_pot(delta=delta, mu=mu_delta, tau=sigma_delta**-2):
            return mc.normal_like(delta, mu, tau)
        
        vars.update(dispersion=delta, log_dispersion=log_delta, dispersion_potential=delta_pot)


    # create varible for interpolated rate;
    # also create variable for age-specific rate function, if it does not yet exist
    if rate_stoch:
        # if the rate_stoch already exists, for example prevalence in the generic model,
        # we use it to back-calculate mu and eventually gamma
        mu = rate_stoch

        @mc.deterministic(name='age_coeffs_%s' % key)
        def gamma(mu=mu, Xa=X_region, Xb=X_study, alpha=alpha, beta=beta):
            return np.log(mu) - np.dot(alpha, Xa) - np.dot(beta, Xb)

        @mc.potential(name='age_coeffs_potential_%s' % key)
        def gamma_potential(gamma=gamma, mu_gamma=mu_gamma, tau_gamma=1./sigma_gamma**2, param_mesh=param_mesh):
            return mc.normal_like(gamma[param_mesh], mu_gamma[param_mesh], tau_gamma)

        vars.update(rate_stoch=mu, age_coeffs=gamma, age_coeffs_potential=gamma_potential)
        
    else:
        # if the rate_stoch does not yet exists, we make gamma a stoch, and use it to calculate mu
        # for computational efficiency, gamma is a linearly interpolated version of gamma_mesh
        initial_gamma = np.log(np.maximum(dm.get_initial_value(key), NEARLY_ZERO))
        gamma_mesh = mc.Normal('age_coeffs_mesh_%s' % key, mu=mu_gamma[param_mesh], tau=sigma_gamma**-2, value=initial_gamma[param_mesh])
        
        @mc.deterministic(name='age_coeffs_%s' % key)
        def gamma(gamma_mesh=gamma_mesh, param_mesh=param_mesh, est_mesh=est_mesh):
            return interpolate(param_mesh, gamma_mesh, est_mesh)

        @mc.deterministic(name=key)
        def mu(Xa=X_region, Xb=X_study, alpha=alpha, beta=beta, gamma=gamma):
            return predict_rate([Xa, Xb], alpha, beta, gamma)

        vars.update(age_coeffs_mesh=gamma_mesh, age_coeffs=gamma, rate_stoch=mu)


    # create potentials for priors
    vars['priors'] = generate_prior_potentials(dm.get_priors(key), est_mesh, mu)
    

    # create observed stochastics for data
    vars['data'] = []
    vars['observed_rates'] = []
    if mu_delta != 0.:  
        for d in data_list:
            try:
                age_indices, age_weights, Y_i, N_i = values_from(dm, d)
            except ValueError:
                debug('WARNING: could not calculate likelihood for data %d' % d['id'])
                continue

            @mc.observed
            @mc.stochastic(name='data_%d' % d['id'])
            def obs(value=Y_i*N_i, N_i=N_i,
                    X=covariates(d, covariate_dict),
                    alpha=alpha, beta=beta, gamma=gamma, delta=delta,
                    age_indices=age_indices,
                    age_weights=age_weights):

                # calculate study-specific rate function
                mu = predict_rate(X, alpha, beta, gamma)
                mu_i = rate_for_range(mu, age_indices, age_weights)
                logp = mc.negative_binomial_like(value, mu_i*N_i, delta)
                return logp

            vars['data'].append(d)
            vars['observed_rates'].append(obs)
        debug('likelihood of %s contains %d rates' % (key, len(vars['observed_rates'])))
        
    return vars


def values_from(dm, d):
    """ Extract the normalized values from a piece of data

    Parameters
    ----------
    dm : disease model

    d : data dict
    """
    est_mesh = dm.get_estimate_age_mesh()

    # get the index vector and weight vector for the age range
    age_indices = indices_for_range(est_mesh, d['age_start'], d['age_end'])
    age_weights = d.get('age_weights', np.ones(len(age_indices))/len(age_indices))

    # ensure all rate data is valid
    Y_i = dm.value_per_1(d)
    # TODO: allow Y_i > 1, extract effective sample size appropriately in this case
    if Y_i < 0:
        debug('WARNING: data %d < 0' % d['id'])
        raise ValueError

    N_i = max(1000., d['effective_sample_size'])
    return age_indices, age_weights, Y_i, N_i