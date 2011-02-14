from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import *
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django import forms
from django.db import transaction
from datetime import datetime
import simplejson as json
import pylab as pl
import csv
import StringIO
from gbd.covariate_data_server.models import *
from gbd import view_utils
from gbd.dismod3.settings import CSV_PATH
from gbd.dismod3.settings import gbd_regions
from gbd.dismod3.utils import clean

@login_required
def covariate_type_list_show(request):
    """ Show the list of all uploaded covariate types """
    ct = CovariateType.objects.all()
    for c in ct:
        if c.region_only:
            c.region_only = 'yes'
        else:
            c.region_only = 'no'

    return render_to_response('covariate_type_list_show.html', {'ct': ct})

def covariate_notes_show(request, id):
    """ Show description for the selected covariate type

    Parameters:
    -----------
      id : int
        the id of the covariate type to display
    """
    ct = get_object_or_404(CovariateType, id=id)
    return render_to_response('covariate_notes_show.html', {'ct': ct})

def covariate_data_count_show(request, id):
    """ Show amount of data for each country of the selected covariate type

    Parameters:
    -----------
      id : int
        the id of the covariate type to display
    """
    ct = get_object_or_404(CovariateType, id=id)
    cov_list = Covariate.objects.filter(type=ct)
    
    if ct.region_only:
        region_dict = {}
        for cov in cov_list:
            region = cov.region
            if region_dict.has_key(region):
                region_dict[region] = region_dict[region] + 1
            else:
                region_dict[region] = 1
        pm = []
        for region in region_dict:
            c = {'region':region, 'count':region_dict[region]}
            c['clean_region'] = clean(c['region'])
            if c['count'] < (ct.year_end - ct.year_start + 1) * 3:
                c['color'] = 'class=highlight'
            else:
                c['color'] = ''
            pm.append(c)

        #pm = ct.covariate_set.all().distinct().values('region')

        #for c in pm:
            #c['clean_region'] = clean(c['region'])
            #c['count'] = ct.covariate_set.filter(region=c['region']).count()
            #if c['count'] < (ct.year_end - ct.year_start + 1) * 3:
                #c['color'] = 'class=highlight'
            #else:
                #c['color'] = ''
        
        if len(pm) != 21:
            error = 'Total number of regions are wrong.  Found ' + str(len(pm)) + '.  Should be 21.'
        else:
            error = ''

        return render_to_response('covariate_data_count_show.html',
                                  {'ct': ct, 'level': 'region', 'error': error,
                                   'paginated_models': view_utils.paginated_models(request, pm)})
    else:
        iso3_dict = {}
        for cov in cov_list:
            iso3 = cov.iso3
            if iso3_dict.has_key(iso3):
                iso3_dict[iso3] = iso3_dict[iso3] + 1
            else:
                iso3_dict[iso3] = 1
        pm = []
        for iso3 in iso3_dict:
            c = {'iso3':iso3, 'count':iso3_dict[iso3]}
            if c['count'] < (ct.year_end - ct.year_start + 1) * 3:
                c['color'] = 'class=highlight'
            else:
                c['color'] = ''
            pm.append(c)

        #pm = ct.covariate_set.all().distinct().values('iso3')

        #for c in pm:
            #c['count'] = ct.covariate_set.filter(iso3=c['iso3']).count()
            #if c['count'] < (ct.year_end - ct.year_start + 1) * 3:
                #c['color'] = 'class=highlight'
            #else:
                #c['color'] = ''

        return render_to_response('covariate_data_count_show.html',
                                  {'ct': ct, 'level': 'country',
                                   'paginated_models': view_utils.paginated_models(request, pm)})

def covariate_type_show(request, id):
    """ Show an index page for the selected covariate type

    Parameters:
    -----------
      id : int
        the id of the covariate type to display
    """
    ct = get_object_or_404(CovariateType, id=id)
    cov_list = Covariate.objects.filter(type=ct)

    if ct.region_only:
        region_dict = {}
        for cov in cov_list:
            key = cov.region + '+' + cov.sex
            if region_dict.has_key(key):
                region_dict[key] = region_dict[key] + 1
            else:
                region_dict[key] = 1
        pm = []
        for key in region_dict:
            region, sex = key.split('+')
            c = {'region':region, 'sex':sex, 'count':region_dict[key]}
            c['clean_region'] = clean(c['region'])
            if c['count'] < (ct.year_end - ct.year_start + 1) * 3:
                c['color'] = 'class=highlight'
            else:
                c['color'] = ''
            pm.append(c)

        #pm = ct.covariate_set.all().distinct().values('region', 'sex')

        #for c in pm:
            #c['clean_region'] = clean(c['region'])
            #c['count'] = ct.covariate_set.filter(region=c['region'], sex=c['sex']).count()
            #if c['count'] < ct.year_end - ct.year_start + 1:
                #c['color'] = 'class=highlight'
            #else:
                #c['color'] = ''

        return render_to_response('covariate_type_show.html',
                                  {'ct': ct, 'level': 'region',
                                   'paginated_models': view_utils.paginated_models(request, pm)})
    else:
        iso3_dict = {}
        for cov in cov_list:
            key = cov.iso3 + '+' + cov.sex
            if iso3_dict.has_key(key):
                iso3_dict[key] = iso3_dict[key] + 1
            else:
                iso3_dict[key] = 1
        pm = []
        for key in iso3_dict:
            c = {'iso3':key[:3], 'sex':key[3:], 'count':iso3_dict[key]}
            if c['count'] < (ct.year_end - ct.year_start + 1) * 3:
                c['color'] = 'class=highlight'
            else:
                c['color'] = ''
            pm.append(c)

        #pm = ct.covariate_set.all().distinct().values('iso3', 'sex')

        #for c in pm:
            #c['count'] = ct.covariate_set.filter(iso3=c['iso3'], sex=c['sex']).count()
            #if c['count'] < ct.year_end - ct.year_start + 1:
                #c['color'] = 'class=highlight'
            #else:
                #c['color'] = ''

        return render_to_response('covariate_type_show.html',
                                  {'ct': ct, 'level': 'country',
                                   'paginated_models': view_utils.paginated_models(request, pm)})

def covariate_data_value_show(request, type, area, format='png'):
    """ Serve a representation of the covariate for the specified type and country

    Parameters:
    -----------
      type : str
        the covariate_type
      area : str
        either the country code or the gbd region
      format : str, optional
        the format to return the results in, may be one of the following:
        json, csv, png, pdf
    """
    ct = get_object_or_404(CovariateType, slug=type)
    fig_width = 18.
    fig_height = 4.5
    sexes = ['male', 'female', 'total']
    pl.figure(figsize=(fig_width, fig_height), dpi=100)
    if len(area) == 3:
        for i, s in enumerate(sexes):
            pl.subplot(1, 3, i + 1)
            X = pl.array(
                sorted([[c.year, c.value] for c in ct.covariate_set.filter(iso3=area, sex=s)]))
            if len(X) > 0:
                pl.plot(X[:,0], X[:,1], '.-')
                pl.ylabel(c.type)
                pl.xlabel('Time (Years)')
                pl.title('%s for %s in %s' % (c.type, s, c.iso3))
    else:
        region_dict = {}
        for r in gbd_regions:
            region_dict[clean(r)] = r

        for i, s in enumerate(sexes):
            pl.subplot(1, 3, i + 1)
            X = pl.array(
                sorted([[c.year, c.value] for c in ct.covariate_set.filter(region=region_dict[area], sex=s)]))
            if len(X) > 0:
                pl.plot(X[:,0], X[:,1], '.-')
                pl.ylabel(c.type)
                pl.xlabel('Time (Years)')
                pl.title('%s for %s in %s' % (c.type, s, c.region))

    response = view_utils.figure_data(format)
    
    return HttpResponse(response, view_utils.MIMETYPE[format])


def covariate_show(request, type, area, sex, format='png'):
    """ Serve a representation of the selected covariate

    Parameters:
    -----------
      type : str
        the covariate_type
      area : str
        either the country code or the gbd region
      sex : str
        the sex to display ('male', 'female', 'all', or '')
      format : str, optional
        the format to return the results in, may be one of the following:
        json, csv, png, pdf
    """
    ct = get_object_or_404(CovariateType, slug=type)
    fig_width = 6.
    fig_height = 4.5
    pl.figure(figsize=(fig_width, fig_height), dpi=100)

    if len(area) == 3:
        X = pl.array(sorted([[c.year, c.value] for c in ct.covariate_set.filter(iso3=area, sex=sex)]))
        if len(X) > 0:
            pl.plot(X[:,0], X[:,1], '.-')
            pl.ylabel(c.type)
            pl.xlabel('Time (Years)')
            pl.title('%s in %s' % (c.type, c.iso3))
    else:
        region_dict = {}
        for r in gbd_regions:
            region_dict[clean(r)] = r
        X = pl.array(sorted([[c.year, c.value] for c in ct.covariate_set.filter(region=region_dict[area], sex=sex)]))
        if len(X) > 0:
            pl.plot(X[:,0], X[:,1], '.-')
            pl.ylabel(c.type)
            pl.xlabel('Time (Years)')
            pl.title('%s in %s' % (c.type, c.region))

    response = view_utils.figure_data(format)
    
    return HttpResponse(response, view_utils.MIMETYPE[format])


class NewDataForm(forms.Form):
    type = forms.CharField(max_length=50)
    file  = forms.FileField()
    source = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':1, 'cols':90, 'wrap': 'off'}))
    yearStart = forms.IntegerField(required=False)
    yearEnd = forms.IntegerField(required=False)
    regionOnly = forms.BooleanField(initial=False, required=False, help_text='Does the covariate data file have region column and no iso3 column?')
        
    def clean_file(self):
        import csv
        data = [d for d in csv.DictReader(self.file)]
        return data
    
    def clean(self):
        data = self.cleaned_data.get('file')
        type_slug = self.cleaned_data.get('type')
        source = self.cleaned_data.get('source')
        year_start = self.cleaned_data.get('yearStart')
        year_end = self.cleaned_data.get('yearEnd')
        region_only = self.cleaned_data.get('regionOnly')

        if data and type_slug:
            if year_start != None:
                try:
                    year = int(year_start)
                except ValueError:
                    raise forms.ValidationError('Could not interpret YearStart')
        
            if year_end != None:     
                try:
                    year = int(year_end)
                except ValueError:
                    raise forms.ValidationError('Could not interpret YearEnd')
            try:
                cov_type = CovariateType.objects.get(slug=type_slug)
            except CovariateType.DoesNotExist:
                if source == '':
                    raise forms.ValidationError('Source is missing')
                if year_start == None:
                    raise forms.ValidationError('YearStart is missing')
                if year_end == None:
                    raise forms.ValidationError('YearEnd is missing')

            if data == None:
                raise forms.ValidationError('Data is missing')       

            # make an iso3 list
            iso3_data = [x[1:] for x in csv.reader(open(CSV_PATH + 'country_region.csv'))]
            iso3_list = []
            for r in iso3_data:
                iso3_list += r

            # make a region list
            region_list = [x[0] for x in csv.reader(open(CSV_PATH + 'country_region.csv'))]

            # make a region_country_dict
            region_country_dict = {}
            for x in csv.reader(open(CSV_PATH + 'country_region.csv')):
                region_country_dict[x[0]] = x[1:]
        
            for ii, d in enumerate(data):
                try:
                    d['value'] = float(d[type_slug])
                except KeyError:
                    raise forms.ValidationError('Could not find column %s (is it spelled correctly?)' % type_slug)
                except ValueError:
                    raise forms.ValidationError('Could not interpret value for %s in line %d' % (type_slug, ii+2))

                if d.has_key('year'):
                    try:
                        d['year'] = int(d['year'])
                    except ValueError:
                        raise forms.ValidationError('Could not interpret year in line %d' % (ii+2))
                else:
                    d['year'] = gbd.fields.ALL_YEARS
                        
                d['sex'] = d.get('sex', '')
                if not d['sex'] in ['male', 'female', 'total', '']:
                    raise forms.ValidationError('Could not interpret sex in line %d' % (ii+2))

                if region_only and not d.has_key('region'):
                    raise forms.ValidationError('Could not find column region (is it spelled correctly?)')

                if not d.has_key('iso3') and not d.has_key('region'):
                    raise forms.ValidationError('Could not find either column iso3 or column region (is it spelled correctly?)')

                if d.has_key('iso3') and not d['iso3'] in iso3_list:
                    raise forms.ValidationError('Could not interpret iso3 in line %d' % (ii+2))

                if d.has_key('region') and not d['region'] in region_list:
                    raise forms.ValidationError('Could not interpret region in line %d' % (ii+2))

                if d.has_key('iso3') and d.has_key('region') and d['iso3'] not in region_country_dict[d['region']]:
                    raise forms.ValidationError('The iso3 and the region are inconsistent in line %d' % (ii+2))
                    
                if d.has_key('age'):
                    try:
                        int(d['age'])
                    except ValueError:
                        raise forms.ValidationError('Could not interpret age in line %d' % (ii+2))

         # Always return the full collection of cleaned data.
        return self.cleaned_data
    
@login_required
def covariate_upload(request):
    if request.method == 'GET':  # no form data is associated with page, yet
        form = NewDataForm()
    elif request.method == 'POST':  # If the form has been submitted...
        form = NewDataForm(request.POST, request.FILES)  # A form bound to the POST data
        form.file = request.FILES.get('file')

        if form.is_valid():
            # All validation rules pass, so create new data based on the
            # form contents
            type_slug = form.cleaned_data['type']
            cov_data = form.cleaned_data['file']
            cov_type, is_new = CovariateType.objects.get_or_create(slug=type_slug, defaults={'year_start': 0, 'year_end': 0, 'mean': 0., 'variance': 0.})

            if is_new and request.POST.get('notes') == '':
                 return render_to_response('covariate_upload.html', {'form': form, 'error': 'Notes are missing.'})

            cov_type.uploader = str(request.user)

            if form.cleaned_data['source'] != '':
                cov_type.source = form.cleaned_data['source']                
                
            cov_type.last_modified_time = datetime.now()
                
            if request.POST.get('notes') != '':
                cov_type.description = request.POST.get('notes')

            if form.cleaned_data['yearStart'] != None:
                cov_type.year_start = form.cleaned_data['yearStart']
        
            if form.cleaned_data['yearEnd'] != None:
                cov_type.year_end = form.cleaned_data['yearEnd']

            cov_type.region_only = form.cleaned_data['regionOnly']

            vals = [d['value'] for d in cov_data]

            cov_type.mean = pl.mean(vals)

            scale = pl.std(vals)
            cov_type.variance = scale * scale
        
            cov_type.save()

            save_covariates(cov_type, cov_data)

            return HttpResponseRedirect(reverse('gbd.covariate_data_server.views.covariate_type_list_show')) # Redirect after POST

    return render_to_response('covariate_upload.html', {'form': form, 'error': ''})

@transaction.commit_on_success
def save_covariates(cov_type, cov_data):
    """ Save covariate data in database

    Parameters:
    -----------
      cov_type : CovariateType object
      cov_data : List of covariate data dicts
    """
    # clean up
    Covariate.objects.filter(type=cov_type).delete()

    # insert covariate data
    for d in cov_data:
        # if sex == '' add a covariate for male, female, and total
        if d['sex'] == '':
            sex_list = ['male', 'female', 'total']
        else:
            sex_list = [d['sex']]
        for sex in sex_list:
            # add a data point, save it on the data list
            if d.has_key('iso3'):
                cov = Covariate(type=cov_type, iso3=d['iso3'], year=d['year'], sex=sex, value=d['value'])
                if d.has_key('region'):
                    cov.region = d['region']
            else:
                cov = Covariate(type=cov_type, region=d['region'], year=d['year'], sex=sex, value=d['value'])
                
            if d.has_key('age'):
                cov.age = d['age']
                  
            cov.save()

@login_required
def get_covariate_types(request):
    """ Get all available covariate types in json

    response:
    ---------
      covariate types : json dict
        including key cov : a json list in a string, may be blank
                        a list of dicts, each for a covariate type, of keys: slug, uploader,          
                        upload_time, source, mean, variance, last_modified_time, year_start,
                        year_end, description, region_only, completeness, or blank
                      error : error in a string, may be blank  
    """
    # prepare response
    response = dict(cov='', error='')

    # get all covariateType objects from database
    cov_types = CovariateType.objects.all()

    # calculate number of countries and number of regions
    iso3_data = [x[1:] for x in csv.reader(open(CSV_PATH + 'country_region.csv'))]
    nCountry = 0
    nRegion = 0
    for r in iso3_data:
        nCountry += len(r)
        nRegion += 1;

    nSex = 3

    # make a list of covaraite type dicts
    cov_list = []
    for cov_type in cov_types:
        # calculate completeness
        iso3_data = [x[1:] for x in csv.reader(open(CSV_PATH + 'country_region.csv'))]
        iso3_list = []
        for r in iso3_data:
            iso3_list += r

        nData = Covariate.objects.filter(type=cov_type).count()
        nYear = cov_type.year_end - cov_type.year_start + 1

        if cov_type.region_only == 'True':
            completeness = float(nData) / nYear / nSex / nRegion
        else:
            completeness = float(nData) / nYear / nSex / nCountry

        # make a covariate type list
        cov = {"slug" : cov_type.slug,
               "uploader" : cov_type.uploader,
               "upload time" : str(cov_type.upload_time)[0:19],
               "source" : cov_type.source,
               "revision time" : str(cov_type.last_modified_time)[0:19],
               "year range" : str(cov_type.year_start) + '-' + str(cov_type.year_end),
               "notes" : cov_type.description,
               "region only" : str(cov_type.region_only),
               "completeness" : str(completeness)[0:8],
               "mean" : cov_type.mean,
               "variance" : cov_type.variance}
        cov_list.append(cov)

    if len(cov_list) == 0:
        response['cov'] = ''
        response['error'] = 'Error: covariate type is missing'
    else:
        response['cov'] = cov_list
        response['error'] = ''

    # make a json of the list and return
    return HttpResponse(json.dumps(response))

@login_required
def get_covariate_data(request):
    """ Get covariate columns for data in csv

    request.POST:
    -------------
      data_csv : csv
        data columns Year_Start, Year_End and Sex are required and if a CovariateType that is 
        region_only is included in cov_req Region is required otherwise Country ISO3 Code is required
      cov_req : json
        a list of dicts, each for a covariate type, of two keys: slug and transform that is a list of
        transform strings: original, log, logit, squared, cubed, normalized, lag-<years> where <year> 
        being the number of lag years  
        example [{"slug": "GDP", "transform": ["original", "lag-5", "log"]}, {"slug": "ABC", "transform": ["squared"]}]

    response:
    ---------
      covariate data : json dict
        including key csv : csv in a string, may be blank
                      error : error in a string, may be blank
        if transform is original the column header is the slug, otherwise is <transform>_<slug>
        example logit_GDP if transform is logit and slug is GDP
    """
    # prepare response
    response = dict(csv='', error='')

    # check input
    data_csv = request.POST.get('data_csv', '')
    if not data_csv:
        response['error'] = 'Error: data_csv is missing'
        HttpResponse(json.dumps(response))

    cov_req_json = request.POST.get('cov_req_json', '')
    if not cov_req_json:
        response['error'] = 'Error: cov_json is missing'
        HttpResponse(json.dumps(response))

    # make a data list from data csv
    csv_f = csv.DictReader(StringIO.StringIO(data_csv))
    data_list = [d for d in csv_f]
    if len(data_list) == 0:
        response['error'] = 'Error: dataset is empty'
        HttpResponse(json.dumps(response))

    # make an input key list
    key_list_in = data_list[0].keys()

    # make a covariate request list from cov_json
    cov_req_list = json.loads(cov_req_json)

    # add covariates to data list
    for cov_req in cov_req_list:
        slug = cov_req['slug']
        cov_type = CovariateType.objects.filter(slug = slug)[0]

        transform_list = []
        for transform in cov_req['transform']:
            try:
                if transform[:4] == 'lag-':
                    data_list = cov_type.calculate_covariates_lag(data_list, int(transform[4:]))
                else:
                    transform_list.append(transform)
            except Exception, e:
                if response['error'] == '':
                    response['error'] = 'Error: ' + str(e)
                else:
                    response['error'] = response['error'] + '\nError: ' + str(e)
                return HttpResponse(json.dumps(response))

        try:
            data_list = cov_type.calculate_covariates(data_list, transform_list)
        except Exception, e:
            if response['error'] == '':
                response['error'] = 'Error: ' + str(e)
            else:
                response['error'] = response['error'] + '\nError: ' + str(e)
            return HttpResponse(json.dumps(response))

    # make an output key list
    key_list_out = list(set(data_list[0].keys()) - set(key_list_in))

    # make a csv string
    strIO = StringIO.StringIO()
    writer = csv.writer(strIO)
    writer.writerow(key_list_out)

    for data in data_list:
        row = []
        for key in key_list_out:
            row.append(data[key])
        writer.writerow(row)

    strIO.seek(0)
    data_csv = strIO.read()
    
    # return the response in json
    response['csv'] = data_csv
    return HttpResponse(json.dumps(response))

