# -*- coding: utf-8 -*-
"""
Created on Tue Oct 11 15:55:59 2022

@author: Ronan

Origine data
https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/

"""

import streamlit as st

import folium
from folium import Choropleth, Circle, Marker
from folium.plugins import Draw
from streamlit_folium import st_folium
from shapely.geometry import Point
from shapely.geometry import Polygon
from bokeh.plotting import figure
import branca.colormap as cm
import datetime as dt
import os

import gzip
import shutil

import pandas as pd
import numpy as np

#import pydeck as pdk



@st.cache
def open_read_csv_gz(years,cd_post):

    frames=[]
    for year in years:

        name_in = str(year) + '.csv.gz'
        
        with gzip.open(name_in, 'rb') as f_in:
            with open('tmp.csv', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        dvi_data = pd.read_csv(
            'tmp.csv',
            usecols=['id_mutation',  'nature_mutation', 'valeur_fonciere', 'adresse_numero',
                       'adresse_suffixe','adresse_nom_voie','code_postal','nom_commune','lot1_surface_carrez',
                       'lot2_surface_carrez','lot3_surface_carrez','lot4_surface_carrez','lot5_surface_carrez','nombre_lots',
                       'longitude','latitude','type_local'],
            dtype={
                'id_mutation': 'str',
                #'date_mutation': dt.datetime,
                'nature_mutation': 'category',
                'valeur_fonciere': 'float64',
                'adresse_numero': 'Int64',
                'adresse_suffixe': 'category',
                'adresse_nom_voie': 'str',
                'code_postal': 'Int64',
                'nom_commune': 'str',
                'lot1_surface_carrez': 'float32',
                'lot2_surface_carrez': 'float32',
                'lot3_surface_carrez': 'float32',
                'lot4_surface_carrez': 'float32',
                'lot5_surface_carrez': 'float32',
                'nombre_lots': 'Int64',
                'longitude': 'float64',
                'latitude': 'float64',
                'type_local': 'str',
                },
            #na_values = 'NA'
            #parse_dates=['date'],
            #infer_datetime_format=True,
            )
        os.remove('tmp.csv')
        
        
        dvi_data['year'] = year
        frames.append(dvi_data[dvi_data['code_postal'].isin(cd_post)])
        
    out_df = pd.concat(frames) 
    
    return out_df




st.set_page_config(layout="wide")
st.title('Welcome')

# data21 = open_read_csv_gz('2021.csv.gz')
# st.success('Data loaded')

# Filtre sur le code postal
cd_post = st.multiselect('Select postal code of interest',[31000,31100,31200,31300,31400,31500])
years = st.multiselect('Select years of interest',[2017,2018,2019,2020,2021])

if st.button('Load data'):
    st.session_state['cd_post'] = cd_post
    st.session_state['years'] = years
    st.session_state['first_act'] = True

if 'first_act' not in st.session_state:
    st.session_state['first_act'] = False
    
if st.session_state['first_act']:

    #data_for_analysis = data21[data21['code_postal'].isin(st.session_state['cd_post'])]
    
    
    load_data = open_read_csv_gz(st.session_state['years'],st.session_state['cd_post'])
    data_for_analysis = load_data.copy(deep = True)
    st.success('Data loaded')
    
    #st.write(data_for_analysis.head())
    #st.write(data_for_analysis.tail())
    
    #for elem in cd_post[1:]:
    #    data_for_analysis = pd.concat(data_for_analysis,data21[data21['code_postal'] == elem])
    
    #data21 = data21[data21['code_postal'] == cd_post]
    
    
    # Clean data
    
    data_for_analysis.dropna(subset=['longitude', 'latitude'],inplace = True)
    
    data_for_analysis['surface'] = data_for_analysis[['lot1_surface_carrez','lot2_surface_carrez','lot3_surface_carrez','lot4_surface_carrez','lot5_surface_carrez']].sum(axis=1)
    data_for_analysis = data_for_analysis[data_for_analysis['surface'] != 0]
    
    data_for_analysis['prix_m2'] = data_for_analysis['valeur_fonciere']/data_for_analysis['surface']
    data_for_analysis = data_for_analysis[data_for_analysis['prix_m2']>1000]
    data_for_analysis = data_for_analysis[data_for_analysis['prix_m2']<20000]
    
    
    col1, col2 = st.columns(2)
    
    with col1:
        ## MAP

        m = folium.Map(location=[43.599, 1.4389], zoom_start=13)
        
        min_price = data_for_analysis['prix_m2'].min()
        max_price = data_for_analysis['prix_m2'].max()
        med_price = data_for_analysis['prix_m2'].quantile(0.5)
        q25_price = data_for_analysis['prix_m2'].quantile(0.25)
        q75_price = data_for_analysis['prix_m2'].quantile(0.75)
        
        colormap = cm.StepColormap(colors=['green','yellow','orange','red'] ,
                                   index=[min_price,q25_price,med_price,q75_price,max_price], 
                                   vmin= min_price,
                                   vmax=max_price)
        
        for i in range(0,len(data_for_analysis)):
            Circle(
                location=[data_for_analysis.iloc[i]['latitude'], data_for_analysis.iloc[i]['longitude']],
                radius=20,
                color=colormap(data_for_analysis.iloc[i]['prix_m2'])
                ).add_to(m)
        
    
        Draw(export=True).add_to(m)
        
        output = st_folium(m, width = 700, height=500)
    
    with col2:
        st.write('Draw a polygon (only) to get properties in the selected area')
        lat = []
        lon = []
        if output['all_drawings']:
            for elem in output['all_drawings'][0]['geometry']['coordinates'][0]:
                lon.append(elem[0])
                lat.append(elem[1])
        
        
            lat_vec = np.array(lat)
            lon_vec = np.array(lon)
            lon_lat_vec = np.column_stack((lon_vec,lat_vec))
            polygon_search = Polygon(lon_lat_vec)
            
            def get_sell_in_poly(df,polygon_search):
                df['point_vect']=''
                for idx_line, line in df.iterrows():
            
                    if (not np.isnan(line['longitude'])) & (not np.isnan(line['latitude'])):
                        df['point_vect'][idx_line] = Point(line['longitude'],line['latitude'])
                        df['point_vect'][idx_line] = polygon_search.contains(df['point_vect'][idx_line])
                return df[df['point_vect']==True]
            
            Selected_transaction = get_sell_in_poly(data_for_analysis,polygon_search)
            
            sel_min_price = Selected_transaction['prix_m2'].min()
            sel_max_price = Selected_transaction['prix_m2'].max()
            sel_med_price = Selected_transaction['prix_m2'].quantile(0.5)
            sel_q25_price = Selected_transaction['prix_m2'].quantile(0.25)
            sel_q75_price = Selected_transaction['prix_m2'].quantile(0.75)
            
            #st.write(Selected_transaction.head())
    
            
            st.write('The mean price in the selected area is ' + str(np.round(Selected_transaction['valeur_fonciere'].mean())) + ' €')
            st.write('The mean price per square meter in the selected area is ' + str(np.round(Selected_transaction['prix_m2'].mean())) + ' €/m2')
            
            price_mean_evo = Selected_transaction[['year','prix_m2']]
            price_mean_evo_mean = price_mean_evo.groupby(['year']).mean()
            price_mean_evo_min = price_mean_evo.groupby(['year']).min()
            price_mean_evo_max = price_mean_evo.groupby(['year']).max()
            price_mean_evo_q5 = price_mean_evo.groupby(['year']).quantile(0.5)
            price_mean_evo_q25 = price_mean_evo.groupby(['year']).quantile(0.25)
            price_mean_evo_q75 = price_mean_evo.groupby(['year']).quantile(0.75)
            
            f=figure(
                title ='Pricing evolution',
                x_axis_label = 'year',
                y_axis_label = 'Price per square meter €/m2')
            
            f.line(price_mean_evo_mean.index,price_mean_evo_mean['prix_m2'],legend_label='Mean price per square meter',color = 'blue')
            f.line(price_mean_evo_q5.index,price_mean_evo_q5['prix_m2'],legend_label='Median price per square meter',color = 'red')
            f.line(price_mean_evo_q25.index,price_mean_evo_q25['prix_m2'],legend_label='q25 price per square meter',color = 'green')
            f.line(price_mean_evo_q75.index,price_mean_evo_q75['prix_m2'],legend_label='q75 price per square meter',color = 'black')
            
            st.bokeh_chart(f,use_container_width = True)
            
            st.write('The min price is : ' + str(np.round(sel_min_price)))
            st.write('The max price is : ' + str(np.round(sel_max_price)))
            