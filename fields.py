from django.db import models
from django.utils.translation import ugettext as _

SEX_CHOICES = [
    ('male', _('Male')),
    ('female', _('Female')),
    ('total', _('Total')),
]

class SexField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 10)
        kwargs.setdefault('choices', SEX_CHOICES)

        super(SexField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"

# -1 as year means apply to all years
ALL_YEARS = -1

standardize_sex = {
    'male': 'male',
    'Male': 'male',
    'Male ': 'male',
    'm': 'male',
    'M': 'male',

    'female': 'female',
    'Female': 'female',
    'Female ': 'female',
    'f': 'female',
    'F': 'female',

    'total': 'total',
    'Total': 'total',
    'Total ': 'total',

    'all': 'all',
    'All': 'all',
    }
    

DATA_TYPE_CHOICES = [
    ('incidence data', _('Incidence Rate')),
    ('prevalence data', _('Prevalence Rate')),
    ('remission data', _('Remission Rate')),
    ('excess-mortality data', _('Excess Mortality Rate')),
    ('mrr data', _('Mortality Rate Ratio')),
    ('smr data', _('Standardized Mortality Ratio')),
    ('mortality data', _('With-condition Mortality Rate')),
    ('duration data', _('Case Duration')),
    ('all-cause mortality data', _('All-cause Mortality Rate')),
]

class DataTypeField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 100)
        kwargs.setdefault('choices', DATA_TYPE_CHOICES)

        super(DataTypeField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"

