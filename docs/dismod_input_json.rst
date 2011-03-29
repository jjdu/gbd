Specification of the DisMod input json format
---------------------------------------------

This document describes the complete input in json for running a DisMod job.

::

    dismod_input = {
      'input_data' : input_data_csv (required), see below,

      'parameters' : param_list (required), see below,

      'output_template' : output_template_csv (required), see below,

      'areas_hierarchy' : [[parent_area, child_area], ...] (required), list of pairs of areas describing the area hierarchy,

      'areas_to_fit' : [area_1, area_2, ...] (required), list of areas in area hierarchy,
    }

    input_data_csv = [input_data_1, input_data_2, ...] in csv (required), see below

    input_data_i = {
      'data_type' : str (required), one of the following types
                    'incidence',
                    'prevalence',
                    'remission',
                    'excess-mortality',
                    'relative-risk',
                    'smr',
                    'with-condition-mortality',
                    'duration',
                    'cause-specific-mortality',
(note for adding additional data types in the future, data_types are lowercase characters and dashes, without any spaces or non-alphabet characters)

      'value' : float (required), parameter value limits
                'incidence' >= 0,
                'prevalence' [0, 1],
                'remission' >= 0,
                'excess-mortality' >=0,
                'relative-risk' >= 0,
                'smr' >= 0,
                'with-condition-mortality' >= 0,
                'duration' >= 0,
                'cause-specific-mortality'  >= 0,

      'area' : str (required), a geographic area defined in the area table,

      'sex' : str (required), one of 'male', 'female', 'total',

      'age_start' : int[0, 150], <= age_end (required),

      'age_end' : int[0, 150], >= age_start (required),

      'year_start' : int[1900, 2050], <= year_end (required),

      'year_end' : int[1900, 2050], >= year_start (required),

      'standard_error' : float > 0 (optional*),

      'effective_sample_size' : int > 0, <= total_study_size_n (optional*),

      'lower_ci' : float >= 0 <= Parameter Value (optional*),
      
      'upper_ci' : float > Parameter Value (optional*),

(* one of se, ess, or ci must be set)

      'age_weights' : [ float, float, ... ] (required*), length equals age_end - age_start + 1,
                      default/missing assume to be [ 1, ... ],
(* this will be merged in by the MDA and is not required of the user)

      'study_id' : int >= 0 (optional),

      'citation' : str (optional),

      'ignore' : int[0, 1] (optional),

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

      'condition' : str (required), one of the GBD causes,

      'notes' : str (required)
    ]
---- continute checking here next time ---
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
      'rate' : int = 0 or = 1 (required),

      'error' : int = 0 or = 1 (required),
      'reference_value' : string (required), a number
    }

    country_level_type_i : {
      'rate' : int = 0 or = 1 (required),

      'error' : int = 0 or = 1 (required),

      'reference_value' : string (required), a number or "Country Specific Value",
    }

    output_template_csv = [output_template_1, output_template_2, ...] in csv (required), see below

    output_template_i = {
      'data_type' : str (required), one of the following types
                    'incidence',
                    'prevalence',
                    'remission',
                    'excess-mortality',
                    'relative-risk',
                    'smr',
                    'with-condition-mortality',
                    'duration',
                    'cause-specific-mortality', 

      'area' : str (required), a geographic area defined in the area table,

      'sex' : str (required), one of 'male', 'female',

      'age_start' : int[0, 150], <= age_end (required),

      'age_end' : int[0, 150], >= age_start (required),

      'year_start' : int[1900, 2050], <= year_end (required),

      'year_end' : int[1900, 2050], >= year_start (required),

      'age_weights' : [ float, float, ... ] (required*), length equals age_end - age_start + 1,
                      default/missing assume to be [ 1, ... ],

?      additional keys, with corresponding values for all selected country-level covariates for this
      data_type, this region, this sex, this year_start and this year_end
    }
