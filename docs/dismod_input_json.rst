Specification of the DisMod input json format
---------------------------------------------

This document describes the complete input in json for running a DisMod job.

::

    dismod_input = {
      'input_data' : input_data_csv (required), see below,

      'parameters' : param_list (required), see below,

      'output_data' : output_data_csv (required), see below,

      'gdb_regions' : [str, str, ...] (required), list of distinct GDB Regions to fit
    }

    input_data_csv = [input_data_1, input_data_2, ...] in csv (required), see below

    input_data_i = {
      'condition' : str (required), one of the GBD causes,

      'data_type' : str (required), one of the following types
                    'incidence data',
                    'prevalence data',
                    'remission data',
                    'excess-mortality data',
                    'relative-risk data',
                    'smr data',
                    'mortality data',
                    'duration data',
                    'cause-specific mortality data',

      'value' : float (required), parameter value limits
                'incidence data' >= 0,
                'prevalence data' [0, 1],
                'remission data' >= 0,
                'excess-mortality data' >=0,
                'relative-risk data' >= 1,
                'smr data' >= 1,
                'mortality data >= 0,
                'duration data' [0, 100],
                'cause-specific mortality data'  >= 0,

      'gbd_region' : str (required), one of the GBD regions,

      'region' : str (required), country iso3 code,

      'sex' : str (required), one of 'male', 'female', 'total',

      'age_start' : int[0, 100], <= age_end (required),

      'age_end' : int[0, 100], >= age_start (required),

      'year_start' : int[1950, 2010], <= year_end (required),

      'year_end' : int[1950, 2010], >= year_start (required),

      'units' : float >= 1 (required),

      'study_id' : int >= 0 (optional),

      'sequela' : str, one of the GBD sequela codes (optional),

      'case_definition' : str (optional),

      'standard_error' : float > 0 (optional),

      'effective_sample_size' : int > 0, <= total_study_size_n (optional),

      'lower_ci' : float >= 0 <= Parameter Value (optional),
      
      'upper_ci' : float > Parameter Value (optional),

      'total_study_size_n : int > 0 (optional),

      'design_factor' : float >= 1 (optional),

      'citation' : str (optional),

      'ignore' : int[0, 1] (optional),

      'age_weights' : [ float, float, ... ] (optional), length equals age_end - age_start + 1,
                      default/missing assume to be [ 1, ... ],

      additional keys, with corresponding values for all study-level covariates, and all country-level   
      covariates merged for this data_type, this region, this sex, this year_start and this year_end
    }

    param_list = [
      'prevalence' : param_dict (required), see below,

      'incidence' : param_dict (required), see below,

      'remission' : param_dict (required), see below,

      'excess-mortality' : param_dict (required), see below,

      'duration' : param_dict (required), see below,

      'relative-risk' : param_dict (required) see below,

      'notes' : str (required)
    ]

    param_dict = {
      'priors' : prior_dict (required), see below,

      'covariates' : covariate_dict (required), see below
    }

    prior_dict = {
      'smoothness' : {
        'amount' : str (required), one of 'Slightly', 'No Prior', 'Moderately', 'Very'],

        'age_start' : int[0, 100], <= 'age_end' (required),

        'age_end' : int[0, 100], >= age_start (required)
      },

      'heterogeneity' : str (required), one of 'Slightly', 'Moderately', 'Very', 'Unusable',

      'level_value' : {
        'value' : float >= level_bounds['lower'], <= level_bounds['upper'] (required),

        'age_before' : int[0, 100], <= age_after (required),

        'age_after' : int[0, 100], >= age_before (required)
      },

      'level_bounds' : {
        'upper' : float >=0 except for prevalence [0, 1] and duration [0, 100] (required),

        'lower' : float >=0, <= 'upper' (required)
      },

      'increasing' : {
        'age_start' : int[0, 100], <= 'age_end' (required),

        'age_end' : int[0, 100] (required)
      },

      'decreasing' : {
        'age_start' : int[0, 100], <= 'age_end' (required),

        'age_end' : int[0, 100], >= age_start (required)
      },

      'unimodal' : {
        'age_start' : int[0, 100], <= 'age_end' (required),

        'age_end' : int[0, 100], >= age_start (required)
      },

      'max_y' : float(0, 1] (required),

      'param_age_mesh' : [float, float, ...], numbers are in range[0, 100] increasing (required)
    }

    covariate_dict = {
      'study_level' : {study_level_type_1, study_level_type_2, ...} (required), see below,

      'country_level' : {country_level_type_1, country_level_type_2, ...} (required), see below
    }

    study_level_type_i : {
      'rate' : {
        'value' : int = 0 or = 1 (required),

        'default' : 1 (required)
      },

      'error' : {
        'value' : int = 0 or = 1 (required),

        'default' : 0 (required)
      },

      'reference_value' : {
        'value' : string (required),

        'default' : "0" (required),
      }
    }

    country_level_type_i : {
      'rate' : {
        'value' : int = 0 or = 1 (required),

        'default' : 1 (required)
      },

      'error' : {
        'value' : int = 0 or = 1 (required),

        'default' : 0 (required)
      },

      'reference_value' : {
        'value' : string (required), a number or "Country Specific Value",

        'default' : "Country Specific Value" (required)
      }
    }

    output_data_csv = [output_data_1, output_data_2, ...] in csv (required), see below

    output_data_i = {
      'data_type' : str (required), one of the following types
                    'incidence data',
                    'prevalence data',
                    'remission data',
                    'excess-mortality data',
                    'relative-risk data',
                    'smr data',
                    'mortality data',
                    'duration data',
                    'cause-specific mortality data',

      'region' : str (required),

      'sex' : str (required), one of 'male', 'female', 'total',

      'age_start' : int[0, 100], <= age_end (required),

      'age_end' : int[0, 100], >= age_start (required),

      'age_weights' : [ float, float, ... ] (optional), length equals age_end - age_start + 1,
                      default/missing assume to be [ 1, ... ],

      'year_start' : int[1950, 2010], <= year_end (required),

      'year_end' : int[1950, 2010], >= year_start (required),

      additional keys, with corresponding values for all selected country-level covariates for this
      data_type, this region, this sex, this year_start and this year_end
    }
