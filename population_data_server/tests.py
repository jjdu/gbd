from django.test import TestCase
from django.test.client import Client
import csv
import StringIO
from django.core.urlresolvers import reverse
from models import *

class PopulationDataServerTestCase(TestCase):
    fixtures = ['population_data_server/fixtures']

    def create_users(self):
        """ Create users for functional testing of access control.

        It seems easier to create the users with a code block than as
        json fixtures, because the password is clearer before it is
        encrypted.
        """
        from django.contrib.auth.models import User
        user = User.objects.create_user('red', '', 'red')

    def assertPng(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content[1:4], 'PNG')

    def assertSuccess(self, response):
        return self.assertEquals(response.status_code, 200)

    def setUp(self):
        self.create_users()
        self.pop = Population.objects.all()[0]

    # unit tests
    def test_str(self):
        """ Test all model string functions"""
        s = str(self.pop)
        self.assertTrue(isinstance(s,str))

        s = self.pop.get_absolute_url()
        self.assertTrue(isinstance(s,str))

    def test_interpolate(self):
        """ Test interpolation"""
        f = self.pop.interpolate([0,10,20])
        self.assertEqual(f[0], 1.5)

    def test_calculate_age_weights(self):
        """ Test calculating age weights"""
        # make a data_list
        data_list = [
        {'parameter':'prevalence','country_iso3_code':'AUS','year_start':'2005','year_end':'2005','sex':'male','age_start':'0','age_end':'50'},
        {'parameter':'prevalence','country_iso3_code':'AUS','year_start':'2005','year_end':'2005','sex':'female','age_start':'0','age_end':'50'},
        {'parameter':'prevalence','country_iso3_code':'AUS','year_start':'2005','year_end':'2005','sex':'total','age_start':'0','age_end':'50'},
        {'parameter':'prevalence','country_iso3_code':'USA','year_start':'2005','year_end':'2005','sex':'all','age_start':'0','age_end':'50'}]

        # apply the function and check the result
        result = calculate_age_weights(data_list)
        self.assertEqual(result[0]['age_weights'][0], 1.5/63.75)
        self.assertEqual(result[0]['age_weights'][1], 1.49/63.75)
        self.assertEqual(result[0]['age_weights'][50], 1.0/63.75)
        self.assertEqual(result[1]['age_weights'][0], 1.5/63.75)
        self.assertEqual(result[1]['age_weights'][1], 1.49/63.75)
        self.assertEqual(result[1]['age_weights'][50], 1.0/63.75)
        self.assertEqual(result[2]['age_weights'][0], 3.0/127.5)
        self.assertEqual(result[2]['age_weights'][1], 2.98/127.5)
        self.assertEqual(result[2]['age_weights'][50], 2.0/127.5)
        self.assertEqual(result[3]['age_weights'][0], 3.0/127.5)
        self.assertEqual(result[3]['age_weights'][1], 2.98/127.5)
        self.assertEqual(result[3]['age_weights'][50], 2.0/127.5)

    # functional tests
    def test_population_show(self):
        """ Test plotting population curve"""
        c = Client()

        url = self.pop.get_absolute_url()
        response = c.get(url)
        self.assertPng(response)

    def test_population_show_in_other_formats(self):
        """ Test getting population curve as json, csv, etc"""
        c = Client()

        # test png
        url = self.pop.get_absolute_url()
        response = c.get(url + '.png')
        self.assertPng(response)

        # test json
        response = c.get(url + '.json')
        r_json = json.loads(response.content)
        self.assertEqual(set(r_json.keys()), set(['age', 'population']))

        # test csv
        response = c.get(url + '.csv')
        self.assertEqual(response.content.split('\r\n')[0], 'Age (years),Population (thousands)')

    def test_get_age_weights(self):
        """ Test getting age weights"""
        c = Client()

        url = reverse('gbd.population_data_server.views.get_age_weights')
        response = c.get(url)

        self.assertRedirects(response, '/accounts/login/?next=%s'%url)
        # then login and do functional tests
        c.login(username='red', password='red')

        # make a data_csv
        data_csv = 'parameter,country_iso3_code,year_start,year_end,sex,age_start,age_end\nprevalence,AUS,2005,2005,male,0,50\nprevalence,AUS,2005,2005,female,0,50\nprevalence,AUS,2005,2005,total,0,50\nprevalence,USA,2005,2005,all,0,50'

        # post and receive response
        response = c.post(url, dict(data_csv=data_csv))

        resp_json = json.loads(response.content)
        data_csv = resp_json['csv']
        error = resp_json['error']

        # check response
        # make a data list from data csv
        csv_f = csv.DictReader(StringIO.StringIO(data_csv))
        data_list = [d for d in csv_f]

        self.assertEqual(json.loads(data_list[0]['age_weights'])[0], 1.5/63.75)
        self.assertEqual(json.loads(data_list[0]['age_weights'])[1], 1.49/63.75)
        self.assertEqual(json.loads(data_list[0]['age_weights'])[50], 1.0/63.75)
        self.assertEqual(json.loads(data_list[1]['age_weights'])[0], 1.5/63.75)
        self.assertEqual(json.loads(data_list[1]['age_weights'])[1], 1.49/63.75)
        self.assertEqual(json.loads(data_list[1]['age_weights'])[50], 1.0/63.75)
        self.assertEqual(json.loads(data_list[2]['age_weights'])[0], 3.0/127.5)
        self.assertEqual(json.loads(data_list[2]['age_weights'])[1], 2.98/127.5)
        self.assertEqual(json.loads(data_list[2]['age_weights'])[50], 2.0/127.5)
        self.assertEqual(json.loads(data_list[3]['age_weights'])[0], 3.0/127.5)
        self.assertEqual(json.loads(data_list[3]['age_weights'])[1], 2.98/127.5)
        self.assertEqual(json.loads(data_list[3]['age_weights'])[50], 2.0/127.5)


