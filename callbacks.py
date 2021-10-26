from dash.dependencies import Input, Output, State, MATCH
from dash.exceptions import PreventUpdate
from dash import html
import dash_bootstrap_components as dbc
from dash import dcc
import dash
#from dash_table import DataTable

from app import app
import pandas as pd
import numpy as np
import json
import plotly.graph_objs as go
import plotly.express as px
import os
from functools import reduce

mttr_target_dict = {'All Regions':[5,10,''],'APAC': [5, 10,''],'EMEA': [5, 10,''],'Global - EMEA': [5, 10,''],
                            'LATAM': [7, 10,''],'NA.':[9, 8,''],'Global - NA':[8, 20,'']}
age_target_dict = {'All Regions':[5,'',30,''],'APAC': [5,'', 15,''], 'EMEA': [3,'', 3,''],'Global - EMEA': [4,'', 25,''],\
                           'LATAM': [7,'', 6,''],'NA.':[2,'', 51,''],'Global - NA':[1, '', 44, '']}
backlog_target_dict = {'All Regions':[16,'',301,''],'APAC': [5,'',15,''],'EMEA': [3,'', 3,''],'Global - EMEA': [4,'',100,''],\
                           'LATAM': [3,'', 25,''],'NA.':[2,'', 52,''],'Global - NA':[1,'', 79,'']}

gd_mttr_target_dict={'All Regions':[5,10,''],'APAC': [5, 10,''],'EMEA': [5, 10,''],'Global - EMEA': [5, 10,''],
                            'LATAM': ['', '',''],'NA.':[5, 10,''],'Global - NA':[5, 10,'']}
gd_age_target_dict = {'All Regions':[3,'',26,''],'APAC': [2,'', 14,''], 'EMEA': [1,'', 31,''],'Global - EMEA': [1,'', 31,''],\
                           'LATAM': ['','', '',''],'NA.':[1,'', 21,''],'Global - NA':[1, '', 43, '']}
gd_backlog_target_dict = {'All Regions':[3,'',120,''],'APAC': [1,'',2,''],'EMEA': [1,'', 55,''],'Global - EMEA': [1,'',55,''],\
                           'LATAM': ['','', '',''],'NA.':[1,'', 21,''],'Global - NA':[1,'', 43,'']}

incidentpivot=pd.DataFrame(columns=['Backlog',\
                                    '00-30','31-60','61-90','91-120','121-180','181-365','365+'])
srpivot=pd.DataFrame(columns=['Backlog',\
                                    '00-30','31-60','61-90','91-120','121-180','181-365','365+'])

age_bucket_columnlist = ['Ticket Type','Backlog With','00-30','31-60','61-90','91-120','121-180','181-365','365+']
age_bucket_col_heading = pd.DataFrame(columns=age_bucket_columnlist)

def get_incident_data(region, ticket, team, status):
    data = tickets[(tickets['Region'].isin(region))\
                    & (tickets['Ticket Type'].isin(ticket)) \
                    & (tickets['Team'].isin(team)) \
                    & (tickets['Status'] == status)]
    return data

def get_backlog_data1(region, ticket, team):
    data = backlog[(backlog['Region'].isin(region))\
                    & (backlog['Ticket Type'].isin(ticket)) \
                    & (backlog['Team'].isin(team))]
    return data

#================================================================================================================
# Function to address inconsistent columns in pivot tables
#================================================================================================================
def get_ticket_details(ticket_type,df,columnlist1,type='age'):
    data = [[ticket_type,'',0,0,0,0]]
    if len(df) == 0:
        df=pd.DataFrame(data,columns=columnlist1)      
        df.loc[len(df)] = data[0]
    elif len(df) == 1:
        df.loc[len(df)] = data[0]
        df.columns=columnlist1
    else:
        df.columns=columnlist1
    if ticket_type != 'total':
        if type == 'age':
            df.drop(['Backlog With'], inplace= True,axis = 1)
    return df    

#================================================================================================================
# Function to address inconsistent columns in pivot tables for health check
#================================================================================================================
def get_healthcheck_details(health_type,df,columnlist1):
    if len(df) == 0:
        data = [[health_type,0,0,0,0]]
        df=pd.DataFrame(data,columns=columnlist1)
    else:
        df.insert(0,column='Highest Volume (count)',value=health_type)
        df.columns=columnlist1
    return df       

#================================================================================================================
# Function to address inconsistent columns in pivot tables
#================================================================================================================
def get_ticket_type_details(ticket_type,df,columnlist,type='age'):
    col = []
    if len(df) == 0:
        data = [[ticket_type,0,0,0,0]]
        df=pd.DataFrame(data,columns=columnlist)
        if type == 'age':
            df.loc[len(df)] = data[0]
    else:
        df.columns = df.columns.droplevel(0)
        count = 0
        for i in df.columns:            
            if i == '' and count == 0:
                col.append('Ticket Type')
            elif i == '' and count == 1:
                col.append('Backlog With')
            else:
                new_name = 'WK ' + format(int(str(i)[4:]),'02')
                col.append(new_name)
            count += 1 
        df.columns=col
        if type == 'age':
            df.drop(['Backlog With'], inplace= True,axis = 1)
    return df     

#================================================================================================================
# Function to get ageing bucket
#================================================================================================================
def get_ticket_bucket(ticket_type,df):
    if len(df) == 0:
        df=pd.DataFrame(columns=age_bucket_columnlist)
    else:
        df.columns = df.columns.droplevel(0)
        df.columns.values[0] = 'Ticket Type'
        df.columns.values[1] = 'Backlog With'
        df = pd.merge(df,age_bucket_col_heading,how='left')
        df.fillna(0,inplace = True)
    df = df[['Ticket Type', 'Backlog With','00-30', '31-60', '61-90',\
                               '91-120', '121-180','181-365', '365+']]
    return df     

#================================================================================================================
# Find the difference between actual and target
#================================================================================================================
def find_shift(data,type='demand'):
    if data[1] == '':
        value = ''
    elif type == 'mttr' or type == 'age':
        if data[1]==0:
            value = '-'
        elif data[0]<data[1]:
            value = '⭐'
        else:
            value = '🔥'
    else:
        if data[0]>=data[1]:
            value = '⭐'
        else:
            value = '🔥'
    
    return value

#================================================================================================================
# Get the start and dates for the report
#================================================================================================================
def get_start_end_dates(weeksfile, year, endweek, slider=4):
    
    endweekindex = weeksfile.loc[(weeksfile["Year"] == year) & (weeksfile["Week"] == endweek)].index.tolist()
    startweekindex = endweekindex[0] - slider + 1
    if startweekindex < 0:        
        startweekindex = 0

    endweek = weeksfile.loc[endweekindex[0]:endweekindex[0]]
    startweek = weeksfile.loc[startweekindex:startweekindex]

    endyearweek = endweek['Year'].apply(str)+endweek['Week'].apply(str).apply(lambda x: x.zfill(2))
    endyearweek = int(endyearweek)

    startyearweek = startweek['Year'].apply(str)+startweek['Week'].apply(str).apply(lambda x: x.zfill(2))
    startyearweek = int(startyearweek)
    return startyearweek, endyearweek

#================================================================================================================
# Get the date for throughtput reprot
#================================================================================================================
def get_throughput_data(pageid, filterfield, actualtype, startyearweek, endyearweek):
# Filter the data by page id
    if pageid == 'keyapps':
        data = tickets[(tickets['Key Apps'].isin(filterfield))]
    elif pageid == 'regions' or pageid == "" or pageid == 'legacy':
        data = tickets[(tickets['Region'].isin(filterfield))]

# Get incident demand for the selected weeks        
# This will be used to plot new demand and status of incidents for selected weeks
    incident_demand = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'Incident') \
                    & (data['Status'] == 'Created') \
                    & (data['YearWeek'] >= startyearweek) \
                    & (data['YearWeek'] <= endyearweek)]

# Get service request demand for the selected weeks
# This will be used to plot new demand and status of service requests for selected weeks
    sr_demand = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'SR') \
                    & (data['Status'] == 'Created') \
                    & (data['YearWeek'] >= startyearweek) \
                    & (data['YearWeek'] <= endyearweek)]
    ser_demand = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'SER') \
                    & (data['Status'] == 'Created') \
                    & (data['YearWeek'] >= startyearweek) \
                    & (data['YearWeek'] <= endyearweek)]

# Get incident throughput for the selected weeks. 
# This will be used to plot throughput and MTTR of requests for selected weeks
    incident_throughput = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'Incident') \
                    & (data['Status'] == 'Resolved') \
                    & (data['YearWeek'] >= startyearweek) \
                    & (data['YearWeek'] <= endyearweek)]
# Get service request throughput for the selected weeks. 
# This will be used to plot throughput and MTTR for selected weeks
    sr_throughput = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'SR') \
                    & (data['Status'] == 'Resolved') \
                    & (data['YearWeek'] >= startyearweek) \
                    & (data['YearWeek'] <= endyearweek)]
        
    ser_throughput = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'SER') \
                    & (data['Status'] == 'Resolved') \
                    & (data['YearWeek'] >= startyearweek) \
                    & (data['YearWeek'] <= endyearweek)]    
    
# Get incident throughput for the current week. 
# This will be used to MTTR for current week
    incident_1_mttr = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'Incident') \
                    & (data['Status'] == 'Resolved') \
                    & (data['YearWeek'] == endyearweek)]
# Get service request throughput for the current week. 
# This will be used to MTTR for current week
    sr_1_mttr = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'SR') \
                    & (data['Status'] == 'Resolved') \
                    & (data['YearWeek'] == endyearweek)]
# Get incident demand for the current week. 
# This will be used to show the status of incident created in the week
    incident_1_week = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'Incident') \
                    & (data['Status'] == 'Created') \
                    & (data['YearWeek'] == endyearweek)]
# Get service request demand for the current week. 
# This will be used to show the status of incident created in the week
    sr_1_week = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'SR') \
                    & (data['Status'] == 'Created') \
                    & (data['YearWeek'] == endyearweek)]
    
    return incident_demand, sr_demand, ser_demand, incident_throughput, sr_throughput, ser_throughput, \
        incident_1_mttr, sr_1_mttr, incident_1_week, sr_1_week

#================================================================================================================
# Get the date for backlog reprot
#================================================================================================================
def get_backlog_data(pageid, filterfield, actualtype, startyearweek, endyearweek):

# Filter the data by page id
    if pageid == 'keyapps':
        data = backlog[(backlog['Key Apps'].isin(filterfield))]
    elif pageid == 'regions' or pageid == "" or pageid == 'legacy':
        data = backlog[(backlog['Region'].isin(filterfield))]

# Get incident demand for the selected weeks        
# This will be used to plot new demand and status of incidents for selected weeks
    incident_backlog = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'Incident') \
                    & (data['YearWeek'] >= startyearweek) \
                    & (data['YearWeek'] <= endyearweek)]

# Get service request demand for the selected weeks
# This will be used to plot new demand and status of service requests for selected weeks
    sr_backlog = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'SR') \
                    & (data['YearWeek'] >= startyearweek) \
                    & (data['YearWeek'] <= endyearweek)]

# Get incident demand for the current week. 
# This will be used to show the status of incident created in the week
    incibacklog_1_week = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'Incident') \
                    & (data['YearWeek'] == endyearweek)]
# Get service request demand for the current week. 
# This will be used to show the status of incident created in the week
    srbacklog_1_week = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'SR') \
                    & (data['YearWeek'] == endyearweek)]

    return incident_backlog, sr_backlog, incibacklog_1_week, srbacklog_1_week

def get_health_check_data(pageid, filterfield, actualtype, startyearweek, endyearweek):
    if pageid == 'keyapps':
        data = escalatedfile[(escalatedfile['Key Apps'].isin(filterfield))]
        data1 = reopenedfile[(reopenedfile['Key Apps'].isin(filterfield))]
        data2 = reassignedfile[(reassignedfile['Key Apps'].isin(filterfield))]
    elif pageid == 'regions' or pageid == "" or pageid == 'legacy':
        data = escalatedfile[(escalatedfile['Region'].isin(filterfield))]
        data1 = reopenedfile[(reopenedfile['Region'].isin(filterfield))]
        data2 = reassignedfile[(reassignedfile['Region'].isin(filterfield))]

# This will be used to plot new demand and status of incidents for selected weeks
    inci_escalated = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'Incident') \
                    & (data['YearWeek'] >= startyearweek) \
                    & (data['YearWeek'] <= endyearweek)]
    inci_reopen = data1[(data1['Team'].isin(actualtype)) \
                    & (data1['Ticket Type'] == 'Incident') \
                    & (data1['YearWeek'] >= startyearweek) \
                    & (data1['YearWeek'] <= endyearweek)]
    inci_reassign = data2[(data2['Team'].isin(actualtype)) \
                    & (data2['Ticket Type'] == 'Incident') \
                    & (data2['YearWeek'] >= startyearweek) \
                    & (data2['YearWeek'] <= endyearweek)]
    inci_escalated_1week = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'Incident') \
                    & (data['YearWeek'] == endyearweek)]
    inci_reopen_1week = data1[(data1['Team'].isin(actualtype)) \
                    & (data1['Ticket Type'] == 'Incident') \
                    & (data1['YearWeek'] == endyearweek)]
    inci_reassign_1week = data2[(data2['Team'].isin(actualtype)) \
                    & (data2['Ticket Type'] == 'Incident') \
                    & (data2['YearWeek'] == endyearweek)]

# Get service request demand for the selected weeks
# This will be used to plot new demand and status of service requests for selected weeks
    sr_escalated = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'SR') \
                    & (data['YearWeek'] >= startyearweek) \
                    & (data['YearWeek'] <= endyearweek)]
    sr_reopen = data1[(data1['Team'].isin(actualtype)) \
                    & (data1['Ticket Type'] == 'SR') \
                    & (data1['YearWeek'] >= startyearweek) \
                    & (data1['YearWeek'] <= endyearweek)]
    sr_reassign = data2[(data2['Team'].isin(actualtype)) \
                    & (data2['Ticket Type'] == 'SR') \
                    & (data2['YearWeek'] >= startyearweek) \
                    & (data2['YearWeek'] <= endyearweek)]
    sr_escalated_1week = data[(data['Team'].isin(actualtype)) \
                    & (data['Ticket Type'] == 'SR') \
                    & (data['YearWeek'] == endyearweek)]
    sr_reopen_1week = data1[(data1['Team'].isin(actualtype)) \
                    & (data1['Ticket Type'] == 'SR') \
                    & (data1['YearWeek'] == endyearweek)]
    sr_reassign_1week = data2[(data2['Team'].isin(actualtype)) \
                    & (data2['Ticket Type'] == 'SR') \
                    & (data2['YearWeek'] == endyearweek)]


    return inci_escalated,inci_reopen,inci_reassign,inci_escalated_1week,inci_reopen_1week,inci_reassign_1week,\
        sr_escalated,sr_reopen,sr_reassign,sr_escalated_1week,sr_reopen_1week,sr_reassign_1week


team_type = ['All', 'Local','GD',]
report_type = ['Demand','Throughput','MTTR','Backlog', 'Backlog Age']
ticket_type1 = ['All','Incident', 'SR', 'SER']
ticket_type2 = ['Incident', 'SR', 'SER']
regions = ['All Regions', 'APAC','EMEA','Global - EMEA','LATAM','NA.','Global - NA']

#================================================================================================================
# Read the data file and rename and create necessary fields
#================================================================================================================
#path =  "\\Dashboard Apps\\ServiceNowDashboard\\data\\"
path = os.getcwd()
path = os.path.join(path,'data\\')
cummulativethroughtputdata = path + 'Cummulative Weekly Incident Data.csv'
cummulativebacklogdata = path + 'Cummulative Weekly Backlog Data.csv'
reportweeks = path + 'Weeks.csv'
escalatedfilepath = path + 'Escalated.csv'
reopenedfilepath = path + 'Reopened.csv'
reassignedfilepath = path + 'Reassigned.csv'

colnames = ['Region','Key Apps','Team','Ticket Type','Number','YearWeek1']

chunksize = 10000
chunk_data = pd.read_csv(escalatedfilepath, usecols=colnames, iterator = True, chunksize=chunksize, \
                         infer_datetime_format= True)
escalatedfile = pd.concat(chunk_data, ignore_index=True)
escalatedfile.rename(columns={'YearWeek1':'YearWeek'},inplace=True)

chunksize = 10000
chunk_data = pd.read_csv(reopenedfilepath, usecols=colnames, iterator = True, chunksize=chunksize, \
                         infer_datetime_format= True)
reopenedfile = pd.concat(chunk_data, ignore_index=True)
reopenedfile.rename(columns={'YearWeek1':'YearWeek'},inplace=True)

chunksize = 10000
chunk_data = pd.read_csv(reassignedfilepath, usecols=colnames, iterator = True, chunksize=chunksize, \
                         infer_datetime_format= True)
reassignedfile = pd.concat(chunk_data, ignore_index=True)
reassignedfile.rename(columns={'YearWeek1':'YearWeek'},inplace=True)

weeksfile = pd.read_csv(reportweeks)
weeksfile.sort_values(['Year','Week'], ascending = [False, False], inplace=True)
currentyear = weeksfile['Year'].max()
years = weeksfile['Year'].unique()
weeks = weeksfile[weeksfile['Year'] == currentyear]
week1 = weeks['Week'].unique()
currentweek = weeks['Week'].unique().max()

#=======================================================================================================================
# Read Historical data in chunks
#=======================================================================================================================

colnames = ['Region','Key Apps','Team','Ticket Type','Number','State','YearWeekCreated','YearWeekResolved','MTTR',\
            'Year Created/Resolved','Week Created/Resolved',\
                'YearWeek','State_Type']

chunksize = 250000
chunk_data = pd.read_csv(cummulativethroughtputdata, usecols=colnames, iterator = True, chunksize=chunksize, \
                         infer_datetime_format= True)
tickets = pd.concat(chunk_data, ignore_index=True)

tickets.rename(columns={'Week Created/Resolved':'Week','Year Created/Resolved':'Year',
                                'State_Type':'Status', 'Resource Type':'Team'}, inplace=True)
                        
tickets['Week'] = tickets['Week'].apply(int)
tickets['Weekstr'] = tickets['Week'].apply(str).apply(lambda x: x.zfill(2))
tickets['Yearstr'] = tickets["Year"].apply(str) 
tickets.sort_values(['Ticket Type','Status','YearWeek'],ignore_index=True,inplace=True)

#=======================================================================================================================
# Read Historical backlog data in chunks
#=======================================================================================================================
colnames = ['Region','Key Apps','Team','Ticket Type','Number','State', 'Reason',\
            'Age','Ageing Bucket','Backlog With','Week_Reported','YearWeek']
chunksize = 250000
chunk_data = pd.read_csv(cummulativebacklogdata, iterator = True, usecols=colnames, chunksize=chunksize,\
                         infer_datetime_format= True)
backlog = pd.concat(chunk_data, ignore_index=True)

backlog.rename(columns={'Week_Reported':'Week Reported', 'Ageing Bucket':'Age Bucket'
                        }, inplace=True)

backlog[['Yearstr', 'Weekstr']] = backlog['Week Reported'].str.split("-",expand=True)
backlog.sort_values(['Ticket Type','YearWeek'],ignore_index=True,inplace=True)

#================================================================================================================
# Callback to get the weeks for the selected Year
#================================================================================================================
@app.callback(
    Output("week-dropdown", "options"),
    Input("year-dropdown", "value"),prevent_initial_call=True)
def year_callback(currentyear):
    weeks = weeksfile[weeksfile['Year'] == currentyear]
    weeks = weeks['Week'].unique()
    return [{'label': i, 'value': i} for i in weeks]

#================================================================================================================
# Associated callback to get the weeks for the selected Year
#================================================================================================================
@app.callback(
    Output('week-dropdown', 'value'),
    [Input('week-dropdown', 'options')],prevent_initial_call=True)
def week_callback(available_options):
    endweek = available_options[0].get('value')
    return endweek

@app.callback(
    [Output('throughput-container','style'),
    Output('backlog-container','style'),],
    [Input('report-dropdown','value'),
     Input("url","pathname")])

def decide_function(reporttype,pathname):

    pageid = pathname.split("/")[2]
    if pageid == 'regions' or pageid == 'keyapps' or pageid == '':       
        if reporttype == 'Backlog':
            return {'display':'None'}, {'display':'Block'}
        elif reporttype == 'Throughput':
            return {'display':'Block'}, {'display':'None'}
    else:
            return {'display':'None'}, {'display':'None'}
        
@app.callback(
    [Output("intermediate-value", "data"),
    Output("startyearweek", "data"),
    Output("endyearweek", "data"),],
    [Input("region-dropdown", "value"),
     Input("year-dropdown","value"),
     Input("week-dropdown","value"),
     Input("resource-dropdown","value"),
     Input("report-dropdown","value"),
     Input("week-slider","value"),
     Input("url","pathname"),])

def data_processing(region,year,endweek,resourcetype, reporttype, slider,pathname):

    trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if trigger == "year-dropdown":
        raise PreventUpdate()

    pageid = pathname.split("/")[2]

    if pageid in ['legacy','compare','sla','themes']:
        raise PreventUpdate()
        
#    if type(endweek) is dict:
#        endweek = endweek.get('value')
        
    # Get the start and dates for the report
    startyearweek, endyearweek = get_start_end_dates(weeksfile, year, endweek, slider)

    if 'All Regions' in region:
        actualregion = ['APAC','EMEA','Global - EMEA','LATAM','NA.','Global - NA']
    else:
        actualregion = [region]
        
    if 'All' in resourcetype:
        actualtype = ['Local','GD']
    else:
        actualtype = [resourcetype]
    if reporttype == 'Throughput':      
    # Get filetered data
        incident_demand, sr_demand, ser_demmand, incident_throughput, sr_throughput, ser_throughput, incident_1_mttr,\
            sr_1_mttr, incident_1_week, sr_1_week = get_throughput_data(pageid,actualregion,actualtype,startyearweek,endyearweek)
    # Perform the aggregarion for Incidents        
        incident_demand_by_week = incident_demand.groupby(['Yearstr','Weekstr'])[['Number']].count().reset_index().sort_values(['Yearstr','Weekstr'])
        incident_throughput_by_week = incident_throughput.groupby(['Yearstr','Weekstr'])[['Number']].count().reset_index().sort_values(['Yearstr','Weekstr'])
        incident_demand_throughput_by_week = pd.merge(incident_demand_by_week,incident_throughput_by_week, on=['Yearstr','Weekstr'], how='outer')
        incident_demand_throughput_by_week.fillna(0,inplace=True)
        incident_demand_throughput_by_week.sort_values(['Yearstr','Weekstr'],inplace=True)
        # Perform the aggregarion for service requests     
        sr_demand_by_week = sr_demand.groupby(['Yearstr','Weekstr'])[['Number']].count().reset_index().sort_values(['Yearstr','Weekstr'])
        sr_throughput_by_week = sr_throughput.groupby(['Yearstr','Weekstr'])[['Number']].count().reset_index().sort_values(['Yearstr','Weekstr'])
        sr_demand_throughput_by_week = pd.merge(sr_demand_by_week,sr_throughput_by_week, on=['Yearstr','Weekstr'], how='outer')
        sr_demand_throughput_by_week.fillna(0,inplace=True)
        sr_demand_throughput_by_week.sort_values(['Yearstr','Weekstr'],inplace=True)

        inci_escalated,inci_reopen,inci_reassign,inci_escalated_1week,inci_reopen_1week,inci_reassign_1week, sr_escalated,\
            sr_reopen,sr_reassign,sr_escalated_1week,sr_reopen_1week,sr_reassign_1week = get_health_check_data(pageid,actualregion,actualtype,startyearweek,endyearweek)

        datasets = {

        # 1st row graphs
        'incident_demand_throughput_by_week': incident_demand_throughput_by_week.to_json(orient='split', date_format='iso'),
         'sr_demand_throughput_by_week': sr_demand_throughput_by_week.to_json(orient='split', date_format='iso'),
         #2nd row graphs
         'incident_1_mttr': incident_1_mttr.to_json(orient='split', date_format='iso'),
         'incident_throughput': incident_throughput.to_json(orient='split', date_format='iso'),
         'sr_1_mttr': sr_1_mttr.to_json(orient='split', date_format='iso'),
         'sr_throughput': sr_throughput.to_json(orient='split', date_format='iso'),
         #3rd row graphs
         'incident_1_week': incident_1_week.to_json(orient='split', date_format='iso'),
         'incident_demand': incident_demand.to_json(orient='split', date_format='iso'),
         'sr_1_week': sr_1_week.to_json(orient='split', date_format='iso'),
         'sr_demand': sr_demand.to_json(orient='split', date_format='iso'),
         #Data values for health check
         'inci_escalated': inci_escalated.to_json(orient='split',date_format='iso'),
         'inci_reopen': inci_reopen.to_json(orient='split',date_format='iso'),
         'inci_reassign': inci_reassign.to_json(orient='split',date_format='iso'),
         'inci_escalated_1week': inci_escalated_1week.to_json(orient='split',date_format='iso'),
         'inci_reopen_1week': inci_reopen_1week.to_json(orient='split',date_format='iso'),
         'inci_reassign_1week': inci_reassign_1week.to_json(orient='split',date_format='iso'),
         'sr_escalated': sr_escalated.to_json(orient='split',date_format='iso'),
         'sr_reopen': sr_reopen.to_json(orient='split',date_format='iso'),
         'sr_reassign': sr_reassign.to_json(orient='split',date_format='iso'),
         'sr_escalated_1week': sr_escalated_1week.to_json(orient='split',date_format='iso'),
         'sr_reopen_1week': sr_reopen_1week.to_json(orient='split',date_format='iso'),
         'sr_reassign_1week': sr_reassign_1week.to_json(orient='split',date_format='iso'),
         }
    else:
        # Get filetered data
        incident_backlog, sr_backlog, incibacklog_1_week, srbacklog_1_week \
            = get_backlog_data(pageid,actualregion,actualtype,startyearweek,endyearweek)
            
        # Perform the aggregarion for Incidents        
        incident_backlog_by_week1 = incident_backlog.groupby(['Yearstr','Weekstr'])[['Number']].count().reset_index().sort_values(['Yearstr','Weekstr'])
        incident_backlog_by_week1['Backlog With'] = 'Total'
        incident_backlog_by_week1 = incident_backlog_by_week1[['Yearstr','Weekstr','Backlog With','Number']]
        incident_backlog_by_week2 = incident_backlog.groupby(['Yearstr','Weekstr','Backlog With'])[['Number']].count().reset_index().sort_values(['Yearstr','Weekstr'])
        incident_backlog_by_week = incident_backlog_by_week1.append(incident_backlog_by_week2)
        incident_backlog_by_week.sort_values(['Yearstr','Weekstr','Backlog With'], inplace=True)
        # Perform the aggregarion for service requests     
        sr_backlog_by_week1 = sr_backlog.groupby(['Yearstr','Weekstr'])[['Number']].count().reset_index().sort_values(['Yearstr','Weekstr'])
        sr_backlog_by_week1['Backlog With'] = 'Total'
        sr_backlog_by_week1 = sr_backlog_by_week1[['Yearstr','Weekstr','Backlog With','Number']]
        sr_backlog_by_week2 = sr_backlog.groupby(['Yearstr','Weekstr','Backlog With'])[['Number']].count().reset_index().sort_values(['Yearstr','Weekstr'])
        sr_backlog_by_week = sr_backlog_by_week1.append(sr_backlog_by_week2)
        sr_backlog_by_week.sort_values(['Yearstr','Weekstr','Backlog With'], inplace=True)
        
    # Perform the aggregarion for Incidents        
        incident_backlogage_by_week1 = incident_backlog.groupby(['Yearstr','Weekstr'])[['Age']].mean().reset_index().sort_values(['Yearstr','Weekstr'])
        incident_backlogage_by_week1['Backlog With'] = 'Total'
        incident_backlogage_by_week1 = incident_backlogage_by_week1[['Yearstr','Weekstr','Backlog With','Age']]
        incident_backlogage_by_week2 = incident_backlog.groupby(['Yearstr','Weekstr','Backlog With'])[['Age']].mean().reset_index().sort_values(['Yearstr','Weekstr'])
        incident_backlogage_by_week = incident_backlogage_by_week1.append(incident_backlogage_by_week2)
        incident_backlogage_by_week.sort_values(['Yearstr','Weekstr','Backlog With'], inplace=True)
        # Perform the aggregarion for service requests     
        sr_backlogage_by_week1 = sr_backlog.groupby(['Yearstr','Weekstr'])[['Age']].mean().reset_index().sort_values(['Yearstr','Weekstr'])
        sr_backlogage_by_week1['Backlog With'] = 'Total'
        sr_backlogage_by_week1 = sr_backlogage_by_week1[['Yearstr','Weekstr','Backlog With','Age']]
        sr_backlogage_by_week2 = sr_backlog.groupby(['Yearstr','Weekstr','Backlog With'])[['Age']].mean().reset_index().sort_values(['Yearstr','Weekstr'])
        sr_backlogage_by_week = sr_backlogage_by_week1.append(sr_backlogage_by_week2)
        sr_backlogage_by_week.sort_values(['Yearstr','Weekstr','Backlog With'], inplace=True)

        columnlist = []
        if len(incibacklog_1_week) == 0:
            incident_pivot=pd.DataFrame(columns=['Backlog','00-30','31-60','61-90','91-120','121-180','181-365','365+'])
            for i in incident_pivot.columns[1:]:
                columnlist.append(incident_pivot[i].sum())
        else:
            incident_pivot = pd.pivot_table(incibacklog_1_week,index=['Backlog With',], values=['Number'],
                     columns=['Age Bucket'],
                     aggfunc=len, fill_value=0).reset_index()
            incident_pivot.columns = incident_pivot.columns.droplevel(0)
            incident_pivot.columns.values[0] = "Backlog"
            incident_pivot.sort_values(['Backlog'], inplace=True)
            for i in incident_pivot.columns[1:]:
                columnlist.append(incident_pivot[i].sum())    
        columnlist.insert(0,'Total')
        incident_pivot.loc[len(incident_pivot.index)] = columnlist

        columnlist = []
        if len(srbacklog_1_week) == 0:
            sr_pivot=pd.DataFrame(columns=['Backlog','00-30','31-60','61-90','91-120','121-180','181-365','365+'])
            for i in sr_pivot.columns[1:]:
                columnlist.append(sr_pivot[i].sum())
        else:
            sr_pivot = pd.pivot_table(srbacklog_1_week,index=['Backlog With',], values=['Number'],
                     columns=['Age Bucket'],
                     aggfunc=len, fill_value=0).reset_index()
            sr_pivot.columns = sr_pivot.columns.droplevel(0)
            sr_pivot.columns.values[0] = "Backlog"
            sr_pivot.sort_values(['Backlog',], inplace=True)
            for i in sr_pivot.columns[1:]:
                columnlist.append(sr_pivot[i].sum())    
        columnlist.insert(0,'Total')
        sr_pivot.loc[len(sr_pivot.index)] = columnlist

        columnlist = []
        if len(incibacklog_1_week) == 0:
            incident_pivot1=pd.DataFrame(columns=['Backlog','00-30','31-60','61-90','91-120','121-180','181-365','365+'])
            for i in incident_pivot1.columns[1:]:
                columnlist.append(incident_pivot[i].sum())
        else:
            incibacklog_1_week['Reason'].fillna('Work In Progress', inplace=True)
            incident_pivot1 = pd.pivot_table(incibacklog_1_week,index=['Reason'], values=['Number'],
                     columns=['Age Bucket'],
                     aggfunc=len, fill_value=0).reset_index()
            incident_pivot1.columns = incident_pivot1.columns.droplevel(0)
            incident_pivot1.columns.values[0] = "Backlog"
            for i in incident_pivot1.columns[1:]:
                columnlist.append(incident_pivot1[i].sum())    
        columnlist.insert(0,'Total')
        incident_pivot1.loc[len(incident_pivot1.index)] = columnlist

        columnlist = []
        if len(srbacklog_1_week) == 0:
            sr_pivot1=pd.DataFrame(columns=['Backlog','00-30','31-60','61-90','91-120','121-180','181-365','365+'])
            for i in sr_pivot1.columns[1:]:
                columnlist.append(sr_pivot[i].sum())
        else:
            srbacklog_1_week['Reason'].fillna('Work In Progress', inplace=True)
            sr_pivot1 = pd.pivot_table(srbacklog_1_week,index=['Reason'], values=['Number'],
                     columns=['Age Bucket'],
                     aggfunc=len, fill_value=0).reset_index()
            sr_pivot1.columns = sr_pivot1.columns.droplevel(0)
            sr_pivot1.columns.values[0] = "Backlog"
            for i in sr_pivot1.columns[1:]:
                columnlist.append(sr_pivot1[i].sum())    
        columnlist.insert(0,'Total')
        sr_pivot1.loc[len(sr_pivot1.index)] = columnlist

    # Store all intermediate-valued as json data to be passed for plotting graphs        
        datasets = {

        'incibacklog_1_week': incibacklog_1_week.to_json(orient='split', date_format='iso'),
        'srbacklog_1_week': srbacklog_1_week.to_json(orient='split', date_format='iso'),
        # 1st row graphs
        'incident_backlog_by_week': incident_backlog_by_week.to_json(orient='split', date_format='iso'),
        'sr_backlog_by_week': sr_backlog_by_week.to_json(orient='split', date_format='iso'),
        #2nd row graphs
        'incident_backlogage_by_week': incident_backlogage_by_week.to_json(orient='split', date_format='iso'),
        'sr_backlogage_by_week': sr_backlogage_by_week.to_json(orient='split', date_format='iso'),
        'incident_pivot': incident_pivot.to_json(orient='split', date_format='iso'),
        'sr_pivot': sr_pivot.to_json(orient='split', date_format='iso'),
        'incident_pivot1': incident_pivot1.to_json(orient='split', date_format='iso'),
        'sr_pivot1': sr_pivot1.to_json(orient='split', date_format='iso'),
     }
    return json.dumps(datasets), startyearweek, endyearweek

#================================================================================================================
# Main callback to create the dashboard
#================================================================================================================
@app.callback(
    [Output("incident_demand_vs_throughput", "figure"),
    Output("sr_demand_vs_throughput", "figure"),
      Output("incident_1_mttr", "figure"), Output("incident_x_mttr", "figure"), 
      Output("sr_1_mttr", "figure"), Output("sr_x_mttr", "figure"),
      Output("incident_1_week", "figure"), Output("incident_x_week", "figure"), 
      Output("sr_1_week", "figure"), Output("sr_x_week", "figure"),
      Output("created1", "children"), Output("resolved1", "children"),
      Output("reassigned1", "children"), Output("reopened1", "children"), Output("escalated1", "children"),
      Output("created2", "children"), Output("resolved2", "children"),
      Output("reassigned2", "children"),Output("reopened2", "children"), Output("escalated2", "children"),
      Output("created11", "children"), Output("resolved11", "children"),
      Output("reassigned11", "children"),Output("reopened11", "children"), Output("escalated11", "children"),
      Output("created22", "children"), Output("resolved22", "children"),
      Output("reassigned22", "children"),Output("reopened22", "children"), Output("escalated22", "children"),
      Output("header1", "children"), Output("header2", "children"),
      Output("header3", "children"), Output("header4", "children"),], 
      [Input("intermediate-value", "data"), Input("startyearweek","data"), Input("endyearweek","data"),
      Input("report-dropdown","value"),Input("week-slider","value"),
      Input("url","pathname"),])
def create_throughput_page(dataframes,startyearweek,endyearweek,reporttype,slider,pathname):
    
    pageid = pathname.split("/")[2]

    if pageid in ['legacy','compare','sla','themes']:
        raise PreventUpdate

    if reporttype == 'Backlog':
        raise PreventUpdate

#================================================================================================================
# Create Header Strings
#================================================================================================================
    year1 = str(endyearweek)[:4]
    week1 = str(endyearweek)[4:]
    header1 = 'Incidents for week ' + week1 + '-' + year1 
    header2 = 'Service Requests for week ' + week1 + '-' + year1 
    year2 = str(startyearweek)[:4]
    week2 = str(startyearweek)[4:]
    header3 = 'Incidents for weeks ' + week2 + '-' + year2 + ' to ' + week1 + '-' + year1 + ' ( ' + str(slider) + ' Week Period )'
    header4 = 'Service Requests for weeks ' + week2 + '-' + year2 + ' to ' + week1 + '-' + year1 + ' ( ' + str(slider) + ' Week Period )'
#================================================================================================================
# Charts for 1st Row
#================================================================================================================
# Chart 1 - Incident demand vs throughput
#================================================================================================================
    
    datasets = json.loads(dataframes)
    data = pd.read_json(datasets['incident_demand_throughput_by_week'], orient='split')
    data['Yearstr'] = data['Yearstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    if len(data) != 0:
        data['YearWeekstr'] = data['Yearstr'].str[2:] + '/' + data['Weekstr']
    else:
        data['YearWeekstr'] = data['Weekstr']

    incifig = go.Figure()
    incifig.add_trace(go.Bar(x=data['YearWeekstr'], y=data['Number_x'], name='Demand',marker_color=px.colors.qualitative.Dark2[0])),
    incifig.add_trace(go.Bar(x=data['YearWeekstr'], y=data['Number_y'], name='Throughput',marker_color=px.colors.qualitative.Dark2[1])),

    incifig.update_layout(template="plotly_dark",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        title={'text': 'Incidents','y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
        xaxis_title="Week",
        font=dict(family="sans-serif, monospace",size=10,color="white"),
        height=185,
        margin=dict(l=10,r=10,b=10,t=10,),
    ),

#================================================================================================================
# Chart 2 - Service Request demand vs throughput
#================================================================================================================
    
    datasets = json.loads(dataframes)
    data = pd.read_json(datasets['sr_demand_throughput_by_week'], orient='split')
    data['Yearstr'] = data['Yearstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    if len(data) != 0:
        data['YearWeekstr'] = data['Yearstr'].str[2:] + '/' + data['Weekstr']
    else:
        data['YearWeekstr'] = data['Weekstr']
    srfig = go.Figure()
    srfig.add_trace(go.Bar(x=data['YearWeekstr'], y=data['Number_x'], name='Demand', marker_color=px.colors.qualitative.Dark2[0])),
    srfig.add_trace(go.Bar(x=data['YearWeekstr'], y=data['Number_y'], name='Throughput',marker_color=px.colors.qualitative.Dark2[1])),

    srfig.update_layout(template="plotly_dark",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        title={'text': 'Service Requests','y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
        xaxis_title="Week",
        font=dict(family="sans-serif, monospace",size=10,color="white"),
        height=185,
        margin=dict(l=10,r=10,b=10,t=10,),
    ),
    
#================================================================================================================
# Charts for 2nd Row
#================================================================================================================
# Chart 1 - Incident MTTR for report week
#================================================================================================================

    datasets = json.loads(dataframes)
    incident_mttr = pd.read_json(datasets['incident_1_mttr'], orient='split')
    inci_resolved1 = len(incident_mttr)
    incident_mttr = round(incident_mttr['MTTR'].mean(),1)
    text = 'Incident MTTR: ' + 'week ' + week1
    incident_mttr_gauge1 = go.Figure(go.Indicator(
        mode = 'gauge+number+delta', value = incident_mttr,
        domain = {'x':[0, 1], 'y':[0, 1]},
        delta = {'reference': 5, 'increasing': {'color': "red"},'decreasing': {'color': "green"}, 'position':'right'},
        gauge =  {
                'shape': "bullet",
                'axis': {'range': [None, 10]},
                'threshold': {'line': {'color': "orange", 'width': 4},
                                'thickness': 1.00,'value':5},
                'steps': [
                    {'range': [0, 5], 'color': "lightgreen"},
                    {'range': [5, 7], 'color': "yellow"},
                    {'range': [7, 10], 'color': "red"}],
                'bar': {'color': "Black",'thickness':0.5},
                'bordercolor':'white',
                'borderwidth':1}
        ),layout={"height":70, })

    incident_mttr_gauge1.update_layout(template="plotly_dark",
          legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
          title={'text': text,'y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
                  font=dict(family="sans-serif, monospace",size=9,color="white",),
                                            margin=dict(l=10,r=10,b=25,t=30),)
    incident_mttr_gauge1.update_traces(number_font_family = "sans-serif",  number_font_size=20,)

#================================================================================================================
# Chart 2 - Incident MTTR for selected weeks
#================================================================================================================
    
    datasets = json.loads(dataframes)
    incident_mttr = pd.read_json(datasets['incident_throughput'], orient='split')
    inci_resolved2 = len(incident_mttr)
    incident_mttr = round(incident_mttr['MTTR'].mean(),1)

    text = 'Incident MTTR : ' + 'week ' + week2 + ' to week ' + week1
    incident_mttr_gauge2 = go.Figure(go.Indicator(
        mode = 'gauge+number+delta', value = incident_mttr,
        domain = {'x':[0, 1], 'y':[0, 1]},
        delta = {'reference': 5, 'increasing': {'color': "red"},'decreasing': {'color': "green"}, 'position':'right'},
        gauge =  {
                'shape': "bullet",
                'axis': {'range': [None, 10]},
                'threshold': {'line': {'color': "orange", 'width': 4},
                                'thickness': 1.00,'value':5},
                'steps': [
                    {'range': [0, 5], 'color': "lightgreen"},
                    {'range': [5, 7], 'color': "yellow"},
                    {'range': [7, 10], 'color': "red"}],
                'bar': {'color': "Black",'thickness':0.5},
                'bordercolor':'white',
                'borderwidth':1}
        ),layout={"height":70, })

    incident_mttr_gauge2.update_layout(template="plotly_dark",
          legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
          title={'text': text,'y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
                  font=dict(family="sans-serif, monospace",size=9,color="white",),
                                            margin=dict(l=10,r=10,b=25,t=30),)
    incident_mttr_gauge2.update_traces(number_font_family = "sans-serif",  number_font_size=20,)

#================================================================================================================
# Chart 3 - Service Request MTTR for report week
#================================================================================================================
    
    datasets = json.loads(dataframes)
    sr_mttr = pd.read_json(datasets['sr_1_mttr'], orient='split')
    sr_resolved1 = len(sr_mttr)
    sr_mttr = round(sr_mttr['MTTR'].mean(),1)

    text = 'Service Request MTTR : ' + 'week ' + week1    
    sr_mttr_gauge1 = go.Figure(go.Indicator(
        mode = 'gauge+number+delta', value = sr_mttr,
        domain = {'x':[0, 1], 'y':[0, 1]},
        delta = {'reference': 10, 'increasing': {'color': "red"},'decreasing': {'color': "green"}, 'position':'right'},
        gauge = {'shape': "bullet",
                'axis': {'range': [None, 20]},
                 'threshold': {'line': {'color': "orange", 'width': 4},
                                'thickness': 1.0,'value':10},
                'steps': [
                    {'range': [0, 10], 'color': "lightgreen"},
                    {'range': [10, 15], 'color': "yellow"},
                    {'range': [15, 20], 'color': "red"}],
                'bar': {'color': "Black",'thickness':0.5},
                'bordercolor':'white',
                'borderwidth':1}
        ),layout={"height":70,})
    sr_mttr_gauge1.update_layout(template="plotly_dark",
          legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
          title={'text': text,'y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
                  font=dict(family="sans-serif, monospace",size=9,color="white",),
                                            margin=dict(l=10,r=10,b=25,t=30),)
    sr_mttr_gauge1.update_traces(number_font_family = "sans-serif",  number_font_size=20,)

#================================================================================================================
# Chart 4 - Service Request MTTR for selected weeks
#================================================================================================================
    
    datasets = json.loads(dataframes)
    sr_mttr = pd.read_json(datasets['sr_throughput'], orient='split')
    sr_resolved2 = len(sr_mttr)
    sr_mttr = round(sr_mttr['MTTR'].mean(),1)

    text = 'Service Request MTTR: ' + 'week ' + week2 + ' to week ' + week1
    sr_mttr_gauge2 = go.Figure(go.Indicator(
        mode = 'gauge+number+delta', value = sr_mttr,
        domain = {'x':[0, 1], 'y':[0, 1]},
        delta = {'reference': 10, 'increasing': {'color': "red"},'decreasing': {'color': "green"}, 'position':'right'},
        gauge = {'shape': "bullet",
                'axis': {'range': [None, 20]},
                'threshold': {'line': {'color': "orange", 'width': 4},
                                'thickness': 1.0,'value':10},
                'steps': [
                    {'range': [0, 10], 'color': "lightgreen"},
                    {'range': [10, 15], 'color': "yellow"},
                    {'range': [15, 20], 'color': "red"}],
                'bar': {'color': "Black",'thickness':0.5},
                'bordercolor':'white',
                'borderwidth':1}
        ),layout={"height":70,})
    sr_mttr_gauge2.update_layout(template="plotly_dark",
          legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
          title={'text': text,'y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
                  font=dict(family="sans-serif, monospace",size=9,color="white",),
                                            margin=dict(l=10,r=10,b=25,t=30),)
    sr_mttr_gauge2.update_traces(number_font_family = "sans-serif",  number_font_size=20,)    

#================================================================================================================
# Charts for 3rd Row
#================================================================================================================
# Chart 1 - Incident spread by status for the current week
#================================================================================================================
  
    datasets = json.loads(dataframes)
    incident_spread = pd.read_json(datasets['incident_demand_throughput_by_week'], orient='split')
    incident = pd.read_json(datasets['incident_1_week'], orient='split')
    if len(incident) == 0:
        inci_created1 = inci_reassigned1 = inci_reopened1 = inci_escalated1 = value = resolved = 0
    else:
        inci_created1 = incident_spread['Number_x'].iloc[-1]   
#        inci_reassigned1 = incident['Reassigned Flag'].sum()
#        inci_reopened1 = incident['Reopened Flag'].sum()
#        inci_escalated1 = incident['Escalated Flag'].sum()
        incident['Match'] = np.where(incident['YearWeekResolved']==incident['YearWeekCreated'], 
                                           'yes', 'no')
        resolved = len(incident[(incident['Match']=='yes')])
        if inci_created1 == 0:
            value = 0
        else:
            value = round((resolved/inci_created1),2)

    text = 'Resolution Rate of New Demand: ' + 'week ' + week1
    
    axisrange = [None, 1]
    incident_gauge1 = go.Figure(go.Indicator(
        mode = 'gauge+number+delta',
        number = {'valueformat': '0%'},
        value = value,
        domain = {'x':[0, 1], 'y':[0, 1]},
        delta = {'reference': .7, 'valueformat': '0%',
                 'increasing': {'color': "green"},'decreasing': {'color': "red"}, 'position':'top'},
        gauge = {
            'shape': 'angular',
            'axis': {'range': axisrange, 'tickformat':'0%'},
            'bar': {'color': 'black','thickness':0.5},
            'threshold': {'line': {'color': "white", 'width': 4},
                          'thickness': 1.0,'value':.7, },
            'steps': [
                {'range': [0, .3], 'color': 'red',},
                {'range': [.3, .6], 'color': 'yellow'},
                {'range': [.6, 1], 'color': 'green'},
                ],
            }),layout={"height":145,})
    
    incident_gauge1.update_layout(template="plotly_dark",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
          title={'text': text,'y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
                  font=dict(family="sans-serif, monospace",size=9,color="white"),
                                            margin=dict(l=20,r=20,b=5,t=40),hovermode='x')
    incident_gauge1.update_traces(number_font_family = "sans-serif",  number_font_size=26,name='Guage Chart')  
# #============================================================================================================    
# # Chart 2 - Incident spread by status for the selected weeks
# #============================================================================================================    

    datasets = json.loads(dataframes)

    incident_spread = pd.read_json(datasets['incident_demand_throughput_by_week'], orient='split')
    incident = pd.read_json(datasets['incident_demand'], orient='split')

    if len(incident) == 0:
        inci_created2 = inci_reassigned2 = inci_reopened2 = inci_escalated2 = value = resolved = 0
    else:
        inci_created2 = incident_spread['Number_x'].sum() 
#        inci_reassigned2 = incident['Reassigned Flag'].sum()
#        inci_reopened2 = incident['Reopened Flag'].sum()
#        inci_escalated2 = incident['Escalated Flag'].sum()
        incident['Match'] = np.where(incident['YearWeekResolved']==incident['YearWeekCreated'], 
                                           'yes', 'no')
        resolved = len(incident[(incident['Match']=='yes')])
        value = round((resolved/inci_created2),2)

    text = 'Resolution Rate of New Demand: ' + 'week ' + week2 + ' to week ' + week1    

    axisrange = [None, 1]
    incident_gauge2 = go.Figure(go.Indicator(
        mode = 'gauge+number+delta',
        number = {'valueformat': '0%'},
        value = value,
        domain = {'x':[0, 1], 'y':[0, 1]},
        delta = {'reference': .7, 'valueformat': '0%',
                 'increasing': {'color': "green"},'decreasing': {'color': "red"}, 'position':'top'},
        gauge = {
            'shape': 'angular',
            'axis': {'range': axisrange, 'tickformat':'0%'},
            'bar': {'color': 'black','thickness':0.5},
            'threshold': {'line': {'color': "white", 'width': 4},
                          'thickness': 1.0,'value':0.7},
            'steps': [
                {'range': [0, .3], 'color': 'red',},
                {'range': [.3, .6], 'color': 'yellow'},
                {'range': [.6, 1], 'color': 'green'},
                ],
            }),layout={"height":145,})
      
    incident_gauge2.update_layout(template="plotly_dark",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
          title={'text': text,'y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
                  font=dict(family="sans-serif, monospace",size=9,color="white"),
                                            margin=dict(l=20,r=20,b=5,t=40),)
    incident_gauge2.update_traces(number_font_family = "sans-serif",  number_font_size=26,)

#============================================================================================================    
# Chart 3 - Service Request spread by status for the current week
#============================================================================================================    

    datasets = json.loads(dataframes)

    sr_spread = pd.read_json(datasets['sr_demand_throughput_by_week'], orient='split')
    sr = pd.read_json(datasets['sr_1_week'], orient='split')
    if len(sr) == 0:
        sr_created1 = sr_reassigned1 = sr_reopened1 = sr_escalated1 = value = resolved = 0
    else:
        sr_created1 = sr_spread['Number_x'].iloc[-1]   
#        sr_reassigned1 = sr['Reassigned Flag'].sum()
#        sr_reopened1 = sr['Reopened Flag'].sum()
#        sr_escalated1 = sr['Escalated Flag'].sum()
        sr['Match'] = np.where(sr['YearWeekResolved']==sr['YearWeekCreated'], 
                                           'yes', 'no')
        resolved = len(sr[(sr['Match']=='yes')])
        if sr_created1 == 0:
            value = 0
        else:
            value = round((resolved/sr_created1),2)

    text = 'Resolution Rate of New Demand: ' + 'week ' + week1
    axisrange = [None, 1]
    sr_gauge1 = go.Figure(go.Indicator(
        mode = 'gauge+number+delta',
        number = {'valueformat': '0%'},
        value = value,
        domain = {'x':[0, 1], 'y':[0, 1]},
        delta = {'reference': .7, 'valueformat': '0%',
                 'increasing': {'color': "green"},'decreasing': {'color': "red"}, 'position':'top'},
        gauge = {
            'axis': {'range': axisrange, 'tickformat':'0%'},
            'bar': {'color': 'black','thickness':0.5},
            'threshold': {'line': {'color': "white", 'width': 4},
                          'thickness': 1.0,'value':0.7},
            'steps': [
                {'range': [0, .3], 'color': 'red',},
                {'range': [.3, .6], 'color': 'yellow'},
                {'range': [.6, 1], 'color': 'green'},
                ],
            }),layout={"height":145,})
    
    sr_gauge1.update_layout(template="plotly_dark",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
          title={'text': text,'y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
                  font=dict(family="sans-serif, monospace",size=9,color="white"),
                                            margin=dict(l=20,r=20,b=5,t=40),)
    sr_gauge1.update_traces(number_font_family = "sans-serif",  number_font_size=26,)    

#============================================================================================================    
# Chart 4 - - Service Request spread by status for the selected weeks
#============================================================================================================    
    
    datasets = json.loads(dataframes)

    sr_spread = pd.read_json(datasets['sr_demand_throughput_by_week'], orient='split')
    sr = pd.read_json(datasets['sr_demand'], orient='split')
    if len(sr) == 0:
        sr_created2 = sr_reassigned2 = sr_reopened2 = sr_escalated2 = value = resolved = 0
    else:
        sr_created2 = sr_spread['Number_x'].sum()   
#        sr_reassigned2 = sr['Reassigned Flag'].sum()
#        sr_reopened2 = sr['Reopened Flag'].sum()
#        sr_escalated2 = sr['Escalated Flag'].sum()
        sr['Match'] = np.where(sr['YearWeekResolved']==sr['YearWeekCreated'],'yes', 'no')
        resolved = len(sr[(sr['Match']=='yes')])
        value = round((resolved/sr_created2),2)

    text = 'Resolution Rate of New Demand: ' + 'week ' + week2 + ' to week ' + week1    
    axisrange = [None, 1]
    sr_gauge2 = go.Figure(go.Indicator(
        mode = 'gauge+number+delta',
        number = {'valueformat': '0%'},
        value = value,
        domain = {'x':[0, 1], 'y':[0, 1]},
        delta = {'reference': .7, 'valueformat': '0%',
                 'increasing': {'color': "green"},'decreasing': {'color': "red"}, 'position':'top', 'relative':False},
        gauge = {
            'axis': {'range': axisrange, 'tickformat':'0%'},
            'bar': {'color': 'black','thickness':0.5},
            'threshold': {'line': {'color': "white", 'width': 4},
                          'thickness': 1.0,'value':0.7},
            'steps': [
                {'range': [0, .3], 'color': 'red',},
                {'range': [.3, .6], 'color': 'yellow'},
                {'range': [.6, 1], 'color': 'green'},
                ],
            }),layout={"height":145,})
      
    sr_gauge2.update_layout(template="plotly_dark",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
          title={'text': text,'y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
                  font=dict(family="sans-serif, monospace",size=9,color="white"),
                                            margin=dict(l=20,r=20,b=5,t=40),)
    sr_gauge2.update_traces(number_font_family = "sans-serif",  number_font_size=26,)    

    
    inci_escalated1 = pd.read_json(datasets['inci_escalated_1week'], orient='split')
    inci_reopened1 = pd.read_json(datasets['inci_reopen_1week'], orient='split')
    inci_reassigned1 = pd.read_json(datasets['inci_reassign_1week'], orient='split')
    sr_escalated1 = pd.read_json(datasets['sr_escalated_1week'], orient='split')
    sr_reopened1 = pd.read_json(datasets['sr_reopen_1week'], orient='split')
    sr_reassigned1 = pd.read_json(datasets['sr_reassign_1week'], orient='split')
    inci_escalated2 = pd.read_json(datasets['inci_escalated'], orient='split')
    inci_reopened2 = pd.read_json(datasets['inci_reopen'], orient='split')
    inci_reassigned2 = pd.read_json(datasets['inci_reassign'], orient='split')
    sr_escalated2 = pd.read_json(datasets['sr_escalated'], orient='split')
    sr_reopened2 = pd.read_json(datasets['sr_reopen'], orient='split')
    sr_reassigned2 = pd.read_json(datasets['sr_reassign'], orient='split')
    inci_escalated1=len(inci_escalated1)
    inci_reopened1=len(inci_reopened1)
    inci_reassigned1=len(inci_reassigned1)
    inci_escalated2=len(inci_escalated2)
    inci_reopened2=len(inci_reopened2)
    inci_reassigned2=len(inci_reassigned2)
    sr_escalated1=len(sr_escalated1)
    sr_reopened1=len(sr_reopened1)
    sr_reassigned1=len(sr_reassigned1)
    sr_escalated2=len(sr_escalated2)
    sr_reopened2=len(sr_reopened2)
    sr_reassigned2=len(sr_reassigned2)

    return incifig, srfig, \
        incident_mttr_gauge1, incident_mttr_gauge2, sr_mttr_gauge1, sr_mttr_gauge2,   \
        incident_gauge1, incident_gauge2, sr_gauge1, sr_gauge2, \
        inci_created1, inci_resolved1, inci_reassigned1, inci_reopened1, inci_escalated1, \
        sr_created1, sr_resolved1, sr_reassigned1, sr_reopened1, sr_escalated1, \
        inci_created2, inci_resolved2, inci_reassigned2, inci_reopened2, inci_escalated2, \
        sr_created2, sr_resolved2, sr_reassigned2, sr_reopened2, sr_escalated2,\
        header1, header2, header3, header4

@app.callback(
    [Output("incident_backlog_trend", "figure"), Output("sr_backlog_trend", "figure"),
      Output("incident_backlog_age", "figure"), Output("sr_backlog_age", "figure"), 
      Output("withibm1", "children"), Output("withwpp1", "children"), Output("total1", "children"), 
      Output("withibm2", "children"), Output("withwpp2", "children"), Output("total2", "children"), 
      Output("header5", "children"), Output("header6", "children"),
      Output("header7", "children"), Output("header8", "children"),
      Output("ageibm1", "children"), Output("agewpp1", "children"), Output("totalage1", "children"), 
      Output("ageibm2", "children"), Output("agewpp2", "children"), Output("totalage2", "children"), 
      ],
      [Input("intermediate-value", "data"), Input("startyearweek","data"), Input("endyearweek","data"),
      Input("report-dropdown","value"),
      Input("url","pathname")],)
def create_backlog_page(dataframes,startyearweek,endyearweek,reporttype,pathname):

    pageid = pathname.split("/")[2]

    if pageid in ['legacy','compare','sla','themes']:
        raise PreventUpdate

    if reporttype == 'Throughput':
        raise PreventUpdate

#================================================================================================================
# Create Header Strings
#================================================================================================================
    year1 = str(endyearweek)[:4]
    week1 = str(endyearweek)[4:]
    header5 = 'Incident Backlog for week ' + week1 + '-' + year1 
    header6 = 'Service Requests Backlog for week ' + week1 + '-' + year1 
    header7 = 'Incident Backlog Age for week ' + week1 + '-' + year1 
    header8 = 'Service Requests Age Backlog for week ' + week1 + '-' + year1 

#================================================================================================================
# Charts for 1st Row
#================================================================================================================
# Chart 1 - Incident Backlog trend
#================================================================================================================
    
    datasets = json.loads(dataframes)
    data = pd.read_json(datasets['incibacklog_1_week'], orient='split')
    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    ibm = data[(data['Backlog With'] == 'With IBM')]
    wpp = data[(data['Backlog With'] == 'With WPP (On Hold)')]
#    total = data[(data['Backlog With'] == 'Total')]
    ibmincidentbacklog1 = len(ibm)
    wppincidentbacklog1 = len(wpp)
    totalincidentbacklog1 = len(ibm) + len(wpp)
    if len(ibm) != 0:
        ibmincidentbacklogage1 = round((ibm['Age'].mean()),2)
    else:
        ibmincidentbacklogage1 = 0
    
    if len(wpp) != 0:      
        wppincidentbacklogage1 = round((wpp['Age'].mean()),2)
    else:
        wppincidentbacklogage1 = 0

    if len(data) != 0:        
        totalincidentbacklogage1 = round((data['Age'].mean()),2)
    else:
        totalincidentbacklogage1 = 0

    data = pd.read_json(datasets['incident_backlog_by_week'], orient='split')
#    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Yearstr'] = data['Yearstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    if len(data) != 0:
        data['YearWeekstr'] = data['Yearstr'].str[2:] + '/' + data['Weekstr']
    else:
        data['YearWeekstr'] = data['Weekstr']
    ibm = data[(data['Backlog With'] == 'With IBM')]
    wpp = data[(data['Backlog With'] == 'With WPP (On Hold)')]
    total = data[(data['Backlog With'] == 'Total')]
#    ibm = pd.merge(ibm,total, on=['Yearstr','Weekstr'], how='right')
#    wpp = pd.merge(wpp,total, on=['Yearstr','Weekstr'], how='right')
    ibm = pd.merge(ibm,total, on=['YearWeekstr'], how='right')
    wpp = pd.merge(wpp,total, on=['YearWeekstr'], how='right')
    incibacklogfig = go.Figure()
    incibacklogfig.add_trace(go.Scatter(x=ibm['YearWeekstr'], y=ibm['Number_x'], name='IBM',))
    incibacklogfig.add_trace(go.Scatter(x=wpp['YearWeekstr'], y=wpp['Number_x'], name='WPP',))
    incibacklogfig.add_trace(go.Scatter(x=total['YearWeekstr'], y=total['Number'], name='Total',))
    incibacklogfig.update_layout(template="plotly_dark",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        title={'text': 'Incidents Backlog','y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
        xaxis_title="Week", 
        font=dict(family="sans-serif, monospace",size=10,color="white"),
        height=145,
        margin=dict(l=10,r=10,b=10,t=10,),
    ),

    incibacklogfig.update_traces(line=dict(shape='spline', smoothing=1.3))   

# #================================================================================================================
# # Chart 2 - Service Request backlog trend
# #================================================================================================================
    
    datasets = json.loads(dataframes)

    data = pd.read_json(datasets['srbacklog_1_week'], orient='split')
#    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Yearstr'] = data['Yearstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    if len(data) != 0:
        data['YearWeekstr'] = data['Yearstr'].str[2:] + '/' + data['Weekstr']
    else:
        data['YearWeekstr'] = data['Weekstr']
    ibm = data[(data['Backlog With'] == 'With IBM')]
    wpp = data[(data['Backlog With'] == 'With WPP (On Hold)')]
#    total = data[(data['Backlog With'] == 'Total')]
    ibmsrbacklog1 = len(ibm)
    wppsrbacklog1 = len(wpp)
    totalsrbacklog1 = len(ibm) + len(wpp)
    ibmsrbacklogage1 = round((ibm['Age'].mean()),2)
    wppsrbacklogage1 = round((wpp['Age'].mean()),2)
    totalsrbacklogage1 = round((data['Age'].mean()),2)

    data = pd.read_json(datasets['sr_backlog_by_week'], orient='split')
    data['Yearstr'] = data['Yearstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    if len(data) != 0:
        data['YearWeekstr'] = data['Yearstr'].str[2:] + '/' + data['Weekstr']
    else:
        data['YearWeekstr'] = data['Weekstr']
#    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    ibm = data[(data['Backlog With'] == 'With IBM')]
    wpp = data[(data['Backlog With'] == 'With WPP (On Hold)')]
    total = data[(data['Backlog With'] == 'Total')]
    ibm = pd.merge(ibm,total, on=['YearWeekstr'], how='right')
    wpp = pd.merge(wpp,total, on=['YearWeekstr'], how='right')

    srbacklogfig = go.Figure()
    srbacklogfig.add_trace(go.Scatter(x=ibm['YearWeekstr'], y=ibm['Number_x'], name='IBM',)),
    srbacklogfig.add_trace(go.Scatter(x=wpp['YearWeekstr'], y=wpp['Number_x'], name='WPP',)),
    srbacklogfig.add_trace(go.Scatter(x=total['YearWeekstr'], y=total['Number'], name='Total',)),

    srbacklogfig.update_layout(template="plotly_dark",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        title={'text': 'Service Requests Backlog','y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
        xaxis_title="Week",
        font=dict(family="sans-serif, monospace",size=10,color="white"),
        height=145,
        margin=dict(l=10,r=10,b=10,t=10,),
    ),
    srbacklogfig.update_traces(line=dict(shape='spline', smoothing=1.3))   
            
#================================================================================================================
# Charts for 2nd Row
#================================================================================================================
# Chart 1 - Incident Backlog Age
#================================================================================================================
    
    datasets = json.loads(dataframes)
    
    data = pd.read_json(datasets['incident_backlogage_by_week'], orient='split')
#    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Yearstr'] = data['Yearstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    if len(data) != 0:
        data['YearWeekstr'] = data['Yearstr'].str[2:] + '/' + data['Weekstr']
    else:
        data['YearWeekstr'] = data['Weekstr']
    data['Age'] = round(data['Age'],2)
    ibm = data[(data['Backlog With'] == 'With IBM')]
    wpp = data[(data['Backlog With'] == 'With WPP (On Hold)')]
    total = data[(data['Backlog With'] == 'Total')]
    ibm = pd.merge(ibm,total, on=['YearWeekstr'], how='right')
    wpp = pd.merge(wpp,total, on=['YearWeekstr'], how='right')
    incibacklogagefig = go.Figure()
    incibacklogagefig.add_trace(go.Scatter(x=ibm['YearWeekstr'], y=ibm['Age_x'], name='IBM')),
    incibacklogagefig.add_trace(go.Scatter(x=wpp['YearWeekstr'], y=wpp['Age_x'], name='WPP')),
    incibacklogagefig.add_trace(go.Scatter(x=total['YearWeekstr'], y=total['Age'], name='Total')),

    incibacklogagefig.update_layout(template="plotly_dark",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        title={'text': 'Incidents Backlog Age','y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
        xaxis_title="Week",
        font=dict(family="sans-serif, monospace",size=10,color="white"),
        height=145,
        margin=dict(l=10,r=10,b=10,t=10,),
    ),

    incibacklogagefig.update_traces(line=dict(shape='spline', smoothing=1.3))   

# #================================================================================================================
# # Chart 2 - Service Request backlog Age
# #================================================================================================================
    
    datasets = json.loads(dataframes)

    data = pd.read_json(datasets['sr_backlogage_by_week'], orient='split')
#    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Yearstr'] = data['Yearstr'].apply(str).apply(lambda x: x.zfill(2))
    data['Weekstr'] = data['Weekstr'].apply(str).apply(lambda x: x.zfill(2))
    if len(data) != 0:
        data['YearWeekstr'] = data['Yearstr'].str[2:] + '/' + data['Weekstr']
    else:
        data['YearWeekstr'] = data['Weekstr']
    data['Age'] = round(data['Age'],2)
    ibm = data[(data['Backlog With'] == 'With IBM')]
    wpp = data[(data['Backlog With'] == 'With WPP (On Hold)')]
    total = data[(data['Backlog With'] == 'Total')]
    ibm = pd.merge(ibm,total, on=['YearWeekstr'], how='right')
    wpp = pd.merge(wpp,total, on=['YearWeekstr'], how='right')
    srbacklogagefig = go.Figure()
    srbacklogagefig.add_trace(go.Scatter(x=ibm['YearWeekstr'], y=ibm['Age_x'], name='IBM')),
    srbacklogagefig.add_trace(go.Scatter(x=wpp['YearWeekstr'], y=wpp['Age_x'], name='WPP')),
    srbacklogagefig.add_trace(go.Scatter(x=total['YearWeekstr'], y=total['Age'], name='Total')),

    srbacklogagefig.update_layout(template="plotly_dark",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        title={'text': 'Service Requests Backlog Age','y':0.93, 'x':0.02, 'xanchor': 'left', 'yanchor': 'top'},
        xaxis_title="Week",
        font=dict(family="sans-serif, monospace",size=10,color="white"),
        height=145,
        margin=dict(l=10,r=10,b=10,t=10,),
    ),
    srbacklogagefig.update_traces(line=dict(shape='spline', smoothing=1.3))   

    return incibacklogfig, srbacklogfig, incibacklogagefig, srbacklogagefig, \
        ibmincidentbacklog1, wppincidentbacklog1, totalincidentbacklog1, ibmsrbacklog1, wppsrbacklog1, totalsrbacklog1,\
        header5, header6,header7,header8,\
        ibmincidentbacklogage1,wppincidentbacklogage1,totalincidentbacklogage1,\
        ibmsrbacklogage1,wppsrbacklogage1,totalsrbacklogage1

@app.callback(
      [Output("incident_age", "data"),Output('incident_age','page_current')],
      [Input("intermediate-value","data"), Input("report-dropdown","value"), 
       Input("incident_radio","value"),
      Input("url","pathname")],)

def display_datatable1(dataframes,reporttype,radio,pathname):

    pageid = pathname.split("/")[2]

    if pageid in ['legacy','compare','sla','themes']:
        raise PreventUpdate

    if reporttype == 'Throughput':
        raise PreventUpdate

    datasets = json.loads(dataframes)
    if radio == 1:
        data = pd.read_json(datasets['incident_pivot'], orient='split')
        incidentage = pd.merge(data,incidentpivot,how='left')
        incidentage.fillna(0,inplace=True)
        incidentage = incidentage[['Backlog', '00-30', '31-60', '61-90',\
                               '91-120', '121-180','181-365', '365+']]
    else:
        data = pd.read_json(datasets['incident_pivot1'], orient='split')
        incidentage = pd.merge(data,incidentpivot,how='left')
        incidentage.fillna(0,inplace=True)
        incidentage = incidentage[['Backlog', '00-30', '31-60', '61-90',\
                               '91-120', '121-180','181-365', '365+']]
    page = 0
    return incidentage.to_dict('records'),page

@app.callback(
      [Output("sr_age", "data"),Output('sr_age','page_current')],
      [Input("intermediate-value","data"), Input("report-dropdown","value"), 
       Input("sr_radio","value"),
      Input("url","pathname")],)
def display_datatable2(dataframes,reporttype, radio,pathname):

    pageid = pathname.split("/")[2]

    if pageid in ['legacy','compare','sla','themes']:
        raise PreventUpdate

    if reporttype == 'Throughput':
        raise PreventUpdate

    datasets = json.loads(dataframes)
    
    if radio == 1:
        data = pd.read_json(datasets['sr_pivot'], orient='split')
        incidentage = pd.merge(data,srpivot,how='left')
        incidentage.fillna(0,inplace=True)
        incidentage = incidentage[['Backlog', '00-30', '31-60', '61-90',\
                               '91-120', '121-180','181-365', '365+']]
    else:
        data = pd.read_json(datasets['sr_pivot1'], orient='split')
        incidentage = pd.merge(data,srpivot,how='left')
        incidentage.fillna(0,inplace=True)
        incidentage = incidentage[['Backlog', '00-30', '31-60', '61-90',\
                               '91-120', '121-180','181-365', '365+']]
    page = 0
    return incidentage.to_dict('records'), page
#=========================================================================================================================
# Legacy Report    
#=========================================================================================================================
@app.callback(
      [Output("demand", "data"), Output('demand','columns'),
       Output("throughput", "data"),Output('throughput','columns'),
       Output("mttr", "data"),Output('mttr','columns'),
       Output("healthcheck", "data"),Output('healthcheck','columns'),
       Output("backlogage", "data"),Output('backlogage','columns'),
       Output("backlog", "data"),Output('backlog','columns'),
       Output("backlogagebucket", "data"),Output('backlogagebucket','columns'),
       Output("wppbacklogage", "data"),Output('wppbacklogage','columns'),Output('wppbacklogage','page_current')],
    [Input("legacyregion-dropdown", "value"),
     Input("year-dropdown","value"),
     Input("week-dropdown","value"),
     Input("resource-dropdown","value"),
     Input("url","pathname"),])
def legacy_report(region,year,endweek,resourcetype,pathname):

    trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if trigger == "year-dropdown":
        raise PreventUpdate()
        
    pageid = pathname.split("/")[2]
    
    if pageid in ['regions','keyapps','compare','sla','themes']:
        raise PreventUpdate
    
#    if type(endweek) is dict:
#        endweek = endweek.get('value')
        
    startyearweek, endyearweek = get_start_end_dates(weeksfile, year, endweek)
    startyearweek1, endyearweek1 = get_start_end_dates(weeksfile, year, endweek,12)

    endweekindex = weeksfile.loc[(weeksfile["Year"] == year) & (weeksfile["Week"] == endweek)].index
    endweekindex = endweekindex[0] + 1
    startweekindex = endweekindex - 4
    week2 = weeksfile.iloc[::-1]
    week2 = week2[startweekindex:endweekindex]
    week2 = week2['Week'].tolist()

    if 'All Regions' in region:
        actualregion = ['APAC','EMEA','Global - EMEA','LATAM','NA.','Global - NA']
    else:
        actualregion = [region]
        
    if 'All' in resourcetype:
        actualtype = ['Local','GD']
    else:
        actualtype = [resourcetype]
    
    heading = []
    for i in week2:
        heading.append('WK ' + str(i))

    columnlist = ['Ticket Type']
    for i in heading:
        columnlist.append(i)

    incident_demand, sr_demand, ser_demand, incident_throughput, sr_throughput, ser_throughput, incident_1_mttr, sr_1_mttr, \
            incident_1_week, sr_1_week = get_throughput_data(pageid,actualregion,actualtype,startyearweek,endyearweek)

    incident_backlog, sr_backlog, incibacklog_1_week, srbacklog_1_week \
            = get_backlog_data(pageid,actualregion,actualtype,startyearweek,endyearweek)

    incident_demand1, sr_demand1, ser_demand1, incident_throughput1, sr_throughput1, ser_throughput1, incident_1_mttr1, sr_1_mttr1,\
            incident_1_week1, sr_1_week1 = get_throughput_data(pageid,actualregion,actualtype,startyearweek1,endyearweek1)

    incident_backlog1, sr_backlog1, incibacklog_1_week1, srbacklog_1_week1 \
            = get_backlog_data(pageid,actualregion,actualtype,startyearweek,endyearweek)
        
    incident_demand_target=int(round(len(incident_demand1)/12,0))
    sr_demand_target=int(round(len(sr_demand1)/12,0))
    ser_demand_target=int(round(len(ser_demand1)/12,0))
    incident_throughput_target=int(round(len(incident_throughput1)/12,0))
    sr_throughput_target=int(round(len(sr_throughput1)/12,0))
    ser_throughput_target=int(round(len(ser_throughput1)/12,0))

    demand_targets = [incident_demand_target, sr_demand_target, ser_demand_target]
    throughput_targets = [incident_throughput_target, sr_throughput_target, ser_throughput_target]

    incident_demand_pivot =  pd.pivot_table(incident_demand, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()
    sr_demand_pivot =  pd.pivot_table(sr_demand, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()
    ser_demand_pivot =  pd.pivot_table(ser_demand, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()

    incident_demand_df = get_ticket_type_details('Incident',incident_demand_pivot,columnlist,type='demand')
    sr_demand_df = get_ticket_type_details('SR',sr_demand_pivot,columnlist,type='demand')
    ser_demand_df = get_ticket_type_details('SER',ser_demand_pivot,columnlist,type='demand')
            
    demand = incident_demand_df.append(sr_demand_df)
    demand = demand.append(ser_demand_df)
    demand['Target'] = demand_targets
    demand['Shift'] = demand[[demand.columns[-2],'Target']].apply(find_shift,axis=1)
    demand.fillna(0,inplace=True)

    incident_throughput_pivot =  pd.pivot_table(incident_throughput, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()
    sr_throughput_pivot =  pd.pivot_table(sr_throughput, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()
    ser_throughput_pivot =  pd.pivot_table(ser_throughput, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()

    incident_throughput_df = get_ticket_type_details('Incident',incident_throughput_pivot,columnlist,type='throughput')
    sr_throughput_df = get_ticket_type_details('SR',sr_throughput_pivot,columnlist,type='throughput')
    ser_throughput_df = get_ticket_type_details('SER',ser_throughput_pivot,columnlist,type='throughput')

    throughput = incident_throughput_df.append(sr_throughput_df)
    throughput = throughput.append(ser_throughput_df)
    throughput['Target']=throughput_targets

    throughput['Shift'] = throughput[[throughput.columns[-2],'Target']].apply(find_shift,axis=1)
    throughput.fillna(0,inplace=True)

    mttr_target = mttr_target_dict[region]
    if resourcetype == 'GD':
        mttr_target = gd_mttr_target_dict[region]
        
    incident_mttr_pivot =  pd.pivot_table(incident_throughput, index=['Ticket Type'], values=['MTTR'],
                     columns=['YearWeek'],
                     aggfunc='mean', fill_value=0).reset_index()
    sr_mttr_pivot =  pd.pivot_table(sr_throughput, index=['Ticket Type'], values=['MTTR'],
                     columns=['YearWeek'],
                     aggfunc='mean', fill_value=0).reset_index()
    ser_mttr_pivot =  pd.pivot_table(ser_throughput, index=['Ticket Type'], values=['MTTR'],
                     columns=['YearWeek'],
                     aggfunc='mean', fill_value=0).reset_index()
    
    incident_mttr_df = get_ticket_type_details('Incident',incident_mttr_pivot,columnlist,type='mttr')
    sr_mttr_df = get_ticket_type_details('SR',sr_mttr_pivot,columnlist,type='mttr')
    ser_mttr_df = get_ticket_type_details('SER',ser_mttr_pivot,columnlist,type='mttr')
    
    mttr = incident_mttr_df.append(sr_mttr_df)
    mttr = mttr.append(ser_mttr_df)
    mttr = mttr.round(1)
    mttr['Target']=mttr_target

    mttr['Shift'] = mttr[[mttr.columns[-2],'Target']].apply(find_shift,type = 'mttr',axis=1)
    mttr.fillna(0,inplace=True)

    inci_escalated,inci_reopen,inci_reassign,inci_escalated_1week,inci_reopen_1week,inci_reassign_1week, sr_escalated,\
            sr_reopen,sr_reassign,sr_escalated_1week,sr_reopen_1week,sr_reassign_1week = get_health_check_data(pageid,actualregion,actualtype,startyearweek,endyearweek)

    escalated_pivot1 =  pd.pivot_table(inci_escalated, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()
    reassign_pivot1 =  pd.pivot_table(inci_reassign, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()
    reopen_pivot1 =  pd.pivot_table(inci_reopen, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()
    escalated_pivot2 =  pd.pivot_table(sr_escalated, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()
    reassign_pivot2 =  pd.pivot_table(sr_reassign, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()
    reopen_pivot2 =  pd.pivot_table(sr_reopen, index=['Ticket Type'], values=['Number'],
                     columns=['YearWeek'],
                     aggfunc=len, fill_value=0).reset_index()

    colnames = []
    for i in range(startyearweek,endyearweek+1):
        colnames.append(i)
        escalated_pivot = pd.DataFrame(columns=colnames)
        reassign_pivot = pd.DataFrame(columns=colnames)
        reopen_pivot = pd.DataFrame(columns=colnames)

    if len(escalated_pivot1) != 0:
        escalated_pivot1.drop('Ticket Type',axis=1,level=0,inplace=True)
        escalated_pivot1.columns=escalated_pivot1.columns.droplevel(0)  
        escalated_pivot = escalated_pivot.append(escalated_pivot1)    
    if len(escalated_pivot2) != 0:
        escalated_pivot2.drop('Ticket Type',axis=1,level=0,inplace=True)
        escalated_pivot2.columns=escalated_pivot2.columns.droplevel(0)  
        escalated_pivot = escalated_pivot.append(escalated_pivot2)   
    if len(escalated_pivot) != 0:
        escalated_pivot = escalated_pivot.sum().to_frame().T    

    if len(reassign_pivot1) != 0:
        reassign_pivot1.drop('Ticket Type',axis=1,level=0,inplace=True)
        reassign_pivot1.columns=reassign_pivot1.columns.droplevel(0)  
        reassign_pivot = reassign_pivot.append(reassign_pivot1)    
    if len(reassign_pivot2) != 0:
        reassign_pivot2.drop('Ticket Type',axis=1,level=0,inplace=True)
        reassign_pivot2.columns=reassign_pivot2.columns.droplevel(0)  
        reassign_pivot = reassign_pivot.append(reassign_pivot2)    
    if len(reassign_pivot) != 0:
        reassign_pivot = reassign_pivot.sum().to_frame().T

    if len(reopen_pivot1) != 0:
        reopen_pivot1.drop('Ticket Type',axis=1,level=0,inplace=True)
        reopen_pivot1.columns=reopen_pivot1.columns.droplevel(0)  
        reopen_pivot = reopen_pivot.append(reopen_pivot1)    
    if len(reopen_pivot2) != 0:
        reopen_pivot2.drop('Ticket Type',axis=1,level=0,inplace=True)
        reopen_pivot2.columns=reopen_pivot2.columns.droplevel(0)  
        reopen_pivot = reopen_pivot.append(reopen_pivot2)  
    if len(reopen_pivot) != 0:
        reopen_pivot = reopen_pivot.sum().to_frame().T
        
    columnlist1 = columnlist.copy()
    columnlist1[0]='Highest Volume (count)' 
    
    escalated_df = get_healthcheck_details('Escalated',escalated_pivot,columnlist1)
    reassign_df = get_healthcheck_details('Reassigned',reassign_pivot,columnlist1)
    reopen_df = get_healthcheck_details('Reopened',reopen_pivot,columnlist1)
    healthcheck_df = escalated_df.append(reassign_df)
    healthcheck_df = healthcheck_df.append(reopen_df)
    healthcheck_df.fillna(0,inplace=True)
    healthcheck_df['Target'] = ''
    healthcheck_df['Shift'] = healthcheck_df[[healthcheck_df.columns[-3],healthcheck_df.columns[-2]]].apply(find_shift,axis=1)
    
    columnlist1 = columnlist.copy()
    columnlist1.insert(1,'Backlog With')
    
    age_target = age_target_dict[region]
    if resourcetype == 'GD':
        age_target = gd_age_target_dict[region]

    incident_age_pivot =  pd.pivot_table(incident_backlog, index=['Ticket Type','Backlog With'], values=['Age'],
                         columns=['YearWeek'],
                         aggfunc='mean', fill_value=0).reset_index()

    incident_age_pivot.columns=incident_age_pivot.columns.droplevel(0)  
    incident_age_pivot.columns.values[0] = 'Ticket Type'
    incident_age_pivot.columns.values[1] = 'Backlog With'
    
    age_pivot = pd.DataFrame(columns=colnames)
    age_pivot.insert(0,column='Ticket Type',value='')
    age_pivot.insert(1,column='Backlog With',value='')
    age_pivot = age_pivot.append(incident_age_pivot)
    
    incident_age_df = get_ticket_details('Incident',age_pivot,columnlist1)
    
    sr_age_pivot =  pd.pivot_table(sr_backlog, index=['Ticket Type','Backlog With'], values=['Age'],
                         columns=['YearWeek'],
                         aggfunc='mean', fill_value=0).reset_index()
    
    sr_age_pivot.columns=sr_age_pivot.columns.droplevel(0)  
    sr_age_pivot.columns.values[0] = 'Ticket Type'
    sr_age_pivot.columns.values[1] = 'Backlog With'
    
    age_pivot = pd.DataFrame(columns=colnames)
    age_pivot.insert(0,column='Ticket Type',value='')
    age_pivot.insert(1,column='Backlog With',value='')
    age_pivot = age_pivot.append(sr_age_pivot)
    
    sr_age_df = get_ticket_details('SR',sr_age_pivot,columnlist1)
    age = incident_age_df.append(sr_age_df)

    age = age.round(0)
    age['Target']=age_target

    age['Shift'] = age[[age.columns[-2],'Target']].apply(find_shift,type = 'age',axis=1)
    age.fillna(0,inplace=True)

    count = 1
    df = []
    for i in age.columns[1:]:

        if count <= 4:
            age[i] = age[i].apply(int).apply(str)
            df.append(age.groupby(['Ticket Type'])[i].apply(' / '.join).reset_index())
        else:
            age[i] = age[i].apply(str)
            df.append(age.groupby(['Ticket Type'])[i].apply(''.join).reset_index())    
        count += 1
    df_age = reduce(lambda  left,right: pd.merge(left,right,on=['Ticket Type'],
                                            how='outer'), df)

    backlog_target = backlog_target_dict[region]
    if resourcetype == 'GD':
        backlog_target = gd_backlog_target_dict[region]

    incident_backlog_pivot =  pd.pivot_table(incident_backlog, index=['Ticket Type','Backlog With'], values=['Number'],
                         columns=['YearWeek'],
                         aggfunc='count', fill_value=0).reset_index()
    
    incident_backlog_pivot.columns=incident_backlog_pivot.columns.droplevel(0)  
    incident_backlog_pivot.columns.values[0] = 'Ticket Type'
    incident_backlog_pivot.columns.values[1] = 'Backlog With'
    
    backlog_pivot = pd.DataFrame(columns=colnames)
    backlog_pivot.insert(0,column='Ticket Type',value='')
    backlog_pivot.insert(1,column='Backlog With',value='')
    backlog_pivot = backlog_pivot.append(incident_backlog_pivot)
    
    incident_backlog_df = get_ticket_details('Incident',backlog_pivot,columnlist1)
      
    sr_backlog_pivot =  pd.pivot_table(sr_backlog, index=['Ticket Type','Backlog With'], values=['Number'],
                         columns=['YearWeek'],
                         aggfunc='count', fill_value=0).reset_index()

    sr_backlog_pivot.columns=sr_backlog_pivot.columns.droplevel(0)  
    sr_backlog_pivot.columns.values[0] = 'Ticket Type'
    sr_backlog_pivot.columns.values[1] = 'Backlog With'
    
    backlog_pivot = pd.DataFrame(columns=colnames)
    backlog_pivot.insert(0,column='Ticket Type',value='')
    backlog_pivot.insert(1,column='Backlog With',value='')
    backlog_pivot = backlog_pivot.append(sr_backlog_pivot)
    
    sr_backlog_df = get_ticket_details('SR',backlog_pivot,columnlist1)

    backlog = incident_backlog_df.append(sr_backlog_df)

    backlog = backlog.round(0)
    backlog['Target']=backlog_target
    backlog.fillna(0,inplace=True)
    
    backlog['Shift'] = backlog[[backlog.columns[-2],'Target']].apply(find_shift,type = 'age',axis=1)

    count = 1
    df = []
    for i in backlog.columns[1:]:

        if count <= 4:
            backlog[i] = backlog[i].apply(int).apply(str)
            df.append(backlog.groupby(['Ticket Type'])[i].apply(' || '.join).reset_index())
        else:
            backlog[i] = backlog[i].apply(str)
            df.append(backlog.groupby(['Ticket Type'])[i].apply(''.join).reset_index())    
        count += 1
    df_backlog = reduce(lambda  left,right: pd.merge(left,right,on=['Ticket Type'],
                                            how='outer'), df)
    
    
    incident_bucket_pivot = pd.pivot_table(incibacklog_1_week,index=['Ticket Type','Backlog With'], values=['Number'],
                     columns=['Age Bucket'],
                     aggfunc=len, fill_value=0).reset_index()
    sr_bucket_pivot = pd.pivot_table(srbacklog_1_week,index=['Ticket Type','Backlog With'], values=['Number'],
                     columns=['Age Bucket'],
                     aggfunc=len, fill_value=0).reset_index()

    backlog_status = [['Incident','With IBM'],
                      ['Incident','With WPP (On Hold)'],
                      ['SR','With IBM'],
                      ['SR','With WPP (On Hold)']]

    incident_bucket_df = get_ticket_bucket('Incident',incident_bucket_pivot)
    for idx, val in enumerate(backlog_status[0:2]):
        record_exists = ((incident_bucket_df['Ticket Type'] == val[0]) & (incident_bucket_df['Backlog With'] == val[1])).any()
        if record_exists == False:
            row = [val[0],val[1],0,0,0,0,0,0,0]
            incident_bucket_df.loc[len(incident_bucket_df)] = row

    sr_bucket_df = get_ticket_bucket('SR',sr_bucket_pivot)
    for idx, val in enumerate(backlog_status[2:]):
        record_exists = ((sr_bucket_df['Ticket Type'] == val[0]) & (sr_bucket_df['Backlog With'] == val[1])).any()
        if record_exists == False:
            row = [val[0],val[1],0,0,0,0,0,0,0]
            sr_bucket_df.loc[len(sr_bucket_df)] = row

    bucket = incident_bucket_df.append(sr_bucket_df)
    bucket.sort_values(['Ticket Type','Backlog With'], inplace = True)

    df = []
    for i in bucket.columns[2:]:
        bucket[i] = bucket[i].apply(int).apply(str)
        df.append(bucket.groupby(['Ticket Type'])[i].apply(' / '.join).reset_index())
    df_bucket = reduce(lambda  left,right: pd.merge(left,right,on=['Ticket Type'],
                                            how='outer'), df)

    incident_reason_pivot = pd.pivot_table(incibacklog_1_week,index=['Ticket Type','Reason'], values=['Number'],
                     columns=['Age Bucket'],
                     aggfunc=len, fill_value=0).reset_index()
    sr_reason_pivot = pd.pivot_table(srbacklog_1_week,index=['Ticket Type','Reason'], values=['Number'],
                     columns=['Age Bucket'],
                     aggfunc=len, fill_value=0).reset_index()
    
    incident_reason_df = get_ticket_bucket('Incident',incident_reason_pivot)
    incident_reason_df.drop(['Ticket Type'], inplace= True,axis = 1)
    
    sr_reason_df = get_ticket_bucket('Incident',sr_reason_pivot)
    sr_reason_df.drop(['Ticket Type'], inplace= True,axis = 1)
    
    df_reason = incident_reason_df.append(sr_reason_df)
    
    df_reason = df_reason.groupby('Backlog With').sum().reset_index()
    df_reason.rename(columns={'Backlog With':'Reason'},inplace=True)
    if len(df_reason) == 0:
#        df_reason.drop(['Ticket Type'], inplace= True,axis = 1)
        df_reason.loc[len(df_reason)] = ['Nothing on Hold','0','0','0','0','0','0','0']

    return demand.to_dict('records'),\
        [{"name": i, "id": i} for i in demand.columns],\
        throughput.to_dict('records'),\
        [{"name": i, "id": i} for i in throughput.columns],\
        mttr.to_dict('records'),\
        [{"name": i, "id": i} for i in mttr.columns],\
        healthcheck_df.to_dict('records'),\
        [{"name": i, "id": i} for i in healthcheck_df.columns],\
        df_age.to_dict('records'),\
        [{"name": i, "id": i} for i in df_age.columns], \
        df_backlog.to_dict('records'),\
        [{"name": i, "id": i} for i in df_backlog.columns], \
        df_bucket.to_dict('records'),\
        [{"name": i, "id": i} for i in df_bucket.columns],\
        df_reason.to_dict('records'),\
        [{"name": i, "id": i} for i in df_reason.columns], 0

@app.callback(
    Output('container', 'children'),
    [Input('add-chart', 'n_clicks')],
    [State('container', 'children')]
)
def display_graphs(n_clicks, div_children):
    new_child = html.Div(
        style={'width': '50%', 'display': 'inline-block', 'outline': 'thin lightgrey solid', 'padding': 10},
#        style={'width': '48%', 'display': 'inline-block', 'outline': 'thin lightgrey solid', 'margin-left': '1.0%','margin-right': '.5%','margin-top':'10px'},
        children=[
            
            dbc.Row([
            
            html.Div([dcc.RadioItems(
                id={
                    'type': 'dynamic-choice',
                    'index': n_clicks
                },inputStyle={"margin-right": "15px","margin-left": "20px",},
                options=[{'label': 'Bar Chart', 'value': 'bar'},
                         {'label': 'Line Chart', 'value': 'line'},
                         {'label': 'Sunburst Chart', 'value': 'pie'}],
                value='bar',
            ),],style={'margin-top':'-10px'}, className = 'dbc_dark',),
            ]),

            dbc.Row([
                        
            html.Div([dbc.Label("Region",color="primary")],
                 style = {'padding-top':'1%','padding-left':'1.6%','font-weight':'bold'}),

            html.Div([dcc.Dropdown(
                id={'type': 'dynamic-dpn-rgn','index': n_clicks},
                options=[{'label': i, 'value': i} for i in regions],
                multi=True,optionHeight=25,
                value = 'All Regions'),],
                style={'padding-top':'0.1%','padding-left':'5%', 'width':'50%','fontSize':14,},className = 'dbc_dark'),   

            html.Div([dbc.Label("Compare",color="primary")],
                 style = {'padding-top':'1%','padding-left':'1.6%','font-weight':'bold'}),
            
            html.Div([dcc.Dropdown(
                id={'type': 'dynamic-dpn-cmp','index': n_clicks},
                options=[{'label': i, 'value': i} for i in report_type],
                multi=False,clearable=False,optionHeight=25,
                value = 'Demand'),],
                style={'padding-top':'0.1%','padding-left':'0.8%','width':'30%','fontSize':14,},className = 'dbc_dark'),

            ],style={'margin-top':'-10px'}, className = 'dbc_dark',),

            dbc.Row([

            html.Div([dbc.Label("Ticket Type",color="primary")],
                 style = {'padding-top':'1%','padding-left':'1.6%','font-weight':'bold'}),

            html.Div([dcc.Dropdown(
                id={'type': 'dynamic-dpn-tkt','index': n_clicks},
                options=[{'label': i, 'value': i} for i in ticket_type1],
                multi=True,optionHeight=25,
                value = 'All'),],
                style={'padding-top':'0.1%','padding-left':'1.2%','width':'46.4%','fontSize':14,},className = 'dbc_dark'),    
           
            html.Div([dbc.Label("Team",color="primary")],
                  style = {'padding-top':'1%','padding-left':'1.8%','font-weight':'bold'}),

            html.Div([dcc.Dropdown(
                id={'type': 'dynamic-dpn-team','index': n_clicks},
                options=[{'label': i, 'value': i} for i in team_type],
                multi=False,clearable=False,optionHeight=25,
                value = 'All'),],
                style={'padding-top':'0.1%','padding-left':'3.2%','width':'32.5%','fontSize':14,},className = 'dbc_dark'),
            
            ],),
                   
            dcc.Loading(dcc.Graph(
                id={
                    'type': 'dynamic-graph',
                    'index': n_clicks
                },
                figure={},config= {"displayModeBar": False, "showTips": False,'displaylogo': False}
            ),),
            
        ]
    )
    div_children.append(new_child)
    return div_children

#================================================================================================================
# Callback to get the weeks for the selected Year
#================================================================================================================
@app.callback(
    [Output({'type': 'dynamic-dpn-tkt', 'index': MATCH}, 'options'),
    Output({'type': 'dynamic-dpn-tkt', 'index': MATCH}, 'multi'),
    Output({'type': 'dynamic-dpn-tkt', 'index': MATCH}, 'clearable'),],
     [Input(component_id={'type': 'dynamic-dpn-cmp', 'index': MATCH}, component_property='value'),
     Input({'type': 'dynamic-choice', 'index': MATCH}, 'value')],
    prevent_initial_call=True)
def backlog_callback(compare,chart_choice):
    if chart_choice == 'line' and compare in ['Backlog','Backlog Age']:
        return [{'label': i, 'value': i} for i in ticket_type2],False,False 
    else:
        return [{'label': i, 'value': i} for i in ticket_type1],True,True

#================================================================================================================
# Associated callback to get the weeks for the selected Year
#================================================================================================================
@app.callback(
    [Output({'type': 'dynamic-dpn-tkt', 'index': MATCH}, 'value'),],
    Input({'type': 'dynamic-dpn-tkt', 'index': MATCH}, 'options'),    prevent_initial_call=True)
def backlog_option_callback(available_options):
    return [available_options[0].get('value')]

@app.callback(
    Output({'type': 'dynamic-graph', 'index': MATCH}, 'figure'),
    [Input(component_id={'type': 'dynamic-dpn-rgn', 'index': MATCH}, component_property='value'),
     Input(component_id={'type': 'dynamic-dpn-cmp', 'index': MATCH}, component_property='value'),
     Input(component_id={'type': 'dynamic-dpn-tkt', 'index': MATCH}, component_property='value'),
     Input(component_id={'type': 'dynamic-dpn-team', 'index': MATCH}, component_property='value'),
     Input({'type': 'dynamic-choice', 'index': MATCH}, 'value')]
)
def update_graph(region, compare, ticket, team, chart_choice):

    if not region: 
        raise PreventUpdate
    if not ticket:
        raise PreventUpdate
    
    if type(ticket) is dict:
        ticket = [ticket.get('value')]
    if type(ticket) is str:
        ticket = [ticket]
        
    if 'All Regions' in region:
        actualregion = ['APAC','EMEA','Global - EMEA','LATAM','NA.','Global - NA']
    else:
        actualregion = region
    if 'All' in team:
        actualteam = ['Local','GD']
    else:
        actualteam = [team]
        
    if 'All' in ticket:
        actualticket = ['Incident','SR','SER']
    else:
        actualticket = ticket

    if compare in (['Demand','Throughput','MTTR']):
        if compare in (['Throughput','MTTR']):
            status = 'Resolved'
        else:
            status = 'Created'
        data = get_incident_data(actualregion, actualticket, actualteam, status)
    else:
        data = get_backlog_data1(actualregion, actualticket, actualteam)
    
    if chart_choice == 'bar':

        if compare == 'MTTR' and status == 'Resolved':
            throughput_by_month = data.groupby(['Ticket Type','Yearstr'])['MTTR'].mean().round(2).reset_index()
            throughput_by_month.rename(columns={'Yearstr':'Year'}, inplace=True)
            fig = px.bar(throughput_by_month, x='Ticket Type', y='MTTR', barmode='group',color='Year', text = 'MTTR',
                         title = 'MTTR Comparison',hover_data={'Ticket Type':False,},
                         color_discrete_sequence=px.colors.qualitative.Dark2,)
        elif compare == 'Demand' or compare == 'Throughput':
            ticket_by_month = data.groupby(['Ticket Type','Yearstr'])['Number'].count().reset_index()
            ticket_by_month.rename(columns={'Yearstr':'Year'}, inplace=True)
            fig = px.bar(ticket_by_month, x='Ticket Type', y='Number', barmode='group',color='Year', text='Number',
                         title = compare + ' Comparison',hover_data={'Ticket Type':False,},
                         color_discrete_sequence=px.colors.qualitative.Dark2,)
        elif compare == 'Backlog':
            week = data['Weekstr'].iloc[-1]
            data = data[(data['Weekstr'] == week)]
            backlog_by_month = data.groupby(['Ticket Type','Yearstr','Backlog With'])['Number'].count().reset_index()
            backlog_by_month.rename(columns={'Yearstr':'Year'}, inplace=True)
            fig = px.bar(backlog_by_month, x='Ticket Type', y='Number', barmode='group',color='Year',text='Number',
                         title ='Backlog Comparison',facet_col = 'Backlog With',
                         facet_col_spacing =.03,hover_data={'Ticket Type':False,'Backlog With':False},
                         color_discrete_sequence=px.colors.qualitative.Dark2,)
        elif compare == 'Backlog Age':
            week = data['Weekstr'].iloc[-1]
            data = data[(data['Weekstr'] == week)]
            backlog_by_month = data.groupby(['Ticket Type','Yearstr','Backlog With'])['Age'].mean().reset_index().round(0)
            backlog_by_month.rename(columns={'Yearstr':'Year'}, inplace=True)
            fig = px.bar(backlog_by_month, x='Ticket Type', y='Age', barmode='group',color='Year',text='Age',
                         title ='Backlog Age Comparison',
                         facet_col = 'Backlog With',hover_data={'Ticket Type':False,'Backlog With':False},
                         color_discrete_sequence=px.colors.qualitative.Dark2,)
            
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig.update_layout(template="plotly_dark", legend_title_text='',
        legend=dict(orientation="h",yanchor="bottom",y=1.3,xanchor="right",x=1),
        height=230,
        margin=dict(l=10,r=10,b=10,t=10,),)


    if chart_choice == 'line':

        if compare == 'MTTR' and status == 'Resolved':
            throughput_by_month = data.groupby(['Ticket Type','Yearstr','Weekstr'])['MTTR'].mean().reset_index().round(2)
            throughput_by_month.rename(columns={'Yearstr':'Year','Weekstr':'Week'}, inplace=True)
            fig = px.line(throughput_by_month, x='Week', y='MTTR',color='Year',facet_col = 'Ticket Type',\
                          title = compare + ' Comparison', facet_col_spacing =.04,hover_data={'Ticket Type':False,},
                          color_discrete_sequence=px.colors.qualitative.Dark2,)
        elif compare == 'Demand' or compare == 'Throughput':
            ticket_by_month = data.groupby(['Ticket Type','Yearstr','Weekstr'])['Number'].count().reset_index()
            ticket_by_month.rename(columns={'Yearstr':'Year','Weekstr':'Week'}, inplace=True)
            fig = px.line(ticket_by_month, x='Week', y='Number',color='Year',facet_col = 'Ticket Type',\
                          title = compare + ' Comparison', facet_col_spacing =.04,hover_data={'Ticket Type':False,},
                          color_discrete_sequence=px.colors.qualitative.Dark2,)
        elif compare == 'Backlog':
            backlog_by_month = data.groupby(['Backlog With','Ticket Type','Yearstr','Weekstr'])['Number'].count().reset_index()
            backlog_by_month.sort_values(['Backlog With','Ticket Type','Yearstr','Weekstr'], ascending=[False,True,True,True], inplace=True)
            backlog_by_month.rename(columns={'Yearstr':'Year','Weekstr':'Week'}, inplace=True)
            fig = px.line(backlog_by_month, x='Week', y='Number',color='Year',facet_col = 'Backlog With',\
                          title = compare + ' Comparison', facet_col_spacing =.03,hover_data={'Backlog With':False,},
                          color_discrete_sequence=px.colors.qualitative.Dark2,)
        elif compare == 'Backlog Age':
            backlog_by_month = data.groupby(['Backlog With','Ticket Type','Yearstr','Weekstr'])['Age'].mean().reset_index().round(0)
            backlog_by_month.sort_values(['Backlog With','Ticket Type','Yearstr','Weekstr'], ascending=[False,True,True,True], inplace=True)
            backlog_by_month.rename(columns={'Yearstr':'Year','Weekstr':'Week'}, inplace=True)
            fig = px.line(backlog_by_month, x='Week', y='Age' ,color='Year',facet_col = 'Backlog With',\
                         title ='Backlog Age Comparison',facet_col_spacing =.03,hover_data={'Backlog With':False,},
                         color_discrete_sequence=px.colors.qualitative.Dark2,)

        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig.update_xaxes(showline=True,  linecolor='white', mirror=True)
        fig.update_yaxes(showline=True,  linecolor='white', mirror=True)
        fig.update_traces(line=dict(shape='spline', smoothing=1.3))  
        fig.update_layout(template="plotly_dark", legend_title_text='',
        legend=dict(orientation="h",yanchor="bottom",y=1.3,xanchor="right",x=1),
        height=230,
        margin=dict(l=10,r=10,b=10,t=10,),)


    if chart_choice == 'pie':

        if compare == 'MTTR' and status == 'Resolved':
            throughput_sunburst = data.groupby(['Ticket Type','Yearstr'])['MTTR'].mean().reset_index().round(2)
            throughput_sunburst.rename(columns={'Yearstr':'Year'}, inplace=True)
            fig =px.sunburst(throughput_sunburst,
                    path = ['Year','Ticket Type',],color='Ticket Type',\
                    values='MTTR', color_discrete_sequence=px.colors.qualitative.Dark2, maxdepth=-1,\
                    title = 'MTTR Comparison', hover_name='Ticket Type',hover_data={'Ticket Type':False,'Year':False,},)
            fig.update_traces(textinfo='label + value',insidetextorientation='radial')
        elif compare == 'Demand' or compare == 'Throughput':
            tickets_by_week = data.groupby(['Ticket Type','Yearstr'])['Number'].count().reset_index()
            tickets_by_week.rename(columns={'Yearstr':'Year'}, inplace=True)
            fig =px.sunburst(tickets_by_week,
                    path = ['Year','Ticket Type',],color='Ticket Type',\
                    values='Number', color_discrete_sequence=px.colors.qualitative.Dark2, maxdepth=-1,\
                    title = compare + ' Comparison', hover_name='Ticket Type',hover_data={'Ticket Type':False,'Year':False,},)
            fig.update_traces(textinfo='label + percent parent',insidetextorientation='radial')
        elif compare == 'Backlog':
            week = data['Weekstr'].iloc[-1]
            data = data[(data['Weekstr'] == week)]
            backlog_sunburst= data.groupby(['Backlog With','Ticket Type','Yearstr'])['Number'].count().reset_index()
            backlog_sunburst['Backlog With'] = np.where(backlog_sunburst['Backlog With'] == "With WPP (On Hold)", "With WPP", "With IBM")
            backlog_sunburst.rename(columns={'Yearstr':'Year'}, inplace=True)
            fig =px.sunburst(backlog_sunburst,
                    path = ['Year','Ticket Type','Backlog With',],color='Ticket Type',\
                    values='Number', color_discrete_sequence=px.colors.qualitative.Dark2, maxdepth=-1, \
                    title ='Backlog Comparison',hover_name='Year',hover_data={'Year':False,},)
            fig.update_traces(textinfo='label + percent parent',insidetextorientation='radial')
        elif compare == 'Backlog Age':
            week = data['Weekstr'].iloc[-1]
            data = data[(data['Weekstr'] == week)]
            backlog_sunburst = data.groupby(['Backlog With','Ticket Type','Yearstr'])['Age'].mean().reset_index().round(0)
            backlog_sunburst['Backlog With'] = np.where(backlog_sunburst['Backlog With'] == "With WPP (On Hold)", "With WPP", "With IBM")
            backlog_sunburst.rename(columns={'Yearstr':'Year',}, inplace=True)
            fig = px.sunburst(backlog_sunburst,
                    path = ['Year','Ticket Type','Backlog With',],color='Ticket Type', \
                    values='Age', color_discrete_sequence=px.colors.qualitative.Dark2, maxdepth=-1, \
                    title ='Backlog Age Comparison', hover_name='Year',hover_data={'Year':False,},)
            fig.update_traces(textinfo='label + value',insidetextorientation='radial')

        fig.update_layout(template="plotly_dark", legend_title_text='',
        height=230,
        margin=dict(l=10,r=10,b=2,t=5,),
        title={'y':0.5,'x':0.02,'xanchor': 'left','yanchor': 'middle'})
    return fig