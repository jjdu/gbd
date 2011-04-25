from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse

from models import *
from dismod3.utils import clean
import simplejson as json
import math
import csv
import StringIO

class CovariateDataServerTestCase(TestCase):
    fixtures = ['covariate_data_server/fixtures']

    def create_users(self):
        """ Create users for functional testing of access control.

        It seems easier to create the users with a code block than as
        json fixtures, because the password is clearer before it is
        encrypted.
        """
        from django.contrib.auth.models import User
        user = User.objects.create_user('red', '', 'red')
        user = User.objects.create_user('green', '', 'green')
        user = User.objects.create_user('blue', '', 'blue')

    def assertPng(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content[1:4], 'PNG')

    def assertSuccess(self, response):
        return self.assertEquals(response.status_code, 200)

    def setUp(self):
        self.ctype = CovariateType.objects.all()[0]
        self.cov = Covariate.objects.all()[0]
        self.ctype1 = CovariateType.objects.all()[1]
        self.create_users()
        
        # make a data_list from a data file
        csv_f = csv.DictReader(open('tests/cov_test_data.tsv'), dialect='excel-tab')
        self.data_list = [d for d in csv_f]

    # unit tests
    def test_str(self):
        """ Test all model string functions"""
        s = str(self.cov)
        self.assertTrue(isinstance(s,str))

        s = self.cov.get_absolute_url()
        self.assertTrue(isinstance(s,str))

    # functional tests
    def test_type_list_show(self):
        c = Client()

        url = reverse('gbd.covariate_data_server.views.covariate_type_list_show')
        response = c.get(url)
        self.assertRedirects(response, '/accounts/login/?next=%s'%url)
        # then login and do functional tests
        c.login(username='red', password='red')

        response = c.get(url)
        self.assertTemplateUsed(response, 'covariate_type_list_show.html')

    def test_notes_show(self):
        c = Client()

        url = reverse('gbd.covariate_data_server.views.covariate_notes_show', args=[1])
        response = c.get(url)
        self.assertTemplateUsed(response, 'covariate_notes_show.html')

    def test_data_count_show(self):
        c = Client()

        url = reverse('gbd.covariate_data_server.views.covariate_data_count_show', args=[1])
        response = c.get(url)
        self.assertTemplateUsed(response, 'covariate_data_count_show.html')

    def test_type_show(self):
        c = Client()

        url = reverse('gbd.covariate_data_server.views.covariate_type_show', args=[1])
        response = c.get(url)
        self.assertTemplateUsed(response, 'covariate_type_show.html')

    def test_data_value_show(self):
        c = Client()

        url = self.cov.get_absolute_url()
        response = c.get(url)
        self.assertPng(response)

        url = self.ctype.get_absolute_url()
        response = c.get(url)

    def test_show(self):
        c = Client()

        url = self.cov.get_absolute_url()
        response = c.get(url)
        self.assertPng(response)

        url = self.ctype.get_absolute_url()
        response = c.get(url)
        
    def test_upload(self):
        c = Client()

        url = reverse('gbd.covariate_data_server.views.covariate_upload')
        response = c.get(url)
        self.assertRedirects(response, '/accounts/login/?next=%s'%url)
        # then login and do functional tests
        c.login(username='red', password='red')

        response = c.get(url)
        self.assertTemplateUsed(response, 'covariate_upload.html')

        response = c.post(url, {})
        self.assertTemplateUsed(response, 'covariate_upload.html')

        # now do it right, and make sure that data and datasets are added
        from StringIO import StringIO
        f = StringIO(',iso3,year,LDI_id,LDI_usd\n1,ABW,1950,1533.743774,1105.747437\n1,ABW,1951,1533.843774,1105.87437\n')
        f.name = 'LDI.csv'
        response = c.post(url, {'file':f, 'type': 'LDI_id', 'source': 'web', 'notes': 'description', 'uploader': 'red', 'yearStart': 1950, 'yearEnd': 2010})
        self.assertRedirects(response, reverse('gbd.covariate_data_server.views.covariate_type_list_show'))
        self.assertEqual(CovariateType.objects.filter(slug='LDI_id').count(), 1)
        self.assertEqual(Covariate.objects.filter(type__slug='LDI_id', sex='male').count(), 2)
        self.assertEqual(Covariate.objects.filter(type__slug='LDI_id', sex='female').count(), 2)
        self.assertEqual(Covariate.objects.filter(type__slug='LDI_id', sex='total').count(), 2)

    def test_transform_str_original(self): 
        """ test transform_str == original
        """
        # call calculate_covariates() to add the covariates to the data_list
        data_list_with_cov = self.ctype.calculate_covariates(self.data_list, ['original'])
    
        # make a known covariate list
        known_cov_list = []
        for i in range(24):
            known_cov_list.append(float(i + 1) / 100)

        # check covariates in data_list_with_cov
        for ii, data in enumerate(data_list_with_cov):
            self.assertEqual(data[self.ctype.slug], known_cov_list[ii])

    def test_transform_str_log(self):
        """ test transform_str == log
        """
        # call calculate_covariates() to add the covariates to the data_list
        data_list_with_cov = self.ctype.calculate_covariates(self.data_list, ['log'])
    
        # make a known covariate list
        known_cov_list = []
        for i in range(24):
            known_cov_list.append(math.log(float(i + 1) / 100))

        # check covariates in data_list_with_cov
        key = 'log_' + self.ctype.slug
        for ii, data in enumerate(data_list_with_cov):
            self.assertEqual(data[key], known_cov_list[ii])

    def test_transform_str_logit(self):
        """ test transform_str == logit
        """
        # call calculate_covariates() to add the covariates to the data_list
        data_list_with_cov = self.ctype.calculate_covariates(self.data_list, ['logit'])
    
        # make a known covariate list
        known_cov_list = []
        for i in range(24):
            d = float(i + 1) / 100
            known_cov_list.append(math.log((d) / (1 - d)))

        # check covariates in data_list_with_cov
        key = 'logit_' + self.ctype.slug
        for ii, data in enumerate(data_list_with_cov):
            self.assertEqual(data[key], known_cov_list[ii])

    def test_transform_str_squared(self):
        """ test transform_str == squared
        """
        # call calculate_covariates() to add the covariates to the data_list
        data_list_with_cov = self.ctype.calculate_covariates(self.data_list, ['squared'])
    
        # make a known covariate list
        known_cov_list = []
        for i in range(24):
            d = float(i + 1) / 100
            known_cov_list.append(d * d)

        # check covariates in data_list_with_cov
        key = 'squared_' + self.ctype.slug
        for ii, data in enumerate(data_list_with_cov):
            self.assertEqual(data[key], known_cov_list[ii])

    def test_transform_str_cubed(self):
        """ test transform_str == cubed
        """
        # call calculate_covariates() to add the covariates to the data_list
        data_list_with_cov = self.ctype.calculate_covariates(self.data_list, ['cubed'])
    
        # make a known covariate list
        known_cov_list = []
        for i in range(24):
            d = float(i + 1) / 100
            known_cov_list.append(d * d * d)

        # check covariates in data_list_with_cov
        key = 'cubed_' + self.ctype.slug
        for ii, data in enumerate(data_list_with_cov):
            self.assertEqual(data[key], known_cov_list[ii])
        
    def test_transform_str_normalized(self):
        """ test transform_str == normalized
        """
        # call calculate_covariates() to add the covariates to the data_list
        data_list_with_cov = self.ctype.calculate_covariates(self.data_list, ['normalized'])
        
        # make a known covariate list
        known_cov_list = []
        for i in range(24):
            known_cov_list.append(float(i + 1) / 100)
     
        shift = self.ctype.mean
        scale = math.sqrt(self.ctype.variance)

        for i in range(len(known_cov_list)):
            known_cov_list[i] = (known_cov_list[i] -shift) / scale

        # check covariates in data_list_with_cov
        key = 'normalized_' + self.ctype.slug
        for ii, data in enumerate(data_list_with_cov):
            self.assertEqual(data[key], known_cov_list[ii])
        
    def test_lag(self):
        """ test lag
        """
        # call calculate_covariates() to add the covariates to the data_list
        data_list_with_cov = self.ctype.calculate_covariates_lag(self.data_list, 5)
        
        # make a known covariate list
        known_cov_list = []
        for i in range(24):
            known_cov_list.append(float(i + 2) / 100)

        # check covariates in data_list_with_cov
        key = 'lag-5_' + self.ctype.slug
        for ii, data in enumerate(data_list_with_cov):
            self.assertEqual(data[key], known_cov_list[ii])

    def test_region_only(self): 
        """ test region only
        """
        # call calculate_covariates() to add the covariates to the data_list
        data_list_with_cov = self.ctype1.calculate_covariates(self.data_list, ['original'])
    
        # make a known covariate list
        known_cov_list = []
        for i in range(6):
            known_cov_list.append(float(i + 1) / 100)
        for i in range(6):
            known_cov_list.append(float(i + 1) / 100)
        for i in range(12):
            known_cov_list.append(float(i + 7) / 100)

        # check covariates in data_list_with_cov
        for ii, data in enumerate(data_list_with_cov):
            self.assertEqual(data[self.ctype1.slug], known_cov_list[ii])

    def test_get_covariate_types(self):
        c = Client()

        url = reverse('gbd.covariate_data_server.views.get_covariate_types')
        response = c.get(url)
        self.assertRedirects(response, '/accounts/login/?next=%s'%url)
        # then login and do functional tests
        c.login(username='red', password='red')

        response = c.get(url)
        #import pdb;pdb.set_trace()
        resp_json = json.loads(response.content)['cov']
        
        self.assertEqual(resp_json[0]['slug'], 'GDP')
        self.assertEqual(resp_json[0]['uploader'], 'red')
        self.assertEqual(resp_json[0]['source'], 'web')
        self.assertEqual(resp_json[0]['notes'], 'notes')
        self.assertEqual(resp_json[0]['year range'], '1950-2010')
        self.assertEqual(resp_json[0]['region only'], 'False')
        self.assertEqual(resp_json[0]['mean'], 0.130)
        self.assertEqual(resp_json[0]['variance'], 0.004817)
        self.assertEqual(resp_json[1]['slug'], 'ABC')
        self.assertEqual(resp_json[1]['uploader'], 'red')
        self.assertEqual(resp_json[1]['source'], 'web')
        self.assertEqual(resp_json[1]['notes'], 'notes')
        self.assertEqual(resp_json[1]['year range'], '1950-2010')
        self.assertEqual(resp_json[1]['region only'], 'True')
        self.assertEqual(resp_json[1]['mean'], 0.095)
        self.assertEqual(resp_json[1]['variance'], 0.002692)

    def test_add_covariate_to_data(self):
        c = Client()

        url = reverse('gbd.covariate_data_server.views.get_covariate_data')
        response = c.get(url)
        self.assertRedirects(response, '/accounts/login/?next=%s'%url)
        # then login and do functional tests
        c.login(username='red', password='red')

        # make an output key list
        key_list = ['region', 'country_iso3_code', 'year_start', 'year_end', 'sex']
   
        # make a csv string
        strIO = StringIO.StringIO()
        writer = csv.writer(strIO)
        writer.writerow(key_list)

        for data in self.data_list:
            row = []
            for key in key_list:
                row.append(data[key])
            writer.writerow(row)

        strIO.seek(0)
        data_csv = strIO.read()

        cov_req_json = '[{"slug": "GDP", "transform": ["original", "lag-5", "log"]}, \
                         {"slug": "ABC", "transform": ["original"]}, \
                         {"slug": "ERR", "transform": ["doubled"]}]'

        # post and receive response
        response = c.post(url, dict(data_csv=data_csv, cov_req_json = cov_req_json))
        resp_json = json.loads(response.content)
        data_csv = resp_json['csv']
        error = resp_json['error']

        # check response
        # make a data list from data csv
        csv_f = csv.DictReader(StringIO.StringIO(data_csv))
        data_list_with_cov = [d for d in csv_f]

        # make a known covariate list for transform = original
        known_cov_list = []
        for i in range(24):
            known_cov_list.append(float(i + 1) / 100)
  
        # check covariates in data_list_with_cov
        for ii, data in enumerate(data_list_with_cov):
            self.assertEqual(float(data['GDP']), known_cov_list[ii])

        # make a known covariate list for transform = lag-5
        known_cov_list = []
        for i in range(24):
            known_cov_list.append(float(i + 2) / 100)

        # check covariates in data_list_with_cov
        key = 'lag-5_' + self.ctype.slug
        for ii, data in enumerate(data_list_with_cov):
            self.assertEqual(float(data[key]), known_cov_list[ii])

        # make a known covariate list for transform = log
        known_cov_list = []
        for i in range(24):
            known_cov_list.append(math.log(float(i + 1) / 100))

        # check covariates in data_list_with_cov
        key = 'log_' + self.ctype.slug
        for ii, data in enumerate(data_list_with_cov):
            self.assertAlmostEqual(float(data[key]), known_cov_list[ii])

        # make a known covariate list for transform = original, region_only
        known_cov_list = []
        for i in range(6):
            known_cov_list.append(float(i + 1) / 100)
        for i in range(6):
            known_cov_list.append(float(i + 1) / 100)
        for i in range(12):
            known_cov_list.append(float(i + 7) / 100)

        # check covariates in data_list_with_cov
        for ii, data in enumerate(data_list_with_cov):
            self.assertAlmostEqual(float(data[self.ctype1.slug]), known_cov_list[ii])

        # check error message
        self.assertEqual(error, 'Error: cannot understand transform_str: doubled')


