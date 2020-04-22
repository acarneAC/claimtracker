#!/usr/bin/env python
# Copyright (c) 2020 Andrew Carne <andrew_carne@icloud.com>

import json
from urllib import request
import restapi

def get_data_NWT(tenure_list, out_cols=None):
    url = "https://www.apps.geomatics.gov.nt.ca/arcgis/rest/services/"
    service_url = "https://www.apps.geomatics.gov.nt.ca/arcgis/rest/services/GNWT/Economy_LCC/MapServer"
    layer = "Active Mineral Claims"
    tenure_filter_col="CLAIM_NUM"
    return get_data(url, service_url, layer, tenure_list, tenure_filter_col, out_cols)

def get_data_YK(tenure_list, out_cols=None):
    url= "https://mapservices.gov.yk.ca/arcgis/rest/services/"
    service_url="https://mapservices.gov.yk.ca/arcgis/rest/services/GeoYukon/GY_Mining/MapServer"
    layer="Quartz Claims - 50k"
    tenure_filter_col="GRANT_NUMBER"
    return get_data(url, service_url, layer, tenure_list, tenure_filter_col, out_cols)

def get_data_NV(tenure_list, out_cols=None):
    url = 'https://services.arcgis.com/CXYUMoYknZtf5Qr3/ArcGIS/rest/services/'
    service_url="https://services.arcgis.com/CXYUMoYknZtf5Qr3/ArcGIS/rest/services/ArcOnlineNvStateClaims/FeatureServer"
    layer='Claim Point Listings'
    tenure_filter_col="SERIALNUMB"
    return get_data(url, service_url, layer, tenure_list, tenure_filter_col, out_cols)

def get_data(base_url, service_url, layer, tenure_list, tenure_filter_col, out_cols=None, batch_size = 25):


    ags = restapi.ArcServer(base_url)
    if not out_cols:
        out_cols = "*"

    query = tenure_filter_col + " IN (" + ','.join(["'" + t + "'" for t in tenure_list[:batch_size]]) + ")"

    extension = service_url.split('/')[-1]
    if extension == 'MapServer':
        svc = restapi.MapService(service_url, token=ags.token)
    elif extension == 'FeatureServer':
        svc = restapi.FeatureService(service_url, token=ags.token)
    elif extension == 'GPServer':
        svc = restapi.GPService(service_url, token=ags.token)
    elif extension == 'ImageServer':
        svc = restapi.ImageService(service_url, token=ags.token)
    elif extension == 'GeocodeServer':
        svc = restapi.Geocoder(service_url, token=ags.token)
    else:
        raise NotImplementedError('restapi does not support "{}" services!')

    lyr = svc.layer(layer)
    result = lyr.query(query, out_cols)

    out_data = [r["properties"] for r in result]

    return out_data
