from flask import Flask
import dash
from dash import dcc, ctx, html, Input, Output, State, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import dash_daq as daq
import plotly.graph_objects as go
import pandas as pd
import os
import time
import math
import base64
import io
import zipfile
import tempfile
import numpy as np
import dash_auth
import copy

default_colors = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#7f7f7f']
name2color = {'Blue':'#1f77b4', 'Orange':'#ff7f0e', 'Green':'#2ca02c', 'Red':'#d62728', 'Purple':'#9467bd', 'Brown':'#8c564b', 'Pink':'#e377c2', 'Gray':'#7f7f7f'}

def Set_colorlist(default_colors, measList):
    n = math.floor(measList // 10)
    for i in range (n):
        default_colors.extend(default_colors)
    return default_colors

def find_min_max(figure):
    x_max = 0.00000000001
    y_max = float('-inf')
    x_min = float('inf')
    y_min = float('inf')
    for fig in figure['data']:
        if fig['meta']['Type'] == 'Line' and fig['visible'] == True or fig['meta']['Type'] == 'Limit' and fig['visible'] == True:
            if max(fig['x'])>x_max:
                x_max = max(fig['x'])
            if max(fig['y'])>y_max:
                y_max = max(fig['y'])
            if min(fig['x'])<x_min:
                x_min = min(fig['x'])
            if min(fig['y'])<y_min:
                y_min = min(fig['y'])
    return x_max,y_max,x_min,y_min

def add_marker(clickData, figure, markers, log):
    add_marker = True
    if 'annotations' not in figure['layout']:
        figure['layout']['annotations'] = []
    name = figure['data'][clickData['points'][0]['curveNumber']]['name']
    x_point = clickData['points'][0]['x']
    y_point = clickData['points'][0]['y']
    if log == 'log':
        x_point_log = math.log(x_point, 10)
    else:
        x_point_log = x_point
    for i in range (len(markers)):
        if x_point == markers[i]['x'] and y_point == markers[i]['y']:
            for j in range(len(figure['data'])):
                if figure['data'][j]['name'] == markers[i]['name']:
                    figure['data'].pop(j)
                    break
            for j in range(len(figure['layout']['annotations'])):
                if figure['layout']['annotations'][j]['name'] == markers[i]['name']:
                    figure['layout']['annotations'].pop(j)
                    break
            markers.pop(i)
            add_marker = False
            break
    if add_marker == False:
        index = 1
        for i in range (len(figure['layout']['annotations'])):
            if figure['layout']['annotations'][i]['name'].split(' ')[0] == 'Marker':
                figure['layout']['annotations'][i]['text'] = figure['layout']['annotations'][i]['text'].replace(figure['layout']['annotations'][i]['text'].split('<br>')[0], '<b> Marker ' + str(index))
                figure['layout']['annotations'][i]['name'] = 'Marker ' + str(index)
                markers[index-1]['name'] = 'Marker ' + str(index)
                index += 1
        index = 1
        for i in range (len(figure['data'])):
            if figure['data'][i]['name'].split(' ')[0] == 'Marker':
                figure['data'][i]['name'] = 'Marker ' + str(index)
                index += 1
    if add_marker is True:
        meta = {'Name': 'Marker ' + str(len(markers) + 1), 'Type': 'Marker'}
        trace = dict(name='Marker ' + str(len(markers) + 1), x=[x_point], y=[y_point], mode='markers',
                     marker=dict(color='red', size=10), showlegend=False, hoverinfo="none", meta=meta)
        annotation = dict(name='Marker ' + str(len(markers) + 1), x=x_point_log, y=y_point, xref="x", yref="y",
                          text=f"<b> {'Marker ' + str(len(markers) + 1)}:<br> {name.split('#')[0]} <br> Frequency (MHz):</b> {x_point:.2f} <b> <br> Level (dBµV/m):</b> {y_point:.2f}",
                          xanchor='left', yanchor='top', showarrow=False, ax=0,
                          bordercolor="#c7c7c7",
                          bgcolor='red',
                          font=dict(color="#ffffff"), visible=True, align='left', meta=meta, captureevents=True,
                          editable=True, )
        figure['data'].append(trace)
        figure['layout']['annotations'].append(annotation)
        markers.append({'line_index': clickData['points'][0]['curveNumber'], 'name': 'Marker ' + str(len(markers) + 1),
                        'x': clickData['points'][0]['x'], 'y': clickData['points'][0]['y'], 'chart_name': name,
                        'trace': trace, 'annotation': annotation})
    return figure, markers

emission_radiated_horizontal_layout = {'height': '600px',
               'hovermode': 'closest',
               'legend': {'bordercolor': 'gray',
                          'borderwidth': 0.5,
                          'orientation': 'h',
                          'x': 0.5,
                          'xanchor': 'center',
                          'y': -0.15},
               'margin': {'b': 50, 'l': 50, 'r': 30, 't': 25},
               'plot_bgcolor': 'white',
               'template': '...',
               'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Horizontal Polarization'},
               'xaxis': {'gridcolor': 'lightgrey',
                         'hoverformat': ('<b> {meta[0]}<br> Frequency (MHz):</b> {x:.2f} <b> <br> Level (dBµV/m):</b> {y:.2f}'),
                         'linecolor': 'black',
                         'mirror': True,
                         'range': [],
                         'showline': True,
                         'tickfont': {'size': 12, 'weight': 'bold'},
                         'ticks': 'outside',
                         'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Frequency (MHz)'},
                         'type': 'log'},
               'yaxis': {'gridcolor': 'lightgrey',
                         'linecolor': 'black',
                         'mirror': True,
                         'range': 'auto',
                         'showline': True,
                         'tickfont': {'size': 12, 'weight': 'bold'},
                         'ticks': 'outside',
                         'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Level (dBµV/m)'}}}

emission_radiated_vertical_layout = {'height': '600px',
               'hovermode': 'closest',
               'legend': {'bordercolor': 'gray',
                          'borderwidth': 0.5,
                          'orientation': 'h',
                          'x': 0.5,
                          'xanchor': 'center',
                          'y': -0.15},
               'margin': {'b': 50, 'l': 50, 'r': 30, 't': 25},
               'plot_bgcolor': 'white',
               'template': '...',
               'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Vertical Polarization'},
               'xaxis': {'gridcolor': 'lightgrey',
                         'hoverformat': ('<b> {meta[0]}<br> Frequency (MHz):</b> {x:.2f} <b> <br> Level (dBµV/m):</b> {y:.2f}'),
                         'linecolor': 'black',
                         'mirror': True,
                         'range': [],
                         'showline': True,
                         'tickfont': {'size': 12, 'weight': 'bold'},
                         'ticks': 'outside',
                         'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Frequency (MHz)'},
                         'type': 'log'},
               'yaxis': {'gridcolor': 'lightgrey',
                         'linecolor': 'black',
                         'mirror': True,
                         'range': 'auto',
                         'showline': True,
                         'tickfont': {'size': 12, 'weight': 'bold'},
                         'ticks': 'outside',
                         'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Level (dBµV/m)'}}}

emission_radiated_horizontal_vertical_layout = {'height': '600px',
               'hovermode': 'closest',
               'legend': {'bordercolor': 'gray',
                          'borderwidth': 0.5,
                          'orientation': 'h',
                          'x': 0.5,
                          'xanchor': 'center',
                          'y': -0.15},
               'margin': {'b': 50, 'l': 50, 'r': 30, 't': 25},
               'plot_bgcolor': 'white',
               'template': '...',
               'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Horizontal/Vertical Polarization'},
               'xaxis': {'gridcolor': 'lightgrey',
                         'hoverformat': ('<b> {meta[0]}<br> Frequency (MHz):</b> {x:.2f} <b> <br> Level (dBµV/m):</b> {y:.2f}'),
                         'linecolor': 'black',
                         'mirror': True,
                         'range': [],
                         'showline': True,
                         'tickfont': {'size': 12, 'weight': 'bold'},
                         'ticks': 'outside',
                         'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Frequency (MHz)'},
                         'type': 'log'},
               'yaxis': {'gridcolor': 'lightgrey',
                         'linecolor': 'black',
                         'mirror': True,
                         'range': 'auto',
                         'showline': True,
                         'tickfont': {'size': 12, 'weight': 'bold'},
                         'ticks': 'outside',
                         'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Level (dBµV/m)'}}}

emission_conducted_phase_layout = {'height': '600px',
               'hovermode': 'closest',
               'legend': {'bordercolor': 'gray',
                          'borderwidth': 0.5,
                          'orientation': 'h',
                          'x': 0.5,
                          'xanchor': 'center',
                          'y': -0.15},
               'margin': {'b': 50, 'l': 50, 'r': 30, 't': 25},
               'plot_bgcolor': 'white',
               'template': '...',
               'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Phase 1 Polarization'},
               'xaxis': {'gridcolor': 'lightgrey',
                         'hoverformat': ('<b> {meta[0]}<br> Frequency (MHz):</b> {x:.2f} <b> <br> Level (dBµV/m):</b> {y:.2f}'),
                         'linecolor': 'black',
                         'mirror': True,
                         'range': [],
                         'showline': True,
                         'tickfont': {'size': 12, 'weight': 'bold'},
                         'ticks': 'outside',
                         'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Frequency (MHz)'},
                         'type': 'log'},
               'yaxis': {'gridcolor': 'lightgrey',
                         'linecolor': 'black',
                         'mirror': True,
                         'range': 'auto',
                         'showline': True,
                         'tickfont': {'size': 12, 'weight': 'bold'},
                         'ticks': 'outside',
                         'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Level (dBµV/m)'}}}

emission_conducted_wire_layout = {'height': '600px',
               'hovermode': 'closest',
               'legend': {'bordercolor': 'gray',
                          'borderwidth': 0.5,
                          'orientation': 'h',
                          'x': 0.5,
                          'xanchor': 'center',
                          'y': -0.15},
               'margin': {'b': 50, 'l': 50, 'r': 30, 't': 25},
               'plot_bgcolor': 'white',
               'template': '...',
               'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Wire + Polarization'},
               'xaxis': {'gridcolor': 'lightgrey',
                         'hoverformat': ('<b> {meta[0]}<br> Frequency (MHz):</b> {x:.2f} <b> <br> Level (dBµV/m):</b> {y:.2f}'),
                         'linecolor': 'black',
                         'mirror': True,
                         'range': [],
                         'showline': True,
                         'tickfont': {'size': 12, 'weight': 'bold'},
                         'ticks': 'outside',
                         'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Frequency (MHz)'},
                         'type': 'log'},
               'yaxis': {'gridcolor': 'lightgrey',
                         'linecolor': 'black',
                         'mirror': True,
                         'range': 'auto',
                         'showline': True,
                         'tickfont': {'size': 12, 'weight': 'bold'},
                         'ticks': 'outside',
                         'title': {'font': {'size': 16, 'weight': 'bold'}, 'text': 'Level (dBµV/m)'}},
                'shape': [],
                'annotations': [],
                }

sidebar_style = {
    "position": "fixed",
    "top": 0,
    "right": 0,
    "bottom": 0,
    "width": "300px",
    "padding": "20px",
    "background-color": "#F4F6F7",  # Light gray background for the sidebar
    "color": "#34495E",  # Dark text color for readability
    "box-shadow": "0px 0px 10px rgba(0, 0, 0, 0.1)",  # Subtle shadow for depth
    "transform": "translateX(100%)",  # Hidden by default
    "transition": "transform 0.3s ease",
    "z-index": "1000",  # To make sure sidebar is on top
    # "overflow-y": "scroll",
    # "overflow-x": "fixed"
}

# Button styles
button_style = {
    "width": "100%",  # Make the button take full width of sidebar
    "padding": "15px",
    "margin-bottom": "10px",  # Space between buttons
    "background-color": "#1F3A68",  # MPS-style blue background
    "color": "#FFF",  # White text
    "border": "none",
    "cursor": "pointer",
    "font-size": "18px",
    "font-family": "Arial, sans-serif",  # Clean sans-serif font
    "border-radius": "5px",  # Rounded corners for the buttons
    "transition": "background-color 0.3s ease",  # Button hover effect
}

submenu_style = {
    "display": "none",  # Submenu hidden initially
    "padding": "10px",
    "background-color": "#E9EFF1",  # Light blue background for submenu
    "color": "#34495E",  # Dark text for submenu
    "transition": "transform 0.3s ease",
    "transform": "translateY(-100%)",  # Hidden by default, off-screen
}

submenu_active_style = {
    "display": "block",  # Show submenu
    "transform": "translateY(0)",  # Slide it down
}

# Content area style
content_style = {
    "margin-right": "0px",  # No margin initially, so sidebar slides over
    "padding": "20px",
    "background-color": "#FFFFFF",  # White background for main content
    "color": "#34495E",  # Dark text color for readability
}

columnDefs_suspectTable = [{"checkboxSelection": {'function': "params.data.disabled == 'False'"}, 'showDisabledCheckboxes': True, "headerCheckboxSelection": True, 'width': 50, 'pinned': 'left'},
    {"headerName":"Suspects: Test Name","field": "Test Name", 'flex':1},
    {"headerName":"Subrange","field": "Subrange", 'width': 120},
    {"headerName":"Source","field": "Source", 'width': 150},
    {"headerName":"Frequency (MHz)","field": "Frequency", 'width': 180},
    {"headerName":"Peak (dB µV/m)","field": "Peak", 'width': 170},
    {"headerName":"Lim.Q-Peak (dB µV/m)","field": "LimQ_Peak", 'width': 220},
    {"headerName":"Peak-Lim.Q-Peak (dB)","field": "Peak_LimQ_Peak", 'width': 220},
    {"headerName":"Height (m)","field": "Height", 'width': 130},
    {"headerName":"Angle (°)","field": "Angle", 'width': 130},
    {"headerName":"Polarization","field": "Polarization", 'width': 150},
    {"headerName":"Correction (dB)","field": "Correction", 'width': 170},
    {"field": "disabled", "hide": True}]

columnDefs_finalsTable = [{"checkboxSelection": {'function': "params.data.disabled == 'False'"}, 'showDisabledCheckboxes': True, "headerCheckboxSelection": True, 'width': 50, 'pinned': 'left'},
    {"headerName":"Finals: Test Name","field": "Test Name", 'width': 450},
    {"headerName":"Subrange","field": "Subrange", 'flex':1},
    {"headerName":"Source","field": "Source", 'flex':1},
    {"headerName":"Frequency (MHz)","field": "Frequency", 'flex':1},
    {"headerName":"QPeak Level (dBµV/m)","field": "QPeak Level", 'flex':1},
    {"headerName":"QPeak Margin (dBµV/m)","field": "QPeak Margin", 'flex':1},
    {"headerName":"Height (m)","field": "Height", 'flex':1},
    {"headerName":"Angle (°)","field": "Angle", 'flex':1},
    {"headerName":"Polarization","field": "Polarization", 'flex':1},
    {"headerName":"RBW (kHz)","field": "RBW", 'flex':1},
    {"headerName":"Meas.Time (s)","field": "Meas.Time", 'flex':1},
    {"field": "disabled", "hide": True}]

detector_to_color_gradient = {
    'Peak': {'9 kHz': 'rgb(106,174,214)', '120 kHz': 'rgb(46,126,188)', '200 kHz': 'rgb(46,126,188)', '1 MHz': 'rgb(8,74,145)'},
    'Q-Peak': {'9 kHz': 'rgb(251,105,74)', '120 kHz': 'rgb(217,37,35)', '200 kHz': 'rgb(217,37,35)', '1 MHz': 'rgb(152,12,19)'},
    'Avg': {'9 kHz': 'rgb(115,196,118)', '120 kHz': 'rgb(47,151,78)', '200 kHz': 'rgb(47,151,78)', '1 MHz': 'rgb(0,100,40)'}
}

Gradient = {'Blue' : 'Blues', 'Orange' : 'Oranges', 'Green' : 'Greens', 'Red' : 'Reds', 'Purple' : 'Purples', 'Brown' : 'copper', 'Pink' : 'RdPu', 'Gray' : 'Grays'}

limits_btn=html.Div([html.Label('Display Limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'}),dbc.Stack([dcc.Checklist(id='industrial-limit',options=[{'label':' Industrial','value':True}],value=[True],inline=True,labelStyle={'fontWeight':'bold','margin-right':'10px'},className='radio-item-spacing'),dcc.Checklist(id='domestic-limit',options=[{'label':' Domestic','value':True}],value=[True],inline=True,labelStyle={'fontWeight':'bold','margin-right':'10px'},className='radio-item-spacing')],direction="horizontal",gap=1)],style={'margin-bottom':'10px','border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px'})

suspects_btn = html.Div([dbc.Row(dbc.Stack([html.Label('Display Suspects',style={'fontWeight':'bold','margin-right':'10px'}),daq.BooleanSwitch(id='display-suspects',on=True)],direction="horizontal",gap=0.5,style={'padding':'5px 20px'}))], style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px'})

finals_btn = html.Div([dbc.Row(dbc.Stack([html.Label('Display Finals',style={'fontWeight':'bold','margin-right':'10px'}),daq.BooleanSwitch(id='display-finals',on=True)],direction="horizontal",gap=0.5,style={'padding':'5px 20px'}))], style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px'})

label = html.Label('Horizontal/Vertical',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})
log_btn = html.Div([html.Label('X axis Scale',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'}),dcc.RadioItems(id='xaxis_emission_radiated_horizontal_vertical',options=[{'label':' Logarithmic','value':'log'},{'label':' Linear','value':'linear'}],value='log',inline=True,labelStyle={'fontWeight':'bold','margin-right':'10px','margin-bottom':'10px'},className='radio-item-spacing')])
input_x_min_max = html.Div([dbc.Row(html.Label('X axis limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})),
                            dbc.Row([dbc.Col([dbc.Stack([html.Label('Min',style={'fontWeight':'bold'}),dcc.Input(id='input_x_min_radiated_horizontal_vertical',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)]),dbc.Col([dbc.Stack([html.Label('Max',style={'fontWeight':'bold'}),dcc.Input(id='input_x_max_radiated_horizontal_vertical',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)])],className="g-0",style={'margin-bottom':'10px'})])
input_y_min_max = html.Div([dbc.Row(html.Label('Y axis limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})),
                            dbc.Row([dbc.Col([dbc.Stack([html.Label('Min',style={'fontWeight':'bold'}),dcc.Input(id='input_y_min_radiated_horizontal_vertical',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)]),dbc.Col([dbc.Stack([html.Label('Max',style={'fontWeight':'bold'}),dcc.Input(id='input_y_max_radiated_horizontal_vertical',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)])],className="g-0")])

Cursor_menu=html.Div([
    dbc.Row(dbc.Stack([html.Label('Activate cursors',style={'fontWeight':'bold','margin-right':'10px'}),daq.BooleanSwitch(id='activate_cursor_radiated_horizontal_vertical',on=False)],direction="horizontal",gap=0.5,style={'padding':'5px 20px','margin-bottom':'5px'})),
    dbc.Row([dcc.Dropdown(id='cursor_list_radiated_horizontal_vertical',options=[],placeholder="Select a line",style={'width':'230px','display': 'none','margin-bottom':'5px'})]),
    dbc.Row(html.Label(f'ΔFrequency (MHz) = - \n ΔLevel (dBμV/m) = -',id='cursor_output_radiated_horizontal_vertical',style={"white-space": "pre",'fontWeight':'bold','display': 'none'}))],style={'padding':'10px'})

columnDefs_limits = [{"checkboxSelection": {'function': "params.data.disabled == 'False'"}, 'showDisabledCheckboxes': True, "headerCheckboxSelection": True, 'width': 50, 'pinned': 'left'},
    {"headerName":"Name","field": "Name", 'flex':1},
    {"field": "disabled", "hide": True}]

columnDefs_line = [{"headerName":"Name","field": "Name", 'width': 500},
    {"headerName":"Color","field": "Color",'width':'90px','editable':True, 'flex':1,'cellEditor':'agSelectCellEditor', 'cellEditorParams': {'values':['Blue', 'Orange', 'Green', 'Red', 'Purple', 'Brown', 'Pink', 'Gray']}},
    {"headerName":"Width","field": "Width",'width':'90px','editable':True, 'flex':1,'cellEditor':{"function": "NumberInput"},"cellEditorParams" : {"placeholder": "Enter a number"}},
    {"headerName":"Type","field": "Type",'width':'90px', 'editable':True, 'flex':1,'cellEditor':'agSelectCellEditor', 'cellEditorParams': {'values':['solid','dash','dot']}}]

limits_table = dag.AgGrid(
        id="limits_table_radiated_horizontal_vertical",
        rowData=[],
        columnDefs=columnDefs_limits,
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True,
                         "isRowSelectable": {'function': "params.data.disabled == 'False'"}},
        defaultColDef={'resizable': True},
        style={'center': True, 'fontSize': '12px', 'height': '300px', 'width': '100%'})

line_table = dag.AgGrid(
        id="line_table_radiated_horizontal_vertical",
        rowData=[],
        columnDefs=columnDefs_line,
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True},
        defaultColDef={'resizable': True},
        style={'center': True, 'fontSize': '12px', 'height': '300px', 'width': '100%'})

line_table_Div_radiated_horizontal_vertical = html.Div([dbc.Stack([limits_table, line_table],gap=2)],id='line_table_container_radiated_horizontal_vertical',style={'width':800,'display':'none','position':'fixed','top':'20%','right':'305px','bg-color':'rgba(255,255,255,0.95)','padding':'10px 10px','boxShadow':'0px 4px 8px rgba(0,0,0,0.1)','zIndex':'1002','borderRadius':'8px','overflow':'auto'})

line_table_btn = html.Button('Show Line Display Parameters',id='line_table_btn_radiated_horizontal_vertical',n_clicks=0,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"})

line_menu = html.Div([dbc.Row((line_table_btn),justify='center')],style={'padding':'10px'})

param_emission_radiated_horizontal_vertical=html.Div([label, log_btn, input_x_min_max, input_y_min_max, Cursor_menu, line_menu], id='Div_axes_param_radiated_horizontal_vertical',style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px', 'display':'none'})

marker_btn_radiated = html.Button('Clear Markers',id='clear_markers_btn_radiated',n_clicks=0,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"})
marker_menu_radiated = html.Div([dbc.Row(dbc.Stack([html.Label('Activate Markers',style={'fontWeight':'bold','margin-right':'10px'}),daq.BooleanSwitch(id='activate-marker_radiated',on=False)],direction="horizontal",gap=0.5,style={'padding':'5px 20px','margin-bottom':'5px'}),justify='center'),dbc.Row([marker_btn_radiated],justify='center')],style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px'})

columnDefs=[{"headerName":"", "checkboxSelection": True, "headerCheckboxSelection": True, 'width': 50, 'pinned': 'left'},
    {"headerName":"Test Name","field": "Test name", 'flex':1, "filter": "agTextColumnFilter", "filterParams": {"filterOptions": ["contains", "notContains", "Equals", "Does not equals"], "debounceMs": 500}},
    {"headerName":"Test Type","field": "Test Type", 'width': 230, "filter": "agTextColumnFilter", "filterParams": {"filterOptions": ["contains", "notContains", "Equals", "Does not equals"], "debounceMs": 500}},
    {"headerName":"Limit","field": "Limit", 'flex':1, "filter": "agTextColumnFilter", "filterParams": {"filterOptions": ["contains", "notContains", "Equals", "Does not equals"], "debounceMs": 500}},
    {"headerName":"Polarization","field": "Polarization", 'width': 140, "filter": "agTextColumnFilter", "filterParams": {"filterOptions": ["contains", "notContains", "Equals", "Does not equals"], "debounceMs": 500}},
    {"headerName":"Detector","field": "Detector", 'width': 120, "filter": "agTextColumnFilter", "filterParams": {"filterOptions": ["contains", "notContains", "Equals", "Does not equals"], "debounceMs": 500}},
    {"headerName":"Frequency Range","field": "Frequency Range", 'width': 180, "filter": "agTextColumnFilter", "filterParams": {"filterOptions": ["contains", "notContains", "Equals", "Does not equals"], "debounceMs": 500}},
    {"headerName":"Bandwidth","field": "Bandwidth", 'width': 130, "filter": "agTextColumnFilter", "filterParams": {"filterOptions": ["contains", "notContains", "Equals", "Does not equals"], "debounceMs": 500}},
    {"headerName":"Modification","field": "Modification", 'flex':1, "filter": "agTextColumnFilter", "filterParams": {"filterOptions": ["contains", "notContains", "Equals", "Does not equals"], "debounceMs": 500}},
    {"headerName":"Date","field": "Date", 'width': 200, "filter": "agDateColumnFilter", "filterParams": {"filterOptions": ["Equals", "Before", "After", "Between"]}},
    {"headerName":"Test Pass","field": "Test_Pass", 'width': 130, "filter": "agTextColumnFilter", "filterParams": {"filterOptions": ["contains", "notContains", "Equals", "Does not equals"], "debounceMs": 500}},
    {"field": "Data","hide": True}]

getRowStyle = {
    "styleConditions": [
        {
            "condition": "params.data.Test_Pass == 'Failed'",
            "style": {"backgroundColor": "red", "color": "white", "font-weight":"bold"},
        },
{
            "condition": "params.data.Test_Pass == 'Inconclusive'",
            "style": {"backgroundColor": "orange", "color": "white", "font-weight":"bold"},
        },
        {
            "condition": "params.data.Test_Pass == 'Passed'",
            "style": {"backgroundColor": "green", "color": "white", "font-weight":"bold"},
        },
    ]
}

check = html.Img(src="https://cdn-icons-png.flaticon.com/512/5610/5610944.png",style={'height': '20px','width':'20px'})
cross = html.Img(src="https://cdn-icons-png.flaticon.com/512/10100/10100000.png",style={'height': '20px','width':'20px'})

logo=html.Img(src="https://community.element14.com/e14/assets/main/mfg-group-assets/monolithicpowersystemsLogo.png",style={'height': '50px','margin-right':'10px'})
title=html.H1("Emission EMC Test",style={'font-size':50,'font-weight':'bold'})
location=html.H1("Ettenheim EMC Lab",style={'font-size':50,'font-weight':'bold','text-align':'right'})

project=dbc.Stack([
                html.Div(dcc.Dropdown(placeholder="Select a project",id='Project-list',options=[],style={'width':'500px'})),
                html.Div(dcc.Upload(id='load-project',children=[html.Button('Load a project',id='Load',n_clicks=0,style={'width':'150px','borderRadius':'5px'})])),
                html.Div(html.Button('Remove a project',id='Remove-project',n_clicks=0,style={'width':'150px','borderRadius':'5px'})),
                html.Div(dbc.Button(id='loading-screen', children=['No loaded project'],disabled=True, style = {'width':'270px', 'borderRadius':'5px', 'border':'none','align-items':'center', 'font-weight':'bold', 'backgroundColor':'#119DFF'})),
            ],direction="horizontal",gap=3,style={'margin-left':'30px','margin-bottom':'20px','align-items':'center'})

table=dcc.Loading([dag.AgGrid(
        id="Test-table",
        rowData=[],
        columnDefs=columnDefs,
        defaultColDef={'resizable': True},
        getRowStyle=getRowStyle,
        style={'width':'100%','center':True},
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True,"domLayout": "autoHeight"})],
        overlay_style={"visibility":"visible", "filter": "blur(2px)"},type="circle")

emission_conducted_phase_graph = dcc.Loading([dcc.Graph(id='emission_conducted_phase',
                                           figure={ 'data':[], 'layout': emission_conducted_phase_layout},
                                           config={'toImageButtonOptions': {'filename':'Emission_EMC_chart_screenshot'}, 'responsive':True, 'displaylogo':False, 'editable':True, 'edits': {'annotationTail':False, 'annotationText':True, 'axisTitleText':False, 'colorbarPosition':False, 'colorbarTitleText':False, 'legendPosition':False, 'legendText':False, 'shapePosition':False, 'titleText':False}, 'modeBarButtonsToRemove': ['zoom', 'pan','zoomin','zoomout','autoscale','resetscale','lasso2d', 'select2d']},
                                           style={'height': '600px','width':'100%','fontWeight':'bold', 'display':'none'})],
                                id='loading_emission_conducted_phase', overlay_style={"visibility":"unvisible", "filter": "blur(2px)"},type="circle")

label_conducted_phase = html.Label('Phase 1',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})
log_btn_conducted_phase = html.Div([html.Label('X axis Scale',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'}),dcc.RadioItems(id='xaxis_emission_conducted_phase',options=[{'label':' Logarithmic','value':'log'},{'label':' Linear','value':'linear'}],value='log',inline=True,labelStyle={'fontWeight':'bold','margin-right':'10px','margin-bottom':'10px'},className='radio-item-spacing')])
input_x_min_max_conducted_phase = html.Div([dbc.Row(html.Label('X axis limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})),
                            dbc.Row([dbc.Col([dbc.Stack([html.Label('Min',style={'fontWeight':'bold'}),dcc.Input(id='input_x_min_conducted_phase',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)]),dbc.Col([dbc.Stack([html.Label('Max',style={'fontWeight':'bold'}),dcc.Input(id='input_x_max_conducted_phase',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)])],className="g-0",style={'margin-bottom':'10px'})])
input_y_min_max_conducted_phase = html.Div([dbc.Row(html.Label('Y axis limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})),
                            dbc.Row([dbc.Col([dbc.Stack([html.Label('Min',style={'fontWeight':'bold'}),dcc.Input(id='input_y_min_conducted_phase',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)]),dbc.Col([dbc.Stack([html.Label('Max',style={'fontWeight':'bold'}),dcc.Input(id='input_y_max_conducted_phase',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)])],className="g-0")])

Cursor_menu_conducted_phase = html.Div([
    dbc.Row(dbc.Stack([html.Label('Activate cursors',style={'fontWeight':'bold','margin-right':'10px'}),daq.BooleanSwitch(id='activate_cursor_conducted_phase',on=False)],direction="horizontal",gap=0.5,style={'padding':'5px 20px','margin-bottom':'5px'})),
    dbc.Row([dcc.Dropdown(id='cursor_list_conducted_phase',options=[],placeholder="Select a line",style={'width':'240px','display': 'none','margin-bottom':'5px'})]),
    dbc.Row(html.Label(f'ΔFrequency (MHz) = - \n ΔLevel (dBμV/m) = -',id='cursor_output_conducted_phase',style={"white-space": "pre",'fontWeight':'bold','display': 'none'}))],style={'padding':'10px'})

line_table_btn_conducted_phase = html.Button('Show Line Display Parameters',id='line_table_btn_conducted_phase',n_clicks=0,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"})

line_menu_conducted_phase = html.Div([dbc.Row((line_table_btn_conducted_phase),justify='center')],style={'padding':'10px'})

param_emission_conducted_phase = html.Div([label_conducted_phase, log_btn_conducted_phase, input_x_min_max_conducted_phase ,input_y_min_max_conducted_phase , Cursor_menu_conducted_phase, line_menu_conducted_phase], id='Div_axes_param_conducted_phase',style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px', 'display':'none'})

limits_table_conducted_phase = dag.AgGrid(
        id="limits_table_conducted_phase",
        rowData=[],
        columnDefs=columnDefs_limits,
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True,
                         "isRowSelectable": {'function': "params.data.disabled == 'False'"}},
        defaultColDef={'resizable': True},
        style={'center': True, 'fontSize': '12px', 'height': '300px', 'width': '100%'})

line_table_conducted_phase = dag.AgGrid(
        id="line_table_conducted_phase",
        rowData=[],
        columnDefs=columnDefs_line,
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True},
        defaultColDef={'resizable': True},
        style={'center': True, 'fontSize': '12px', 'height': '300px', 'width': '100%'})

line_table_Div_conducted_phase = html.Div([dbc.Stack([limits_table_conducted_phase, line_table_conducted_phase],gap=2)],id='line_table_container_conducted_phase',style={'width':800,'display':'none','position':'fixed','top':'20%','right':'305px','bg-color':'rgba(255,255,255,0.95)','padding':'10px 10px','boxShadow':'0px 4px 8px rgba(0,0,0,0.1)','zIndex':'1002','borderRadius':'8px','overflow':'auto'})

emission_conducted_wire_graph = dcc.Loading([dcc.Graph(id='emission_conducted_wire',
                                           figure={ 'data':[], 'layout': emission_conducted_wire_layout},
                                           config={'toImageButtonOptions': {'filename':'Emission_EMC_chart_screenshot'}, 'responsive':True, 'displaylogo':False, 'editable':True, 'edits': {'annotationTail':False, 'annotationText':True, 'axisTitleText':False, 'colorbarPosition':False, 'colorbarTitleText':False, 'legendPosition':False, 'legendText':False, 'shapePosition':False, 'titleText':False}, 'modeBarButtonsToRemove': ['zoom', 'pan','zoomin','zoomout','autoscale','resetscale','lasso2d', 'select2d']},
                                           style={'height': '600px','width':'100%','fontWeight':'bold', 'display':'none'})],
                                id='loading_emission_conducted_wire', overlay_style={"visibility":"unvisible", "filter": "blur(2px)"},type="circle")

label_conducted_wire = html.Label('Wire +',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})
log_btn_conducted_wire = html.Div([html.Label('X axis Scale',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'}),dcc.RadioItems(id='xaxis_emission_conducted_wire',options=[{'label':' Logarithmic','value':'log'},{'label':' Linear','value':'linear'}],value='log',inline=True,labelStyle={'fontWeight':'bold','margin-right':'10px','margin-bottom':'10px'},className='radio-item-spacing')])
input_x_min_max_conducted_wire = html.Div([dbc.Row(html.Label('X axis limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})),
                            dbc.Row([dbc.Col([dbc.Stack([html.Label('Min',style={'fontWeight':'bold'}),dcc.Input(id='input_x_min_conducted_wire',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)]),dbc.Col([dbc.Stack([html.Label('Max',style={'fontWeight':'bold'}),dcc.Input(id='input_x_max_conducted_wire',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)])],className="g-0",style={'margin-bottom':'10px'})])
input_y_min_max_conducted_wire = html.Div([dbc.Row(html.Label('Y axis limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})),
                            dbc.Row([dbc.Col([dbc.Stack([html.Label('Min',style={'fontWeight':'bold'}),dcc.Input(id='input_y_min_conducted_wire',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)]),dbc.Col([dbc.Stack([html.Label('Max',style={'fontWeight':'bold'}),dcc.Input(id='input_y_max_conducted_wire',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)])],className="g-0")])

Cursor_menu_conducted_wire = html.Div([
    dbc.Row(dbc.Stack([html.Label('Activate cursors',style={'fontWeight':'bold','margin-right':'10px'}),daq.BooleanSwitch(id='activate_cursor_conducted_wire',on=False)],direction="horizontal",gap=0.5,style={'padding':'5px 20px','margin-bottom':'5px'})),
    dbc.Row([dcc.Dropdown(id='cursor_list_conducted_wire',options=[],placeholder="Select a line",style={'width':'240px','display': 'none','margin-bottom':'5px'})]),
    dbc.Row(html.Label(f'ΔFrequency (MHz) = - \n ΔLevel (dBμV/m) = -',id='cursor_output_conducted_wire',style={"white-space": "pre",'fontWeight':'bold','display': 'none'}))],style={'padding':'10px'})

line_table_btn_conducted_wire = html.Button('Show Line Display Parameters',id='line_table_btn_conducted_wire',n_clicks=0,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"})

line_menu_conducted_wire = html.Div([dbc.Row(html.Label('Line Display Parameters',style={'margin-bottom':'5px','margin-left':'25px','fontWeight':'bold'})),dbc.Row((line_table_btn_conducted_wire),justify='center')],style={'padding':'10px'})

param_emission_conducted_wire = html.Div([label_conducted_wire, log_btn_conducted_wire, input_x_min_max_conducted_wire ,input_y_min_max_conducted_wire , Cursor_menu_conducted_wire, line_menu_conducted_wire], id='Div_axes_param_conducted_wire',style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px', 'display':'none'})

limits_table_conducted_wire = dag.AgGrid(
        id="limits_table_conducted_wire",
        rowData=[],
        columnDefs=columnDefs_limits,
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True,
                         "isRowSelectable": {'function': "params.data.disabled == 'False'"}},
        defaultColDef={'resizable': True},
        style={'center': True, 'fontSize': '12px', 'height': '300px', 'width': '100%'})

line_table_conducted_wire = dag.AgGrid(
        id="line_table_conducted_wire",
        rowData=[],
        columnDefs=columnDefs_line,
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True},
        defaultColDef={'resizable': True},
        style={'center': True, 'fontSize': '12px', 'height': '300px', 'width': '100%'})

line_table_Div_conducted_wire = html.Div([dbc.Stack([limits_table_conducted_wire, line_table_conducted_wire],gap=2)],id='line_table_container_conducted_wire',style={'width':800,'display':'none','position':'fixed','top':'20%','right':'305px','bg-color':'rgba(255,255,255,0.95)','padding':'10px 10px','boxShadow':'0px 4px 8px rgba(0,0,0,0.1)','zIndex':'1002','borderRadius':'8px','overflow':'auto'})

suspectTable_conducted = dag.AgGrid(
        id = "suspectsTable-conducted",
        rowData = [],
        columnDefs = columnDefs_suspectTable,
        defaultColDef={'resizable': True, "filter": "agTextColumnFilter"},
        style={'width': '100%', 'center': True, 'display': 'block'},
        dashGridOptions={"rowSelection": "multiple", "suppressRowClickSelection": True, "animateRows": False,
                         "domLayout": "autoHeight", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "suppressMoveWhenRowDragging": True,
                         "isRowSelectable": {'function': "params.data.disabled == 'False'"}})

finalsTable_conducted = dag.AgGrid(
        id = "finalsTable-conducted",
        rowData = [],
        columnDefs = columnDefs_finalsTable,
        defaultColDef={'resizable': True, "filter": "agTextColumnFilter"},
        style={'width': '100%', 'center': True, 'display': 'block'},
        dashGridOptions={"rowSelection": "multiple", "suppressRowClickSelection": True, "animateRows": False,
                         "domLayout": "autoHeight", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "suppressMoveWhenRowDragging": True,
                         "isRowSelectable": {'function': "params.data.disabled == 'False'"}})

minimize_suspectTable_conducted_btn = html.Div(id='minimize_suspectTable_conducted_container', children=[dbc.Row(html.Button('Hide Suspects Table',id='minimize_suspectTable_conducted_btn',n_clicks=1,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"}),justify='center')],style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px'})

minimize_finalTable_conducted_btn = html.Div(id='minimize_finalTable_conducted_container', children=[dbc.Row(html.Button('Hide Finals Table',id='minimize_finalTable_conducted_btn',n_clicks=1,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"}),justify='center')],style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px'})

marker_btn_conducted = html.Button('Clear Markers',id='clear_markers_btn_conducted',n_clicks=0,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"})

marker_menu_conducted = html.Div([dbc.Row(dbc.Stack([html.Label('Activate Markers',style={'fontWeight':'bold','margin-right':'10px'}),daq.BooleanSwitch(id='activate-marker_conducted',on=False)],direction="horizontal",gap=0.5,style={'padding':'5px 20px','margin-bottom':'5px'}),justify='center'),dbc.Row([marker_btn_conducted],justify='center')],style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px'})

emission_conducted_table=html.Div(dbc.Stack([emission_conducted_phase_graph, emission_conducted_wire_graph, suspectTable_conducted, finalsTable_conducted],gap = 3),style={'height': '100%','width':'100%','border':'1px solid #d6d6d6','border-top':'none','margin-top':'-20px','padding':'10px'})

emission_radiated_horizontal_graph = dcc.Loading([dcc.Graph(id='emission_radiated_horizontal',
                                           figure={ 'data':[], 'layout': emission_radiated_horizontal_layout},
                                           config={'toImageButtonOptions': {'filename':'Emission_EMC_chart_screenshot'}, 'responsive':True, 'displaylogo':False, 'editable':True, 'edits': {'annotationTail':False, 'annotationText':True, 'axisTitleText':False, 'colorbarPosition':False, 'colorbarTitleText':False, 'legendPosition':False, 'legendText':False, 'shapePosition':False, 'titleText':False}, 'modeBarButtonsToRemove': ['zoom', 'pan','zoomin','zoomout','autoscale','resetscale','lasso2d', 'select2d']},
                                           style={'height': '600px','width':'100%','fontWeight':'bold', 'display':'none'})],
                                id='loading_emission_radiated_horizontal', overlay_style={"visibility":"unvisible", "filter": "blur(2px)"},type="circle")

label_radiated_horizontal = html.Label('Horizontal',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})
log_btn_radiated_horizontal = html.Div([html.Label('X axis Scale',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'}),dcc.RadioItems(id='xaxis_emission_radiated_horizontal',options=[{'label':' Logarithmic','value':'log'},{'label':' Linear','value':'linear'}],value='log',inline=True,labelStyle={'fontWeight':'bold','margin-right':'10px','margin-bottom':'10px'},className='radio-item-spacing')])
input_x_min_max_radiated_horizontal = html.Div([dbc.Row(html.Label('X axis limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})),
                            dbc.Row([dbc.Col([dbc.Stack([html.Label('Min',style={'fontWeight':'bold'}),dcc.Input(id='input_x_min_radiated_horizontal',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)]),dbc.Col([dbc.Stack([html.Label('Max',style={'fontWeight':'bold'}),dcc.Input(id='input_x_max_radiated_horizontal',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)])],className="g-0",style={'margin-bottom':'10px'})])
input_y_min_max_radiated_horizontal = html.Div([dbc.Row(html.Label('Y axis limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})),
                            dbc.Row([dbc.Col([dbc.Stack([html.Label('Min',style={'fontWeight':'bold'}),dcc.Input(id='input_y_min_radiated_horizontal',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)]),dbc.Col([dbc.Stack([html.Label('Max',style={'fontWeight':'bold'}),dcc.Input(id='input_y_max_radiated_horizontal',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)])],className="g-0")])

Cursor_menu_radiated_horizontal = html.Div([
    dbc.Row(dbc.Stack([html.Label('Activate cursors',style={'fontWeight':'bold','margin-right':'10px'}),daq.BooleanSwitch(id='activate_cursor_radiated_horizontal',on=False)],direction="horizontal",gap=0.5,style={'padding':'5px 20px','margin-bottom':'5px'})),
    dbc.Row([dcc.Dropdown(id='cursor_list_radiated_horizontal',options=[],placeholder="Select a line",style={'width':'240px','display': 'none','margin-bottom':'5px'})]),
    dbc.Row(html.Label(f'ΔFrequency (MHz) = - \n ΔLevel (dBμV/m) = -',id='cursor_output_radiated_horizontal',style={"white-space": "pre",'fontWeight':'bold','display': 'none'}))],style={'padding':'10px'})

line_table_btn_radiated_horizontal = html.Button('Show Line Display Parameters',id='line_table_btn_radiated_horizontal',n_clicks=0,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"})

line_menu_radiated_horizontal = html.Div([dbc.Row((line_table_btn_radiated_horizontal),justify='center')],style={'padding':'10px'})

param_emission_radiated_horizontal = html.Div([label_radiated_horizontal, log_btn_radiated_horizontal, input_x_min_max_radiated_horizontal ,input_y_min_max_radiated_horizontal , Cursor_menu_radiated_horizontal, line_menu_radiated_horizontal], id='Div_axes_param_radiated_horizontal',style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px', 'display':'none'})

limits_table_radiated_horizontal = dag.AgGrid(
        id="limits_table_radiated_horizontal",
        rowData=[],
        columnDefs=columnDefs_limits,
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True,
                         "isRowSelectable": {'function': "params.data.disabled == 'False'"}},
        defaultColDef={'resizable': True},
        style={'center': True, 'fontSize': '12px', 'height': '300px', 'width': '100%'})

line_table_radiated_horizontal = dag.AgGrid(
        id="line_table_radiated_horizontal",
        rowData=[],
        columnDefs=columnDefs_line,
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True},
        defaultColDef={'resizable': True},
        style={'center': True, 'fontSize': '12px', 'height': '300px', 'width': '100%'})

line_table_Div_radiated_horizontal = html.Div([dbc.Stack([limits_table_radiated_horizontal, line_table_radiated_horizontal],gap=2)],id='line_table_container_radiated_horizontal',style={'width':800,'display':'none','position':'fixed','top':'20%','right':'305px','bg-color':'rgba(255,255,255,0.95)','padding':'10px 10px','boxShadow':'0px 4px 8px rgba(0,0,0,0.1)','zIndex':'1002','borderRadius':'8px','overflow':'auto'})

emission_radiated_vertical_graph = dcc.Loading([dcc.Graph(id='emission_radiated_vertical',
                                           figure={ 'data':[], 'layout': emission_radiated_vertical_layout},
                                           config={'toImageButtonOptions': {'filename':'Emission_EMC_chart_screenshot'}, 'responsive':True, 'displaylogo':False, 'editable':True, 'edits': {'annotationTail':False, 'annotationText':True, 'axisTitleText':False, 'colorbarPosition':False, 'colorbarTitleText':False, 'legendPosition':False, 'legendText':False, 'shapePosition':False, 'titleText':False}, 'modeBarButtonsToRemove': ['zoom', 'pan','zoomin','zoomout','autoscale','resetscale','lasso2d', 'select2d']},
                                           style={'height': '600px','width':'100%','fontWeight':'bold', 'display':'none'})],
                                id='loading_emission_radiated_vertical', overlay_style={"visibility":"unvisible", "filter": "blur(2px)"},type="circle")

label_radiated_vertical = html.Label('Vertical',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})
log_btn_radiated_vertical = html.Div([html.Label('X axis Scale',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'}),dcc.RadioItems(id='xaxis_emission_radiated_vertical',options=[{'label':' Logarithmic','value':'log'},{'label':' Linear','value':'linear'}],value='log',inline=True,labelStyle={'fontWeight':'bold','margin-right':'10px','margin-bottom':'10px'},className='radio-item-spacing')])
input_x_min_max_radiated_vertical = html.Div([dbc.Row(html.Label('X axis limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})),
                            dbc.Row([dbc.Col([dbc.Stack([html.Label('Min',style={'fontWeight':'bold'}),dcc.Input(id='input_x_min_radiated_vertical',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)]),dbc.Col([dbc.Stack([html.Label('Max',style={'fontWeight':'bold'}),dcc.Input(id='input_x_max_radiated_vertical',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)])],className="g-0",style={'margin-bottom':'10px'})])
input_y_min_max_radiated_vertical = html.Div([dbc.Row(html.Label('Y axis limits',style={'fontWeight':'bold','margin-left':'20px','margin-bottom':'5px'})),
                            dbc.Row([dbc.Col([dbc.Stack([html.Label('Min',style={'fontWeight':'bold'}),dcc.Input(id='input_y_min_radiated_vertical',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)]),dbc.Col([dbc.Stack([html.Label('Max',style={'fontWeight':'bold'}),dcc.Input(id='input_y_max_radiated_vertical',type='number',value=None,debounce = True,style={'width':'75px', 'textAlign':'center'})],direction="horizontal",gap=2)])],className="g-0")])

Cursor_menu_radiated_vertical = html.Div([
    dbc.Row(dbc.Stack([html.Label('Activate cursors',style={'fontWeight':'bold','margin-right':'10px'}),daq.BooleanSwitch(id='activate_cursor_radiated_vertical',on=False)],direction="horizontal",gap=0.5,style={'padding':'5px 20px','margin-bottom':'5px'})),
    dbc.Row([dcc.Dropdown(id='cursor_list_radiated_vertical',options=[],placeholder="Select a line",style={'width':'240px','display': 'none','margin-bottom':'5px'})]),
    dbc.Row(html.Label(f'ΔFrequency (MHz) = - \n ΔLevel (dBμV/m) = -',id='cursor_output_radiated_vertical',style={"white-space": "pre",'fontWeight':'bold','display': 'none'}))],style={'padding':'10px'})

line_table_btn_radiated_vertical = html.Button('Show Line Display Parameters',id='line_table_btn_radiated_vertical',n_clicks=0,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"})

line_menu_radiated_vertical = html.Div([dbc.Row((line_table_btn_radiated_vertical),justify='center')],style={'padding':'10px'})

param_emission_radiated_vertical = html.Div([label_radiated_vertical, log_btn_radiated_vertical, input_x_min_max_radiated_vertical ,input_y_min_max_radiated_vertical , Cursor_menu_radiated_vertical, line_menu_radiated_vertical], id='Div_axes_param_radiated_vertical',style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px', 'display':'none'})

limits_table_radiated_vertical = dag.AgGrid(
        id="limits_table_radiated_vertical",
        rowData=[],
        columnDefs=columnDefs_limits,
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True,
                         "isRowSelectable": {'function': "params.data.disabled == 'False'"}},
        defaultColDef={'resizable': True},
        style={'center': True, 'fontSize': '12px', 'height': '300px', 'width': '100%'})

line_table_radiated_vertical = dag.AgGrid(
        id="line_table_radiated_vertical",
        rowData=[],
        columnDefs=columnDefs_line,
        dashGridOptions={"rowSelection": "multiple", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "rowDragMultiRow": True,
                         "suppressMoveWhenRowDragging": True},
        defaultColDef={'resizable': True},
        style={'center': True, 'fontSize': '12px', 'height': '300px', 'width': '100%'})

line_table_Div_radiated_vertical = html.Div([dbc.Stack([limits_table_radiated_vertical, line_table_radiated_vertical],gap=2)],id='line_table_container_radiated_vertical',style={'width':800,'display':'none','position':'fixed','top':'20%','right':'305px','bg-color':'rgba(255,255,255,0.95)','padding':'10px 10px','boxShadow':'0px 4px 8px rgba(0,0,0,0.1)','zIndex':'1002','borderRadius':'8px','overflow':'auto'})

emission_radiated_horizontal_vertical_graph = dcc.Loading([dcc.Graph(id='emission_radiated_horizontal_vertical',
                                           figure={ 'data':[], 'layout': emission_radiated_horizontal_vertical_layout},
                                           config={'toImageButtonOptions': {'filename':'Emission_EMC_chart_screenshot'}, 'responsive':True, 'displaylogo':False, 'editable':True, 'edits': {'annotationTail':False, 'annotationText':True, 'axisTitleText':False, 'colorbarPosition':False, 'colorbarTitleText':False, 'legendPosition':False, 'legendText':False, 'shapePosition':False, 'titleText':False}, 'modeBarButtonsToRemove': ['zoom', 'pan','zoomin','zoomout','autoscale','resetscale','lasso2d', 'select2d']},
                                           style={'height': '600px','width':'100%','fontWeight':'bold', 'display':'none'})],
                                id='loading_emission_radiated_horizontal_vertical', overlay_style={"visibility":"unvisible", "filter": "blur(2px)"},type="circle")

suspectTable_radiated = dag.AgGrid(
        id = "suspectsTable-radiated",
        rowData = [],
        columnDefs = columnDefs_suspectTable,
        defaultColDef={'resizable': True, "filter": "agTextColumnFilter"},
        style={'width': '100%', 'center': True, 'display': 'block'},
        dashGridOptions={"rowSelection": "multiple", "suppressRowClickSelection": True, "animateRows": False,
                         "domLayout": "autoHeight", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "suppressMoveWhenRowDragging": True,
                         "isRowSelectable": {'function': "params.data.disabled == 'False'"}})

finalsTable_radiated = dag.AgGrid(
        id = "finalsTable-radiated",
        rowData = [],
        columnDefs = columnDefs_finalsTable,
        defaultColDef={'resizable': True, "filter": "agTextColumnFilter"},
        style={'width': '100%', 'center': True, 'display': 'block'},
        dashGridOptions={"rowSelection": "multiple", "suppressRowClickSelection": True, "animateRows": False,
                         "domLayout": "autoHeight", "rowDragManaged": True,
                         "rowDragEntireRow": True,
                         "suppressMoveWhenRowDragging": True,
                         "isRowSelectable": {'function': "params.data.disabled == 'False'"}})

minimize_suspectTable_radiated_btn = html.Div(id='minimize_suspectTable_radiated_container', children=[dbc.Row(html.Button('Hide Suspects Table',id='minimize_suspectTable_radiated_btn',n_clicks=1,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"}),justify='center')],style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px'})

minimize_finalTable_radiated_btn = html.Div(id='minimize_finalTable_radiated_container', children=[dbc.Row(html.Button('Hide Finals Table',id='minimize_finalTable_radiated_btn',n_clicks=1,style={'width':'230px','height':'50px',"padding": "15px","background-color": "#1F3A68","color": "#FFF","border": "none","cursor": "pointer","font-size": "14px","font-family": "Arial, sans-serif","border-radius": "5px"}),justify='center')],style={'border':'1px solid #d6d6d6','border-radius':'10px','padding':'10px','margin-bottom':'10px'})

emission_radiated_table=html.Div(dbc.Stack([emission_radiated_horizontal_graph, emission_radiated_vertical_graph, emission_radiated_horizontal_vertical_graph, suspectTable_radiated, finalsTable_radiated],gap = 3),style={'height': '100%','width':'100%','border':'1px solid #d6d6d6','border-top':'none','margin-top':'-20px','padding':'10px'})

imunity_graph=dcc.Graph(id='Chart-2',config={'displayModeBar':False})
tables=html.Div([
    dcc.Tabs(id='test-tabs',value='', children=[
        dcc.Tab(id='emission-conducted-voltage-tab', label='Emission - Conducted Voltage', value='emission-conducted-voltage-tab',disabled=True,children=[emission_conducted_table],style={'font-size':18,'font-weight': 'bold'},selected_style={'font-size':18,'font-weight': 'bold'}),
        dcc.Tab(id='emission-radiated-electric-tab', label='Emission - Radiated Electric', value='emission-radiated-electric-tab',disabled=True,children=[emission_radiated_table] ,style={'font-size':18,'font-weight': 'bold'},selected_style={'font-size':18,'font-weight': 'bold'}),
        dcc.Tab(id='report-tab', label='Report', value='report-tab',disabled=True,children=[html.Div('',style={'border':'1px solid #d6d6d6','border-top':'none'})],style={'font-size':18,'font-weight': 'bold'},selected_style={'font-size':18,'font-weight': 'bold'})
    ],style={'padding':'20px 0px'})])

footer=html.Footer([html.P('Copyright © 2024 Monolithic Power Systems, Inc. All rights reserved.',style={'text-align':'center','color':'#666'})],style={'position':'relative','bottom':'0','width':'100%','padding':'20px 0px','background-color':'#e0e0e0','text-align':'center','margin-top':'20px'})

USERNAME_PASSWORD_PAIRS = [['username','password']]

server = Flask(__name__)
server.config.update(SECRET_KEY="SECRET_KEY")

app = dash.Dash(__name__, server=server, include_assets_files=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.secret_key = 'super secret key'
auth = dash_auth.BasicAuth(app, USERNAME_PASSWORD_PAIRS)
server = app.server

# App layout
app.layout = html.Div([
    # Button to toggle the sidebar
    html.Button("Graph Parameters", id="toggle-button", n_clicks=0, disabled=True,
                style={
                    "position": "fixed",
                    "right": "20px",
                    "top": "94px",
                    "z-index": "1001",
                    "background-color": "#1F3A68",  # MPS-style blue background
                    "color": "#FFF",
                    "border": "none",
                    "padding": "10px 20px",
                    "cursor": "pointer",
                    "font-size": "16px",
                    "border-radius": "5px",
                    "transition": "background-color 0.3s ease",  # Button hover effect
                    "transition": "transform 0.3s ease",
                }),

    # Sidebar div
    html.Div(id="sidebar", style=sidebar_style, children=[
        html.H2("Graph Parameters", style={"font-size": "24px", "margin-bottom": "20px", "font-weight": "bold", "font-family": "Arial, sans-serif"}),
        html.Hr(style={"border-color": "#BDC3C7"}),  # Light gray line

        # Emission Results Button
        html.Button("Conducted Voltage", id="emission_conducted_param_btn", style=button_style, disabled=True),

        # Emission Results Submenu
        html.Div(id="conducted-voltage-submenu", children=[
            param_emission_conducted_phase, param_emission_conducted_wire, marker_menu_conducted, minimize_suspectTable_conducted_btn, minimize_finalTable_conducted_btn
        ], style=submenu_style),

        # Immunity Button
        html.Button("Radiated Electric", id="emission_radiated_param_btn", style=button_style, disabled=True),

        # Immunity Submenu
        html.Div(id="radiated-electric-submenu", children=[
            param_emission_radiated_horizontal, param_emission_radiated_vertical, param_emission_radiated_horizontal_vertical, marker_menu_radiated, minimize_suspectTable_radiated_btn, minimize_finalTable_radiated_btn
        ], style=submenu_style),
    ]),

    # Main content area
    html.Div([
        html.Div([
            html.Div([
                logo, title
            ], style={'display': 'flex', 'align-items': 'center'}),
            location
        ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between',
                  'padding': '10px 20px', 'background-color': '#1E2A38', 'color': 'white', 'margin-bottom': '20px'}),
        html.Div(
            [project, table, tables], style={'flex': '1', 'margin': '0 20px'}),
        footer,
        line_table_Div_conducted_phase,
        line_table_Div_conducted_wire,
        line_table_Div_radiated_horizontal,
        line_table_Div_radiated_vertical,
        line_table_Div_radiated_horizontal_vertical,
        dcc.Store(id='left-cursor', data=None),
        dcc.Store(id='right-cursor', data=None),
        dcc.Store(id='markers', data=[]),
        dcc.Store(id='colors', data=default_colors),
        dcc.Store(id='rowData_test_conducted_phase', data={}),
        dcc.Store(id='rowData_test_conducted_wire', data={}),
        dcc.Store(id='rowData_test_radiated_horizontal', data={}),
        dcc.Store(id='rowData_test_radiated_vertical', data={}),
        dcc.Store(id='rowData_test_radiated_horizontal_vertical', data={}),
        dcc.Store(id='selectedRows_conducted_phase', data=[]),
        dcc.Store(id='selectedRows_conducted_wire', data=[]),
        dcc.Store(id='selectedRows_radiated_horizontal', data=[]),
        dcc.Store(id='selectedRows_radiated_vertical', data=[]),
        dcc.Store(id='selectedRows_radiated_horizontal_vertical', data=[]),
        dcc.Store(id='cursor_data', data={'left': {},'right': {}}),
    ], style={'display': 'flex', 'flexDirection': 'column', 'minHeight': '100vh'})
])

@app.callback(Output('emission_conducted_phase', 'figure', allow_duplicate = True),
    Output('emission_conducted_wire', 'figure', allow_duplicate = True),
    Output('markers', 'data', allow_duplicate = True),
    Input('clear_markers_btn_conducted', 'n_clicks'),
    State('markers', 'data'),
    State('emission_conducted_phase', 'figure'),
    State('emission_conducted_wire', 'figure'),
    prevent_initial_call=True)

def clear_markers_conducted(n_clicks, data, figure_phase, figure_wire):
    if data != []:
        figures = [figure_phase, figure_wire]
        figure_res = []
        for figure in figures:
            if figure['data'] != []:
                res, data = clear_markers(data, figure)
                figure_res.append(res)
            else:
                figure_res.append(no_update)
        return figure_res[0], figure_res[1], data
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_horizontal', 'figure', allow_duplicate = True),
    Output('emission_radiated_vertical', 'figure', allow_duplicate = True),
    Output('emission_radiated_horizontal_vertical', 'figure', allow_duplicate = True),
    Output('markers', 'data', allow_duplicate = True),
    Input('clear_markers_btn_radiated', 'n_clicks'),
    State('markers', 'data'),
    State('emission_radiated_horizontal', 'figure'),
    State('emission_radiated_vertical', 'figure'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    prevent_initial_call=True)

def clear_markers_radiated(n_clicks, data, figure_horizontal, figure_vertical, figure_horizontal_vertical):
    if data != []:
        figures = [figure_horizontal, figure_vertical, figure_horizontal_vertical]
        figure_res = []
        for figure in figures:
            if figure['data'] != []:
                res, data = clear_markers(data, figure)
                figure_res.append(res)
            else:
                figure_res.append(no_update)
        return figure_res[0], figure_res[1], figure_res[2], data
    else:
        raise PreventUpdate

def clear_markers(data, figure):
    for marker in data:
        for i in range (len(figure['data'])):
            if marker['name'] == figure['data'][i]['name']:
                figure['data'].pop(i)
                break
        for i in range (len(figure['layout']['annotations'])):
            if marker['name'] == figure['layout']['annotations'][i]['name']:
                figure['layout']['annotations'].pop(i)
                break
    data = []
    return figure, data

@app.callback(Output('emission_conducted_phase', 'figure', allow_duplicate = True),
    Output('emission_conducted_wire', 'figure', allow_duplicate = True),
    Input('activate-marker_conducted', 'on'),
    State('markers', 'data'),
    State('emission_conducted_phase', 'figure'),
    State('emission_conducted_wire', 'figure'),
    prevent_initial_call=True)

def toggle_marker_conducted(on, data, figure_phase, figure_wire):
    if data != []:
        figures = [figure_phase, figure_wire]
        figure_res = []
        for figure in figures:
            if figure['data'] != []:
                figure_res.append(toggle_marker(on, data, figure))
            else:
                figure_res.append(no_update)
        return figure_res[0], figure_res[1]
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_horizontal', 'figure', allow_duplicate = True),
    Output('emission_radiated_vertical', 'figure', allow_duplicate = True),
    Output('emission_radiated_horizontal_vertical', 'figure', allow_duplicate = True),
    Input('activate-marker_radiated', 'on'),
    State('markers', 'data'),
    State('emission_radiated_horizontal', 'figure'),
    State('emission_radiated_vertical', 'figure'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    prevent_initial_call=True)

def toggle_marker_radiated(on, data, figure_horizontal, figure_vertical, figure_horizontal_vertical):
    if data != []:
        figures = [figure_horizontal, figure_vertical, figure_horizontal_vertical]
        figure_res = []
        for figure in figures:
            if figure['data'] != []:
                figure_res.append(toggle_marker(on, data, figure))
            else:
                figure_res.append(no_update)
        return figure_res[0], figure_res[1], figure_res[2]
    else:
        raise PreventUpdate

def toggle_marker(on, data, figure):
    if on is True:
        for marker in data:
            for trace in figure['data']:
                if marker['name'] == trace['name']:
                    trace['visible'] = True
                    break
            for annotation in figure['layout']['annotations']:
                if marker['name'] == annotation['name']:
                    annotation['visible'] = True
                    break
    if on is False:
        for marker in data:
            for trace in figure['data']:
                if marker['name'] == trace['name']:
                    trace['visible'] = False
                    break
            for annotation in figure['layout']['annotations']:
                if marker['name'] == annotation['name']:
                    annotation['visible'] = False
                    break
    return figure

@app.callback(Output('line_table_container_conducted_phase', 'style', allow_duplicate = True),
    Output('line_table_container_conducted_wire', 'style', allow_duplicate = True),
    Output('line_table_btn_conducted_phase', 'children', allow_duplicate = True),
    Output('line_table_btn_conducted_wire', 'children', allow_duplicate = True),
    Input('line_table_btn_conducted_phase', 'n_clicks'),
    Input('emission_radiated_param_btn', 'n_clicks'),
    Input('emission_conducted_param_btn', 'n_clicks'),
    State('line_table_btn_conducted_phase', 'children'),
    State('line_table_container_conducted_phase', 'style'),
    State('line_table_container_conducted_wire', 'style'),
    prevent_initial_call=True)

def toggle_line_param_phase (btn_click, radiated_btn, conducted_btn, btn_txt, line_param_phase, line_param_wire):
    triggered_id = ctx.triggered_id
    if triggered_id == 'line_table_btn_conducted_phase' or btn_txt == 'Hide Line Display Parameters':
        line_params = [(line_param_phase, ''), (line_param_wire, '')]
        res_line_params = toggle_line_param (line_params, btn_txt, 0)
        return res_line_params[0][0], res_line_params[1][0], res_line_params[0][1], res_line_params[1][1]
    else:
        raise PreventUpdate

@app.callback(Output('line_table_container_conducted_phase', 'style', allow_duplicate = True),
    Output('line_table_container_conducted_wire', 'style', allow_duplicate = True),
    Output('line_table_btn_conducted_phase', 'children', allow_duplicate = True),
    Output('line_table_btn_conducted_wire', 'children', allow_duplicate = True),
    Input('line_table_btn_conducted_wire', 'n_clicks'),
    Input('emission_radiated_param_btn', 'n_clicks'),
    Input('emission_conducted_param_btn', 'n_clicks'),
    State('line_table_btn_conducted_wire', 'children'),
    State('line_table_container_conducted_phase', 'style'),
    State('line_table_container_conducted_wire', 'style'),
    prevent_initial_call=True)

def toggle_line_param_wire (btn_click, radiated_btn, conducted_btn, btn_txt, line_param_phase, line_param_wire):
    triggered_id = ctx.triggered_id
    if triggered_id == 'line_table_btn_conducted_wire' or btn_txt == 'Hide Line Display Parameters':
        line_params = [(line_param_phase, ''), (line_param_wire, '')]
        res_line_params = toggle_line_param (line_params, btn_txt, 1)
        return res_line_params[0][0], res_line_params[1][0], res_line_params[0][1], res_line_params[1][1]
    else:
        raise PreventUpdate

@app.callback(Output('line_table_container_radiated_horizontal', 'style', allow_duplicate = True),
    Output('line_table_container_radiated_vertical', 'style', allow_duplicate = True),
    Output('line_table_container_radiated_horizontal_vertical', 'style', allow_duplicate = True),
    Output('line_table_btn_radiated_horizontal', 'children', allow_duplicate = True),
    Output('line_table_btn_radiated_vertical', 'children', allow_duplicate = True),
    Output('line_table_btn_radiated_horizontal_vertical', 'children', allow_duplicate=True),
    Input('line_table_btn_radiated_horizontal', 'n_clicks'),
    Input('emission_radiated_param_btn', 'n_clicks'),
    Input('emission_conducted_param_btn', 'n_clicks'),
    State('line_table_btn_radiated_horizontal', 'children'),
    State('line_table_container_radiated_horizontal', 'style'),
    State('line_table_container_radiated_vertical', 'style'),
    State('line_table_container_radiated_horizontal_vertical', 'style'),
    prevent_initial_call=True)

def toggle_line_param_radiated_horizontal (btn_click, radiated_btn, conducted_btn, btn_txt,line_param_horizontal, line_param_vertical, line_param_horizontal_vertical):
    triggered_id = ctx.triggered_id
    if triggered_id == 'line_table_btn_radiated_horizontal' or btn_txt == 'Hide Line Display Parameters':
        line_params = [(line_param_horizontal, ''), (line_param_vertical, ''), (line_param_horizontal_vertical, '')]
        res_line_params = toggle_line_param (line_params, btn_txt, 0)
        return res_line_params[0][0], res_line_params[1][0], res_line_params[2][0], res_line_params[0][1], res_line_params[1][1], res_line_params[2][1]
    else:
        raise PreventUpdate

@app.callback(Output('line_table_container_radiated_horizontal', 'style', allow_duplicate = True),
    Output('line_table_container_radiated_vertical', 'style', allow_duplicate = True),
    Output('line_table_container_radiated_horizontal_vertical', 'style', allow_duplicate = True),
    Output('line_table_btn_radiated_horizontal', 'children', allow_duplicate = True),
    Output('line_table_btn_radiated_vertical', 'children', allow_duplicate = True),
    Output('line_table_btn_radiated_horizontal_vertical', 'children', allow_duplicate=True),
    Input('line_table_btn_radiated_vertical', 'n_clicks'),
    Input('emission_radiated_param_btn', 'n_clicks'),
    Input('emission_conducted_param_btn', 'n_clicks'),
    State('line_table_btn_radiated_vertical', 'children'),
    State('line_table_container_radiated_horizontal', 'style'),
    State('line_table_container_radiated_vertical', 'style'),
    State('line_table_container_radiated_horizontal_vertical', 'style'),
    prevent_initial_call=True)

def toggle_line_param_radiated_vertical (btn_click, radiated_btn, conducted_btn, btn_txt,line_param_horizontal, line_param_vertical, line_param_horizontal_vertical):
    triggered_id = ctx.triggered_id
    if triggered_id == 'line_table_btn_radiated_vertical' or btn_txt == 'Hide Line Display Parameters':
        line_params = [(line_param_horizontal, ''), (line_param_vertical, ''), (line_param_horizontal_vertical, '')]
        res_line_params = toggle_line_param (line_params, btn_txt, 1)
        return res_line_params[0][0], res_line_params[1][0], res_line_params[2][0], res_line_params[0][1], res_line_params[1][1], res_line_params[2][1]
    else:
        raise PreventUpdate

@app.callback(Output('line_table_container_radiated_horizontal', 'style', allow_duplicate = True),
    Output('line_table_container_radiated_vertical', 'style', allow_duplicate = True),
    Output('line_table_container_radiated_horizontal_vertical', 'style', allow_duplicate = True),
    Output('line_table_btn_radiated_horizontal', 'children', allow_duplicate = True),
    Output('line_table_btn_radiated_vertical', 'children', allow_duplicate = True),
    Output('line_table_btn_radiated_horizontal_vertical', 'children', allow_duplicate=True),
    Input('line_table_btn_radiated_horizontal_vertical', 'n_clicks'),
    Input('emission_radiated_param_btn', 'n_clicks'),
    Input('emission_conducted_param_btn', 'n_clicks'),
    State('line_table_btn_radiated_horizontal_vertical', 'children'),
    State('line_table_container_radiated_horizontal', 'style'),
    State('line_table_container_radiated_vertical', 'style'),
    State('line_table_container_radiated_horizontal_vertical', 'style'),
    prevent_initial_call=True)

def toggle_line_param_radiated_horizontal_vertical (btn_click, radiated_btn, conducted_btn, btn_txt,line_param_horizontal, line_param_vertical, line_param_horizontal_vertical):
    triggered_id = ctx.triggered_id
    if triggered_id == 'line_table_btn_radiated_horizontal_vertical' or btn_txt == 'Hide Line Display Parameters':
        line_params = [(line_param_horizontal,''), (line_param_vertical,''), (line_param_horizontal_vertical,'')]
        res_line_params = toggle_line_param (line_params, btn_txt, 2)
        return res_line_params[0][0], res_line_params[1][0], res_line_params[2][0], res_line_params[0][1], res_line_params[1][1], res_line_params[2][1]
    else:
        raise PreventUpdate

def toggle_line_param (line_params, btn_txt, id):
    triggered_id = ctx.triggered_id
    for index, element in enumerate(line_params):
        style = element[0]
        if triggered_id != 'emission_radiated_param_btn' and triggered_id != 'emission_conducted_param_btn' and index == id:
            if btn_txt == 'Show Line Display Parameters':
                style['display'] = 'block'
                line_params[index] = (style, 'Hide Line Display Parameters')
            else:
                style['display'] = 'none'
                line_params[index] = (style, 'Show Line Display Parameters')
        else:
            style['display'] = 'none'
            line_params[index] = (style, 'Show Line Display Parameters')
    return line_params

@app.callback(Output('loading-screen', 'children',allow_duplicate = True),
    Output('loading-screen', 'style',allow_duplicate = True),
    Output('load-project', 'contents',allow_duplicate = True),
    Input('load-project', 'contents'),
    Input('Remove-project', 'n_clicks'),
    State('loading-screen', 'children'),
    State('loading-screen', 'style'),
    State('rowData_test_radiated_horizontal_vertical', 'data'),
    State('Project-list', 'value'),
    prevent_initial_call=True)

def toggle_loading(contents, n_clicks, children, style, data, value):
    triggered_id = ctx.triggered_id
    if triggered_id == 'load-project':
        style['backgroundColor'] = '#119DFF'
        return [dbc.Spinner(size="sm"), "  Loading a new project"], style, None
    elif triggered_id == 'Remove-project' and value is not None and len(data) == 1:
        style['backgroundColor'] = '#119DFF'
        time.sleep(1)
        return ['No loaded project'], style, None
    else:
        style['backgroundColor'] = 'red'
        return [cross, '  Project update failed'], style, None

@app.callback(Output('Project-list', 'options',allow_duplicate = True),
    Output('rowData_test_conducted_phase', 'data',allow_duplicate = True),
    Output('rowData_test_conducted_wire', 'data',allow_duplicate = True),
    Output('rowData_test_radiated_horizontal', 'data',allow_duplicate = True),
    Output('rowData_test_radiated_vertical', 'data',allow_duplicate = True),
    Output('rowData_test_radiated_horizontal_vertical', 'data',allow_duplicate = True),
    Output('load-project', 'filename',allow_duplicate = True),
    Output('loading-screen', 'children',allow_duplicate = True),
    Output('loading-screen', 'style',allow_duplicate = True),
    Input('load-project', 'filename'),
    Input('Remove-project', 'n_clicks'),
    State('load-project', 'contents'),
    State('Project-list', 'value'),
    State('Project-list', 'options'),
    State('loading-screen', 'style'),
    State('rowData_test_conducted_phase', 'data'),
    State('rowData_test_conducted_wire', 'data'),
    State('rowData_test_radiated_horizontal', 'data'),
    State('rowData_test_radiated_vertical', 'data'),
    State('rowData_test_radiated_horizontal_vertical', 'data'),
    prevent_initial_call=True)

def update_Project_list(Project_path, remove_click, Project_content, value, options, style, rowData_test_conducted_horizontal, rowData_test_conducted_vertical, rowData_test_radiated_horizontal, rowData_test_radiated_vertical, rowData_test_radiated_horizontal_vertical):
    try:
        triggered_id=ctx.triggered_id
        if triggered_id == 'load-project':
            return add_project(options,Project_path, Project_content, style, rowData_test_conducted_horizontal, rowData_test_conducted_vertical, rowData_test_radiated_horizontal, rowData_test_radiated_vertical, rowData_test_radiated_horizontal_vertical)
        elif triggered_id == 'Remove-project' and value is not None:
            return remove_Project_list(value, options, style, rowData_test_conducted_horizontal, rowData_test_conducted_vertical, rowData_test_radiated_horizontal, rowData_test_radiated_vertical, rowData_test_radiated_horizontal_vertical)
        else:
            style['backgroundColor'] = 'red'
            return options, no_update, no_update, no_update, no_update, no_update, None, [cross, '  Project update failed'], style
    except:
        style['backgroundColor'] = 'red'
        return options, no_update, no_update, no_update, no_update, no_update, None, [cross, '  Project update failed'], style

def add_project(options,Project_path, Project_content, style, rowData_test_conducted_horizontal, rowData_test_conducted_vertical, rowData_test_radiated_horizontal, rowData_test_radiated_vertical, rowData_test_radiated_horizontal_vertical):
    if Project_path:
        Project_name = os.path.basename(Project_path).split('/')[-1]
        Project_name = '.'.join(Project_name.split('.')[:-1])
        if Project_name in options:
            style['backgroundColor'] = 'green'
            return options, no_update, no_update, no_update, no_update, no_update, None, [check, '  Project already loaded'], style
        Project_content = base64.b64decode(Project_content.split(',')[1])
        Project_content = zipfile.ZipFile(io.BytesIO(Project_content))
        with tempfile.TemporaryDirectory() as upload_directory:
            Project_content.extractall(upload_directory)
            for root, dirs, files in os.walk(upload_directory):
                for file in files:
                    rowData = []
                    if file.endswith('xlsx') or file.endswith('xls') or file.endswith('csv'):
                        df = pd.read_excel(os.path.join(root, file), sheet_name = None)
                        test_name = file.split('.')[0]
                        test_type = df['Test Infos'].iloc[0]['Type']
                        limit = df['Test Infos'].iloc[0]['Limit']
                        modification = df['Test Infos'].iloc[0]['Modification']
                        test_date = df['Test Infos'].iloc[0]['Date']
                        test_pass = df['Test Infos'].iloc[0]['Passed/Failed']
                        for subrange in range((len(df['Subrange Settings']))):
                            polarization = df['Subrange Settings'].iloc[subrange]['Polarization']
                            freq_range = df['Subrange Settings'].iloc[subrange]['Frequency Range']
                            bandwidth = df['Subrange Settings'].iloc[subrange]['RBW']
                            detectors = df['Subrange Settings'].iloc[subrange]['Detector']
                            for index, detector in enumerate(detectors.split(', ')):
                                data = {}
                                data['data'] = df['Data'][df['Data']['Subrange'] == subrange + 1].iloc[:,[1, index + 2]].to_json()
                                data['Limit Definition'] = df['Limit Definition'].to_json()
                                if 'Suspects Table' and 'Finals Table' in list(df.keys()):
                                    data['suspects'] = df['Suspects Table'][df['Data']['Subrange'] == subrange + 1].to_json()
                                    data['finals'] = df['Finals Table'][df['Data']['Subrange'] == subrange + 1].to_json().to_json()
                                elif 'Suspects Table' in list(df.keys()):
                                    data['suspects'] = df['Suspects Table'][df['Data']['Subrange'] == subrange + 1].to_json()
                                elif 'Finals Table' in list(df.keys()):
                                    data['finals'] = df['Finals Table'][df['Data']['Subrange'] == subrange + 1].to_json()
                                rowData.append({
                                    "Test name": test_name,
                                    "Test Type": test_type,
                                    "Limit": limit,
                                    "Polarization": polarization,
                                    "Detector": detector,
                                    "Frequency Range": freq_range,
                                    "Bandwidth": bandwidth,
                                    "Modification": modification,
                                    "Date": test_date,
                                    "Test_Pass": test_pass,
                                    "Data": data})
                        if test_type == 'Conducted Voltage Emission':
                            if polarization == 'Phase 1':
                                if Project_name in rowData_test_conducted_horizontal:
                                    rowData_test_conducted_horizontal[Project_name].extend(rowData)
                                else:
                                    rowData_test_conducted_horizontal[Project_name] = rowData
                            elif polarization == 'Wire +':
                                if Project_name in rowData_test_conducted_vertical:
                                    rowData_test_conducted_vertical[Project_name].extend(rowData)
                                else:
                                    rowData_test_conducted_vertical[Project_name] = rowData
                        elif test_type == 'Radiated Electric Emission':
                            if polarization == 'Horizontal':
                                if Project_name in rowData_test_radiated_horizontal:
                                    rowData_test_radiated_horizontal[Project_name].extend(rowData)
                                else:
                                    rowData_test_radiated_horizontal[Project_name] = rowData
                            elif polarization == 'Vertical':
                                if Project_name in rowData_test_radiated_vertical:
                                    rowData_test_radiated_vertical[Project_name].extend(rowData)
                                else:
                                    rowData_test_radiated_vertical[Project_name] = rowData
                            elif polarization == 'H/V':
                                if Project_name in rowData_test_radiated_horizontal_vertical:
                                    rowData_test_radiated_horizontal_vertical[Project_name].extend(rowData)
                                else:
                                    rowData_test_radiated_horizontal_vertical[Project_name] = rowData

        options.append(Project_name)
        style['backgroundColor'] = 'green'
    return options, rowData_test_conducted_horizontal, rowData_test_conducted_vertical, rowData_test_radiated_horizontal, rowData_test_radiated_vertical, rowData_test_radiated_horizontal_vertical, None, [check, '  Project successfully loaded'], style

def remove_Project_list(value, options, style, rowData_test_conducted_horizontal, rowData_test_conducted_vertical, rowData_test_radiated_horizontal, rowData_test_radiated_vertical, rowData_test_radiated_horizontal_vertical):
    options.remove(value)
    if value in rowData_test_conducted_horizontal.keys():
        rowData_test_conducted_horizontal.pop(value)
    if value in rowData_test_conducted_vertical.keys():
        rowData_test_conducted_vertical.pop(value)
    if value in rowData_test_radiated_horizontal.keys():
        rowData_test_radiated_horizontal.pop(value)
    if value in rowData_test_radiated_vertical.keys():
        rowData_test_radiated_vertical.pop(value)
    if value in rowData_test_radiated_horizontal_vertical.keys():
        rowData_test_radiated_horizontal_vertical.pop(value)
    style['backgroundColor'] = 'green'
    return options, rowData_test_conducted_horizontal, rowData_test_conducted_vertical, rowData_test_radiated_horizontal, rowData_test_radiated_vertical, rowData_test_radiated_horizontal_vertical, None, [check, '  Project successfully removed'], style

@app.callback(Output('Test-table', 'rowData',allow_duplicate = True),
    Input('Project-list', 'value'),
    State('rowData_test_conducted_phase', 'data'),
    State('rowData_test_conducted_wire', 'data'),
    State('rowData_test_radiated_horizontal', 'data'),
    State('rowData_test_radiated_vertical', 'data'),
    State('rowData_test_radiated_horizontal_vertical', 'data'),
    prevent_initial_call=True)

def update_Test_table(value, rowData_test_conducted_horizontal, rowData_test_conducted_vertical, rowData_test_radiated_horizontal, rowData_test_radiated_vertical, rowData_test_radiated_horizontal_vertical):
    if value:
        rowData_table = []
        rowData_test = [rowData_test_conducted_horizontal, rowData_test_conducted_vertical, rowData_test_radiated_horizontal, rowData_test_radiated_vertical, rowData_test_radiated_horizontal_vertical]
        for rowData in rowData_test:
            if value in rowData.keys():
                rowData_table.extend(rowData[value])
        return rowData_table
    else:
        return []

@app.callback(Output('suspectsTable-conducted', 'rowData',allow_duplicate = True),
    Output('suspectsTable-conducted', 'style',allow_duplicate = True),
    Output('suspectsTable-conducted', 'selectedRows',allow_duplicate = True),
    Output('minimize_suspectTable_conducted_container', "style"),
    Input('selectedRows_conducted_phase', 'data'),
    Input('selectedRows_conducted_wire', 'data'),
    State('suspectsTable-conducted', 'style'),
    State('minimize_suspectTable_conducted_container', "style"),
    prevent_initial_call=True)

def suspectsTable_conducted(selectedRows_conducted_phase, selectedRows_conducted_wire, style, minimize_suspectTable_container_style):
    selectedRows = selectedRows_conducted_phase + selectedRows_conducted_wire
    return suspectsTable(selectedRows, style, minimize_suspectTable_container_style, 'Conducted Voltage Emission')

@app.callback(Output('suspectsTable-radiated', 'rowData',allow_duplicate = True),
    Output('suspectsTable-radiated', 'style',allow_duplicate = True),
    Output('suspectsTable-radiated', 'selectedRows',allow_duplicate = True),
    Output('minimize_suspectTable_radiated_container', "style"),
    Input('selectedRows_radiated_horizontal', 'data'),
    Input('selectedRows_radiated_vertical', 'data'),
    Input('selectedRows_radiated_horizontal_vertical', 'data'),
    State('suspectsTable-radiated', 'style'),
    State('minimize_suspectTable_radiated_container', "style"),
    prevent_initial_call=True)

def suspectsTable_radiated(selectedRows_radiated_horizontal, selectedRows_radiated_vertical, selectedRows_radiated_horizontal_vertical, style, minimize_suspectTable_container_style):
    selectedRows = selectedRows_radiated_horizontal + selectedRows_radiated_vertical + selectedRows_radiated_horizontal_vertical
    return suspectsTable(selectedRows, style, minimize_suspectTable_container_style, 'Radiated Electric Emission')

def suspectsTable(selectedRows, style, minimize_suspectTable_container_style, type):
    rowData = []
    selectedRows_suspectsTable = {"ids":[]}
    if selectedRows:
        for row in selectedRows:
            if 'suspects' in list(row['Data'].keys()) and row['Test Type'] == type:
                suspects = pd.read_json(row['Data']['suspects'])
                test_name = row['Test name']
                for i in range(len(suspects)):
                    subrange = str(suspects.iloc[i]['Subrange'])
                    source = str(suspects.iloc[i]['Source'])
                    freq = suspects.iloc[i]['Frequency (MHz)']
                    peak = suspects.iloc[i]['Peak (dB µV/m)']
                    LimQ_Peak = str(suspects.iloc[i]['Lim.Q-Peak (dB µV/m)'])
                    PeakLimQPeak = str(suspects.iloc[i]['Peak-Lim.Q-Peak (dB)'])
                    Height = suspects.iloc[i]['Height (m)']
                    Angle = suspects.iloc[i]['Angle (°)']
                    Polarization = suspects.iloc[i]['Polarization']
                    Correction = suspects.iloc[i]['Correction (dB)']
                    rowData.append({
                        "Test Name": test_name,
                        "Subrange": subrange,
                        "Source": source,
                        "Frequency": freq,
                        "Peak": peak,
                        "LimQ_Peak": LimQ_Peak,
                        "Peak_LimQ_Peak": PeakLimQPeak,
                        "Height": Height,
                        "Angle": Angle,
                        "Polarization": Polarization,
                        "Correction": Correction,
                        'disabled': 'False'})
    if rowData != []:
        style['display'] = 'block'
        minimize_suspectTable_container_style['display'] = 'block'
        for i in range(len(rowData)):
            selectedRows_suspectsTable['ids'].append(str(i))
    else:
        style['display'] = 'none'
        minimize_suspectTable_container_style['display'] = 'none'
    return rowData, style, selectedRows_suspectsTable, minimize_suspectTable_container_style

@app.callback(Output('emission_conducted_phase', 'figure',allow_duplicate = True),
    Input('suspectsTable-conducted', 'selectedRows'),
    State('suspectsTable-conducted', 'rowData'),
    State('emission_conducted_phase', 'figure'),
    prevent_initial_call=True)

def select_suspect_conducted(selectedRows, rowData, figure):
    return select_suspect(selectedRows, rowData, figure)

@app.callback(Output('emission_radiated_horizontal_vertical', 'figure',allow_duplicate = True),
    Input('suspectsTable-radiated', 'selectedRows'),
    State('suspectsTable-radiated', 'rowData'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    prevent_initial_call=True)

def select_suspect_radiated(selectedRows, rowData, figure):
    return select_suspect(selectedRows, rowData, figure)

def select_suspect(selectedRows, rowData, figure):
    if rowData and 'ids' not in selectedRows:
        names = []
        for suspect in selectedRows:
            names.append('Suspect ' + suspect["Test Name"] + '-' + str(suspect['Subrange']) + '-' + suspect['Polarization'])
        for trace in figure['data']:
            if trace['meta']['Type'] == 'Suspect':
                if trace['name'] in names:
                    trace['visible'] = True
                else:
                    trace['visible'] = False
        return figure
    else:
        raise PreventUpdate

@app.callback(Output('finalsTable-conducted', 'rowData',allow_duplicate = True),
    Output('finalsTable-conducted', 'style',allow_duplicate = True),
    Output('finalsTable-conducted', 'selectedRows',allow_duplicate = True),
    Output('minimize_finalTable_conducted_container', "style"),
    Input('selectedRows_conducted_phase', 'data'),
    Input('selectedRows_conducted_wire', 'data'),
    State('finalsTable-conducted', 'style'),
    State('minimize_finalTable_conducted_container', "style"),
    prevent_initial_call=True)

def finalsTable_conducted(selectedRows_conducted_phase, selectedRows_conducted_wire, style, minimize_finalTable_conducted_container_style):
    selectedRows = selectedRows_conducted_phase + selectedRows_conducted_wire
    return finalsTable(selectedRows, style, minimize_finalTable_conducted_container_style, 'Conducted Voltage Emission')

@app.callback(Output('finalsTable-radiated', 'rowData',allow_duplicate = True),
    Output('finalsTable-radiated', 'style',allow_duplicate = True),
    Output('finalsTable-radiated', 'selectedRows',allow_duplicate = True),
    Output('minimize_finalTable_radiated_container', "style"),
    Input('selectedRows_radiated_horizontal', 'data'),
    Input('selectedRows_radiated_vertical', 'data'),
    Input('selectedRows_radiated_horizontal_vertical', 'data'),
    State('finalsTable-radiated', 'style'),
    State('minimize_finalTable_radiated_container', "style"),
    prevent_initial_call=True)

def finalsTable_radiated(selectedRows_radiated_horizontal, selectedRows_radiated_vertical, selectedRows_radiated_horizontal_vertical, style, minimize_finalTable_radiated_container_style):
    selectedRows = selectedRows_radiated_horizontal + selectedRows_radiated_vertical + selectedRows_radiated_horizontal_vertical
    return finalsTable(selectedRows, style, minimize_finalTable_radiated_container_style, 'Radiated Electric Emission')

def finalsTable(selectedRows, style, minimize_finalTable_container_style, type):
    rowData = []
    finalsTable_selectedRows = {"ids":[]}
    if selectedRows:
        for row in selectedRows:
            if 'finals' in list(row['Data'].keys()) and row['Test Type'] == type:
                finals = pd.read_json(row['Data']['finals'])
                test_name = row['Test name']
                for i in range(len(finals)):
                    subrange = str(finals.iloc[i]['Subrange'])
                    source = str(finals.iloc[i]['Source'])
                    freq = finals.iloc[i]['Frequency (MHz)']
                    QPeak_Level = finals.iloc[i]['QPeak Level (dBµV/m)']
                    QPeak_Margin = finals.iloc[i]['QPeak Margin (dBµV/m)']
                    Height = finals.iloc[i]['Height (m)']
                    Angle = finals.iloc[i]['Angle (°)']
                    Polarization = finals.iloc[i]['Polarization']
                    RBW = finals.iloc[i]['RBW (kHz)']
                    MeasTime = finals.iloc[i]['Meas.Time (s)']
                    rowData.append({
                        "Test Name": test_name,
                        "Subrange": subrange,
                        "Source": source,
                        "Frequency": freq,
                        "QPeak Level": QPeak_Level,
                        "QPeak Margin": QPeak_Margin,
                        "Height": Height,
                        "Angle": Angle,
                        "Polarization": Polarization,
                        "RBW (kHz)": RBW,
                        "Meas.Time": MeasTime})
    if rowData != []:
        style['display'] = 'block'
        minimize_finalTable_container_style['display'] = 'block'
        for i in range(len(rowData)):
            finalsTable_selectedRows['ids'].append(str(i))
    else:
        style['display'] = 'none'
        minimize_finalTable_container_style['display'] = 'none'
    return rowData, style, finalsTable_selectedRows, minimize_finalTable_container_style

@app.callback(Output('emission_conducted_phase', 'figure',allow_duplicate = True),
    Input('finalsTable-conducted', 'selectedRows'),
    State('finalsTable-conducted', 'rowData'),
    State('emission_conducted_phase', 'figure'),
    prevent_initial_call=True)

def select_final_conducted(selectedRows, rowData, figure):
    return select_final(selectedRows, rowData, figure)

@app.callback(Output('emission_radiated_horizontal_vertical', 'figure',allow_duplicate = True),
    Input('finalsTable-radiated', 'selectedRows'),
    State('finalsTable-radiated', 'rowData'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    prevent_initial_call=True)

def select_final_radiated(selectedRows, rowData, figure):
    return select_final(selectedRows, rowData, figure)

def select_final(selectedRows, rowData, figure):
    if rowData:
        names = []
        for final in selectedRows:
            names.append('Final ' + final["Test Name"] + '-' + str(final['Subrange']) + '-' + final['Polarization'])
        for trace in figure['data']:
            if trace['meta']['Type'] == 'Suspect':
                if trace['name'] in names:
                    trace['visible'] = True
                else:
                    trace['visible'] = False
        return figure
    else:
        raise PreventUpdate

@app.callback(Output('selectedRows_conducted_phase', 'data',allow_duplicate = True),
    Output('selectedRows_conducted_wire', 'data',allow_duplicate = True),
    Output('selectedRows_radiated_horizontal', 'data',allow_duplicate = True),
    Output('selectedRows_radiated_vertical', 'data',allow_duplicate = True),
    Output('selectedRows_radiated_horizontal_vertical', 'data',allow_duplicate = True),
    Input('Test-table', 'selectedRows'),
    State('selectedRows_conducted_phase', 'data'),
    State('selectedRows_conducted_wire', 'data'),
    State('selectedRows_radiated_horizontal', 'data'),
    State('selectedRows_radiated_vertical', 'data'),
    State('selectedRows_radiated_horizontal_vertical', 'data'),
    prevent_initial_call=True)

def store_selected_Rows(selectedRows, selectedRows_conducted_phase, selectedRows_conducted_wire, selectedRows_radiated_horizontal, selectedRows_radiated_vertical, selectedRows_radiated_horizontal_vertical):
    new_selectedRows_conducted_phase, new_selectedRows_conducted_wire, new_selectedRows_radiated_horizontal, new_selectedRows_radiated_vertical, new_selectedRows_radiated_horizontal_vertical =[], [], [], [], []
    for row in selectedRows:
        if row['Test Type'] == 'Conducted Voltage Emission':
            if row['Polarization'] == 'Phase 1':
                new_selectedRows_conducted_phase.append(row)
            elif row['Polarization'] == 'Wire +':
                new_selectedRows_conducted_wire.append(row)
        elif row['Test Type'] == 'Radiated Electric Emission':
            if row['Polarization'] == 'Horizontal':
                new_selectedRows_radiated_horizontal.append(row)
            elif row['Polarization'] == 'Vertical':
                new_selectedRows_radiated_vertical.append(row)
            elif row['Polarization'] == 'H/V':
                new_selectedRows_radiated_horizontal_vertical.append(row)

    if new_selectedRows_conducted_phase == selectedRows_conducted_phase:
        new_selectedRows_conducted_phase = no_update
    if new_selectedRows_conducted_wire == selectedRows_conducted_wire:
        new_selectedRows_conducted_wire = no_update
    if new_selectedRows_radiated_horizontal == selectedRows_radiated_horizontal:
        new_selectedRows_radiated_horizontal = no_update
    if new_selectedRows_radiated_vertical == selectedRows_radiated_vertical:
        new_selectedRows_radiated_vertical = no_update
    if new_selectedRows_radiated_horizontal_vertical == selectedRows_radiated_horizontal_vertical:
        new_selectedRows_radiated_horizontal_vertical = no_update

    return new_selectedRows_conducted_phase, new_selectedRows_conducted_wire, new_selectedRows_radiated_horizontal, new_selectedRows_radiated_vertical, new_selectedRows_radiated_horizontal_vertical

@app.callback(Output('emission_conducted_phase', "figure", allow_duplicate = True),
    Output('emission_conducted_phase', 'relayoutData',allow_duplicate = True),
    Output('emission_conducted_phase', 'style',allow_duplicate = True),
    Output('loading_emission_conducted_phase', 'display',allow_duplicate = True),
    Output('cursor_list_conducted_phase','options',allow_duplicate = True),
    Output('cursor_list_conducted_phase','value',allow_duplicate = True),
    Output('activate_cursor_conducted_phase','on', allow_duplicate=True),
    Output('cursor_data', 'data', allow_duplicate=True),
    Output('emission-conducted-voltage-tab','disabled',allow_duplicate = True),
    Output('test-tabs','value', allow_duplicate=True),
    Output('markers', 'data',allow_duplicate = True),
    Output('cursor_output_conducted_phase', 'children', allow_duplicate=True),
    Output('Div_axes_param_conducted_phase', 'style'),
    Output('limits_table_conducted_phase', 'rowData', allow_duplicate=True),
    Output('limits_table_conducted_phase', 'selectedRows', allow_duplicate=True),
    Output('line_table_conducted_phase', 'rowData', allow_duplicate=True),
    Output('line_table_conducted_phase', 'selectedRows', allow_duplicate=True),
    Output('line_table_container_conducted_phase', 'style', allow_duplicate=True),
    Output('line_table_btn_conducted_phase', 'children', allow_duplicate=True),
    Output("emission_conducted_param_btn", 'disabled', allow_duplicate=True),
    Output("conducted-voltage-submenu", "style",allow_duplicate = True),
    Input('selectedRows_conducted_phase', 'data'),
    State('emission_conducted_phase', 'figure'),
    State('emission_conducted_phase', 'style'),
    State("line_table_conducted_phase", "selectedRows"),
    State('loading_emission_conducted_phase', 'display'),
    State('xaxis_emission_conducted_phase', 'value'),
    State('cursor_list_conducted_phase', 'options'),
    State('cursor_list_conducted_phase', 'value'),
    State('emission_conducted_param_btn', 'disabled'),
    State('test-tabs', 'value'),
    State('cursor_output_conducted_phase', 'children'),
    State('Div_axes_param_conducted_phase', 'style'),
    State('markers', 'data'),
    State('rowData_test_conducted_phase', 'data'),
    State('limits_table_conducted_phase', 'rowData'),
    State('line_table_conducted_phase', 'rowData'),
    State('line_table_container_conducted_phase', 'style'),
    State('line_table_btn_conducted_phase', 'children'),
    State('cursor_data', 'data'),
    State('activate_cursor_conducted_phase', 'on'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def figure_conducted_phase(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on):
    return update_chart(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on)

@app.callback(Output('emission_conducted_wire', "figure", allow_duplicate = True),
    Output('emission_conducted_wire', 'relayoutData',allow_duplicate = True),
    Output('emission_conducted_wire', 'style',allow_duplicate = True),
    Output('loading_emission_conducted_wire', 'display',allow_duplicate = True),
    Output('cursor_list_conducted_wire','options',allow_duplicate = True),
    Output('cursor_list_conducted_wire','value',allow_duplicate = True),
    Output('activate_cursor_conducted_wire','on', allow_duplicate=True),
    Output('cursor_data', 'data', allow_duplicate=True),
    Output('emission-conducted-voltage-tab','disabled',allow_duplicate = True),
    Output('test-tabs','value', allow_duplicate=True),
    Output('markers', 'data',allow_duplicate = True),
    Output('cursor_output_conducted_wire', 'children', allow_duplicate=True),
    Output('Div_axes_param_conducted_wire', 'style'),
    Output('limits_table_conducted_wire', 'rowData', allow_duplicate=True),
    Output('limits_table_conducted_wire', 'selectedRows', allow_duplicate=True),
    Output('line_table_conducted_wire', 'rowData', allow_duplicate=True),
    Output('line_table_conducted_wire', 'selectedRows', allow_duplicate=True),
    Output('line_table_container_conducted_wire', 'style', allow_duplicate=True),
    Output('line_table_btn_conducted_wire', 'children', allow_duplicate=True),
    Output("emission_conducted_param_btn", 'disabled', allow_duplicate=True),
    Output("conducted-voltage-submenu", "style",allow_duplicate = True),
    Input('selectedRows_conducted_wire', 'data'),
    State('emission_conducted_wire', 'figure'),
    State('emission_conducted_wire', 'style'),
    State("line_table_conducted_wire", "selectedRows"),
    State('loading_emission_conducted_wire', 'display'),
    State('xaxis_emission_conducted_wire', 'value'),
    State('cursor_list_conducted_wire', 'options'),
    State('cursor_list_conducted_wire', 'value'),
    State('emission_conducted_param_btn', 'disabled'),
    State('test-tabs', 'value'),
    State('cursor_output_conducted_wire', 'children'),
    State('Div_axes_param_conducted_wire', 'style'),
    State('markers', 'data'),
    State('rowData_test_conducted_wire', 'data'),
    State('limits_table_conducted_wire', 'rowData'),
    State('line_table_conducted_wire', 'rowData'),
    State('line_table_container_conducted_wire', 'style'),
    State('line_table_btn_conducted_wire', 'children'),
    State('cursor_data', 'data'),
    State('activate_cursor_conducted_wire', 'on'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def figure_conducted_wire(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on):
    print(True)
    return update_chart(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on)

@app.callback(Output('emission_radiated_horizontal', "figure", allow_duplicate = True),
    Output('emission_radiated_horizontal', 'relayoutData',allow_duplicate = True),
    Output('emission_radiated_horizontal', 'style',allow_duplicate = True),
    Output('loading_emission_radiated_horizontal', 'display',allow_duplicate = True),
    Output('cursor_list_radiated_horizontal','options',allow_duplicate = True),
    Output('cursor_list_radiated_horizontal','value',allow_duplicate = True),
    Output('activate_cursor_radiated_horizontal','on', allow_duplicate=True),
    Output('cursor_data', 'data', allow_duplicate=True),
    Output('emission-radiated-electric-tab','disabled',allow_duplicate = True),
    Output('test-tabs','value', allow_duplicate=True),
    Output('markers', 'data',allow_duplicate = True),
    Output('cursor_output_radiated_horizontal', 'children', allow_duplicate=True),
    Output('Div_axes_param_radiated_horizontal', 'style'),
    Output('limits_table_radiated_horizontal', 'rowData', allow_duplicate=True),
    Output('limits_table_radiated_horizontal', 'selectedRows', allow_duplicate=True),
    Output('line_table_radiated_horizontal', 'rowData', allow_duplicate=True),
    Output('line_table_radiated_horizontal', 'selectedRows', allow_duplicate=True),
    Output('line_table_container_radiated_horizontal', 'style', allow_duplicate=True),
    Output('line_table_btn_radiated_horizontal', 'children', allow_duplicate=True),
    Output("emission_radiated_param_btn", 'disabled', allow_duplicate=True),
    Output("radiated-electric-submenu", "style",allow_duplicate = True),
    Input('selectedRows_radiated_horizontal', 'data'),
    State('emission_radiated_horizontal', 'figure'),
    State('emission_radiated_horizontal', 'style'),
    State("line_table_radiated_horizontal", "selectedRows"),
    State('loading_emission_radiated_horizontal', 'display'),
    State('xaxis_emission_radiated_horizontal', 'value'),
    State('cursor_list_radiated_horizontal', 'options'),
    State('cursor_list_radiated_horizontal', 'value'),
    State('emission_radiated_param_btn', 'disabled'),
    State('test-tabs', 'value'),
    State('cursor_output_radiated_horizontal', 'children'),
    State('Div_axes_param_radiated_horizontal', 'style'),
    State('markers', 'data'),
    State('rowData_test_radiated_horizontal', 'data'),
    State('limits_table_radiated_horizontal', 'rowData'),
    State('line_table_radiated_horizontal', 'rowData'),
    State('line_table_container_radiated_horizontal', 'style'),
    State('line_table_btn_radiated_horizontal', 'children'),
    State('cursor_data', 'data'),
    State('activate_cursor_radiated_horizontal', 'on'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def figure_radiated_horizontal(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on):
    return update_chart(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on)

@app.callback(Output('emission_radiated_vertical', "figure", allow_duplicate = True),
    Output('emission_radiated_vertical', 'relayoutData',allow_duplicate = True),
    Output('emission_radiated_vertical', 'style',allow_duplicate = True),
    Output('loading_emission_radiated_vertical', 'display',allow_duplicate = True),
    Output('cursor_list_radiated_vertical','options',allow_duplicate = True),
    Output('cursor_list_radiated_vertical','value',allow_duplicate = True),
    Output('activate_cursor_radiated_vertical','on', allow_duplicate=True),
    Output('cursor_data', 'data', allow_duplicate=True),
    Output('emission-radiated-electric-tab','disabled',allow_duplicate = True),
    Output('test-tabs','value', allow_duplicate=True),
    Output('markers', 'data',allow_duplicate = True),
    Output('cursor_output_radiated_vertical', 'children', allow_duplicate=True),
    Output('Div_axes_param_radiated_vertical', 'style'),
    Output('limits_table_radiated_vertical', 'rowData', allow_duplicate=True),
    Output('limits_table_radiated_vertical', 'selectedRows', allow_duplicate=True),
    Output('line_table_radiated_vertical', 'rowData', allow_duplicate=True),
    Output('line_table_radiated_vertical', 'selectedRows', allow_duplicate=True),
    Output('line_table_container_radiated_vertical', 'style', allow_duplicate=True),
    Output('line_table_btn_radiated_vertical', 'children', allow_duplicate=True),
    Output("emission_radiated_param_btn", 'disabled', allow_duplicate=True),
    Output("radiated-electric-submenu", "style",allow_duplicate = True),
    Input('selectedRows_radiated_vertical', 'data'),
    State('emission_radiated_vertical', 'figure'),
    State('emission_radiated_vertical', 'style'),
    State("line_table_radiated_vertical", "selectedRows"),
    State('loading_emission_radiated_vertical', 'display'),
    State('xaxis_emission_radiated_vertical', 'value'),
    State('cursor_list_radiated_vertical', 'options'),
    State('cursor_list_radiated_vertical', 'value'),
    State('emission_radiated_param_btn', 'disabled'),
    State('test-tabs', 'value'),
    State('cursor_output_radiated_vertical', 'children'),
    State('Div_axes_param_radiated_vertical', 'style'),
    State('markers', 'data'),
    State('rowData_test_radiated_vertical', 'data'),
    State('limits_table_radiated_vertical', 'rowData'),
    State('line_table_radiated_vertical', 'rowData'),
    State('line_table_container_radiated_vertical', 'style'),
    State('line_table_btn_radiated_horizontal', 'children'),
    State('cursor_data', 'data'),
    State('activate_cursor_radiated_vertical', 'on'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def figure_radiated_vertical(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on):
    return update_chart(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on)

@app.callback(Output('emission_radiated_horizontal_vertical', "figure", allow_duplicate = True),
    Output('emission_radiated_horizontal_vertical', 'relayoutData',allow_duplicate = True),
    Output('emission_radiated_horizontal_vertical', 'style',allow_duplicate = True),
    Output('loading_emission_radiated_horizontal_vertical', 'display',allow_duplicate = True),
    Output('cursor_list_radiated_horizontal_vertical','options',allow_duplicate = True),
    Output('cursor_list_radiated_horizontal_vertical','value',allow_duplicate = True),
    Output('activate_cursor_radiated_horizontal_vertical','on', allow_duplicate=True),
    Output('cursor_data', 'data', allow_duplicate=True),
    Output('emission-radiated-electric-tab','disabled',allow_duplicate = True),
    Output('test-tabs','value', allow_duplicate=True),
    Output('markers', 'data',allow_duplicate = True),
    Output('cursor_output_radiated_horizontal_vertical', 'children', allow_duplicate=True),
    Output('Div_axes_param_radiated_horizontal_vertical', 'style'),
    Output('limits_table_radiated_horizontal_vertical', 'rowData', allow_duplicate=True),
    Output('limits_table_radiated_horizontal_vertical', 'selectedRows', allow_duplicate=True),
    Output('line_table_radiated_horizontal_vertical', 'rowData', allow_duplicate=True),
    Output('line_table_radiated_horizontal_vertical', 'selectedRows', allow_duplicate=True),
    Output('line_table_container_radiated_horizontal_vertical', 'style', allow_duplicate=True),
    Output('line_table_btn_radiated_horizontal_vertical', 'children', allow_duplicate=True),
    Output("emission_radiated_param_btn", 'disabled', allow_duplicate=True),
    Output("radiated-electric-submenu", "style", allow_duplicate = True),
    Input('selectedRows_radiated_horizontal_vertical', 'data'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    State('emission_radiated_horizontal_vertical', 'style'),
    State("line_table_radiated_horizontal_vertical", "selectedRows"),
    State('loading_emission_radiated_horizontal_vertical', 'display'),
    State('xaxis_emission_radiated_horizontal_vertical', 'value'),
    State('cursor_list_radiated_horizontal_vertical', 'options'),
    State('cursor_list_radiated_horizontal_vertical', 'value'),
    State('emission_radiated_param_btn', 'disabled'),
    State('test-tabs', 'value'),
    State('cursor_output_radiated_horizontal_vertical', 'children'),
    State('Div_axes_param_radiated_horizontal_vertical', 'style'),
    State('markers', 'data'),
    State('rowData_test_radiated_horizontal_vertical', 'data'),
    State('limits_table_radiated_horizontal_vertical', 'rowData'),
    State('line_table_radiated_horizontal_vertical', 'rowData'),
    State('line_table_container_radiated_horizontal_vertical', 'style'),
    State('line_table_btn_radiated_horizontal_vertical', 'children'),
    State('cursor_data', 'data'),
    State('activate_cursor_radiated_horizontal_vertical', 'on'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def figure_radiated_horizontal_vertical(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on):
    return update_chart(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on)

def update_chart(data, figure, figure_style, line_table_selectedRows, loading_display, xaxis_value, cursor_list_options, cursor_list_value, tab_disabled, test_tabs_value, cursor_output_children, Div_axes_param_style, markers_data, rowData_test_data, limit_table_rowData, line_table_rowData, line_table_container_style, line_table_btn_txt, cursor_data, activate_cursor_on):
    if data != [] or figure_style['display'] == 'block':
        selectedRows = []
        if data != []:
            cursor_data = {'left': {}, 'right': {}}
            figure['data'] = []
            figure['layout']['shapes'] = []
            figure['layout']['annotations'] = []
            cursor_output_children = f'ΔFrequency (MHz) = - \n ΔLevel (dBμV/m) = -'
            if activate_cursor_on == False:
                activate_cursor_on = no_update
            else:
                activate_cursor_on = False

            for row in data:
                meta = {'Name': '', 'Type': '', 'Detector': '', 'Bandwidth': '', 'Color': '', 'Suspects': [], 'Finals': [],
                        'Limits': [], 'Cursors': []}
                figure, meta['Suspects'] = plot_suspects(row, figure)
                figure, meta['Finals'] = plot_finals(row, figure)
                meta['Name'] = row["Test name"] + '-' + row["Bandwidth"] + '-' + row['Detector']
                meta['Type'] = 'Line'
                meta['Detector'] = row["Detector"]
                meta['Bandwidth'] = row["Bandwidth"]
                meta['Color'] = [detector_to_color_gradient[row['Detector']][row['Bandwidth']],
                                 'Blue' if row['Detector'] == 'Peak' else 'Red' if row['Detector'] == 'Q-Peak' else 'Green' if row['Detector'] == 'Avg' else None]
                df = pd.read_json(row['Data']['data'])
                color = detector_to_color_gradient[row['Detector']][row['Bandwidth']]
                figure, meta = plot_limits(row, figure, meta, color)
                figure['data'].append(dict(x=df.iloc[:, 0], y=df.iloc[:, 1], mode="lines",
                                           name=row["Test name"] + '-' + row["Bandwidth"] + '-' + row['Detector'],
                                           hoverinfo='none', showlegend=True, meta=meta, visible=True,
                                           line=dict(color=color, dash='solid', width=1),
                                           hovertemplate=f'<b>{row["Test name"]} - {row["Bandwidth"]} - {row["Detector"]}</b><br>' + '<b>Frequency (MHz):</b> %{x:.2f}<br>' + '<b>Level (dBµV/m):</b> %{y:.2f} <extra></extra>'))
                cursor_list_options, cursor_list_value = set_cursor_list(figure)

            if markers_data != []:
                name = []
                for trace in figure['data']:
                    name.append(trace['name'])
                new = []
                for marker in markers_data:
                    if marker['chart_name'] in name:
                        figure['data'].append(marker['trace'])
                        figure['layout']['annotations'].append(marker['annotation'])
                        new.append(marker)
                markers_data = new

            if figure['data'] == []:
                figure_style['display'] = 'none'
                Div_axes_param_style['display'] = 'none'
                loading_display = 'hide'
                line_table_btn_txt = 'Show Line Display Parameters'
                line_table_container_style['display'] = 'none'
            else:
                figure_style['display'] = 'block'
                Div_axes_param_style['display'] = 'block'
                loading_display = 'auto'
                x_max, y_max, x_min, y_min = find_min_max(figure)
                if xaxis_value =='log':
                    x_min, x_max = math.log(x_min, 10), math.log(x_max, 10)
                figure['layout']['xaxis']['range'] = (x_min, x_max)
                figure['layout']['yaxis']['autorange'] = True
                figure = set_color(figure)

            figure['layout']['xaxis']['type'] = xaxis_value

            limit_table_rowData, line_table_rowData, selectedRows = fill_line_table(figure)

        else:
            figure['data'] = []
            figure['layout']['shapes'] = []
            figure['layout']['annotations'] = []

        if figure['data'] == []:
            emission_tab_disabled = True
            radiated_btn_disabled = True
            Div_axes_param_style['display'] = 'none'
            figure_style['display'] = 'none'
            test_tabs_value = ''
            emission_submenu_style = submenu_style
        else:
            emission_tab_disabled = False
            radiated_btn_disabled = False
            Div_axes_param_style['display'] = 'block'
            figure_style['display'] = 'block'
            emission_submenu_style = no_update
            triggered_id = ctx.triggered_id
            if 'radiated' in triggered_id:
                test_tabs_value = 'emission-radiated-electric-tab'
            else:
                test_tabs_value = 'emission-conducted-voltage-tab'
        return figure, {'autosize': True}, figure_style, loading_display, cursor_list_options, cursor_list_value, activate_cursor_on, cursor_data, emission_tab_disabled, test_tabs_value, markers_data, cursor_output_children, Div_axes_param_style, limit_table_rowData, selectedRows, line_table_rowData, line_table_selectedRows, line_table_container_style, line_table_btn_txt, radiated_btn_disabled, emission_submenu_style
    else:
        raise PreventUpdate

def plot_suspects(row, figure):
    meta = []
    if 'suspects' in list(row['Data'].keys()):
        suspects = pd.read_json(row['Data']['suspects'])
        for index, suspect in suspects.iterrows():
            Frequency = suspect["Frequency (MHz)"]
            meta_suspect = {'Name': '', 'Type': ''}
            meta_suspect['Name'] = 'Suspect ' + row["Test name"] + '-' + str(suspect['Subrange']) + '-' + suspect['Polarization']
            meta_suspect['Type'] = 'Suspect'
            Suspect = dict(
                name='Suspect ' + row["Test name"] + '-' + str(suspect['Subrange']) + '-' +
                     suspect["Polarization"],
                x=[Frequency], y=[suspect[3]],
                mode='markers', showlegend=False, visible=True, meta=meta_suspect,
                marker=dict(color='orange', size=10, symbol="x"),
                hovertemplate=f'<b>Suspect {row["Test name"]}</b><br>' + '<b>Frequency (MHz):</b> %{x:.2f}<br>' + '<b>Level (dBµV/m):</b> %{y:.2f} <extra></extra>')
            figure['data'].append(Suspect)
            meta.append('Suspect ' + row["Test name"] + '-' + str(suspect['Subrange']) + '-' +suspect["Polarization"])
    return figure, meta

def plot_finals(row, figure):
    meta = []
    if 'finals' in list(row['Data'].keys()):
        finals = pd.read_json(row['Data']['finals'])
        for index, final in finals.iterrows():
            Frequency = final["Frequency (MHz)"]
            meta_final = {'Name': '', 'Type': ''}
            meta_final['Name'] = 'Suspect ' + row["Test name"] + '-' + str(final['Subrange']) + '-' + final['Polarization']
            meta_final['Type'] = 'Final'
            Final = dict(
                name='Final ' + row["Test name"] + '-' + str(final['Subrange']) + '-' + final["Polarization"],
                x=[Frequency], y=[final[3]],
                mode='markers', showlegend=False, visible=True, meta=meta_final,
                marker=dict(color='green', size=10, symbol="x"),
                hovertemplate=f'<b>Final {row["Test name"]}</b><br>' + '<b>Frequency (MHz):</b> %{x:.2f}<br>' + '<b>Level (dBµV/m):</b> %{y:.2f} <extra></extra>')
            figure['data'].append(Final)
            meta.append('Final ' + row["Test name"] + '-' + str(final['Subrange']) + '-' + final["Polarization"])
    return figure, meta

def plot_limits(selectedRowsData,figure, meta, color):
    data, limit = pd.read_json(selectedRowsData['Data']['data']), pd.read_json(selectedRowsData['Data']['Limit Definition'])
    limit_filtered = limit[((limit['Detector'] == 'QPEAK') | (limit['Detector'] == selectedRowsData['Detector'].upper())) & ((limit['Freq Start'] >= data.iloc[0, 0]) & (limit['Freq Stop'] <= data.iloc[-1, 0]))].drop_duplicates()
    for index, row in limit_filtered.iterrows():
        if selectedRowsData['Test Type'] == 'Radiated Electric Emission':
            level_start = limit_filtered[(limit_filtered['Freq Start'] == row['Freq Start']) & (limit_filtered['Freq Stop'] == row['Freq Stop']) & (limit_filtered['Detector'] == row['Detector']) & (limit_filtered['Level Start'] != row['Level Start'])].iloc[0, 1]
            level_stop = limit_filtered[(limit_filtered['Freq Start'] == row['Freq Start']) & (limit_filtered['Freq Stop'] == row['Freq Stop']) & (limit_filtered['Detector'] == row['Detector']) & (limit_filtered['Level Start'] != row['Level Start'])].iloc[0, 3]
            if row['Level Start'] > level_start and row['Level Stop'] > level_stop:
                name = "Domestic Limit" + '-' + selectedRowsData['Limit']
            else:
                name = "Industrial Limit" + '-' + selectedRowsData['Limit']
        else:
            name = "Limit" + '-' + selectedRowsData['Limit']
        meta_limit = {'Name': '', 'Type': ''}
        meta_limit['Name'] = name
        meta_limit['Type'] = 'Limit'
        figure['data'].append(go.Scatter(x=[row['Freq Start'], row['Freq Start'], row['Freq Stop'], row['Freq Stop']],
                                         y=[row['Level Start'] - 0.15, row['Level Start'] + 0.15, row['Level Stop'] + 0.15,
                                            row['Level Stop'] - 0.15],
                                         name=name, showlegend=False,
                                         visible=True, fill="toself",
                                         mode='text', fillcolor='red',
                                         hovertemplate='', hoverinfo='text', text=None, meta=meta_limit))
        meta['Limits'].append(name)
    return figure, meta

def set_cursor_list(figure):
    cursor_options = []
    cursor_value = None
    for trace in figure['data']:
        if 'Suspect' not in trace['name'] and 'Limit' not in trace['name'] and 'Marker' not in trace['name']:
            cursor_options.append(trace['meta']['Name'])
    if cursor_options != []:
        cursor_value = cursor_options[0]
    return cursor_options, cursor_value

def returnSum(myDict):
    list = []
    for i in myDict:
        list = list + myDict[i]

    return list

def set_color(figure):
    color_to_color_gradient = {'Blue': {}, 'Orange': {}, 'Green': {}, 'Red': {}, 'Purple': {}, 'Brown': {}, 'Pink': {},
                               'Gray': {}}
    for index, trace in enumerate(figure['data']):
        if 'Limit' not in trace['name'] and 'Suspect' not in trace['name'] and 'Marker' not in trace['name']:
            if trace['meta']['Color'][0] in color_to_color_gradient[trace['meta']['Color'][1]]:
                color_to_color_gradient[trace['meta']['Color'][1]][trace['meta']['Color'][0]].append(index)
            else:
                color_to_color_gradient[trace['meta']['Color'][1]][trace['meta']['Color'][0]] = [index]

    key_index = []
    for color, list_color in color_to_color_gradient.items():
        val = returnSum(list_color)
        if len(val) > 1:
            for item_init in val:
                for item in val:
                    if item_init != item:
                        if len(set(figure['data'][item_init]['x']) & set(figure['data'][item]['x'])) > 1:
                            key_index.append(item_init)
                            key_index.append(item)
                            break

            if key_index != []:
                key_index = list(dict.fromkeys(key_index))
                color_codes = generate_gradient(len(key_index), Gradient[color])
                for index, key in enumerate(key_index):
                    figure['data'][key]['line']['color'] = color_codes[index]
                    figure['data'][key]['meta']['Color'][0] = color_codes[index]
                    # for trace in figure['data']:
                    #     if trace['name'] in figure['data'][key]['meta']['Limits']:
                    #         trace['fillcolor'] = color_codes[index]
    return figure

def generate_gradient(n, color):
    from matplotlib import cm
    color = cm.get_cmap(color)
    return [f'rgb({r*255:.0f},{g*255:.0f},{b*255:.0f})' for r, g, b, a in color(np.linspace(0.5, 0.9, n))]

def fill_line_table(figure):
    rowData_limit = []
    rowData_line = []
    selectedRows = {"ids":[]}
    if figure:
        for trace in figure['data']:
            name = trace['meta']['Name']
            if trace['meta']['Type'] == 'Limit' and name not in list(map(lambda d: d["Name"], rowData_limit)):
                rowData_limit.append({
                            'Name': name,
                            'disabled': 'False'})
            if trace['meta']['Type'] == 'Line':
                color = 'Blue' if trace['meta']['Detector'] == 'Peak' else 'Red' if trace['meta']['Detector'] == 'Q-Peak' else 'Green' if trace['meta']['Detector'] == 'Avg' else None
                rowData_line.append({
                            'Name':name,
                            'Color':color,
                            'Width':1,
                            'Type':'solid'})
        for i in range(len(rowData_limit)):
            selectedRows['ids'].append(str(i))
    return rowData_limit, rowData_line, selectedRows

@app.callback(
    Output('emission_conducted_phase', 'figure', allow_duplicate=True),
    Output('emission_conducted_phase', 'restyleData', allow_duplicate=True),
    Output('input_x_min_conducted_phase', 'value', allow_duplicate=True),
    Output('input_x_max_conducted_phase', 'value', allow_duplicate=True),
    Output('suspectsTable-conducted', 'rowData', allow_duplicate=True),
    Output('suspectsTable-conducted', 'selectedRows', allow_duplicate=True),
    Output('finalsTable-conducted', 'rowData', allow_duplicate=True),
    Output('finalsTable-conducted', 'selectedRows', allow_duplicate=True),
    Output('limits_table_conducted_phase', 'rowData', allow_duplicate=True),
    Output('limits_table_conducted_phase', 'selectedRows', allow_duplicate=True),
    Input('emission_conducted_phase', 'restyleData'),
    State('emission_conducted_phase', 'figure'),
    State('markers', 'data'),
    State('activate-marker_conducted', 'on'),
    State('suspectsTable-conducted', 'rowData'),
    State('finalsTable-conducted', 'rowData'),
    State('limits_table_conducted_phase', 'rowData'),
    State('limits_table_conducted_phase', 'selectedRows'),
    prevent_initial_call=True)

def update_conducted_phase(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected):
    return update(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected)

@app.callback(
    Output('emission_conducted_wire', 'figure', allow_duplicate=True),
    Output('emission_conducted_wire', 'restyleData', allow_duplicate=True),
    Output('input_x_min_conducted_wire', 'value', allow_duplicate=True),
    Output('input_x_max_conducted_wire', 'value', allow_duplicate=True),
    Output('suspectsTable-conducted', 'rowData', allow_duplicate=True),
    Output('suspectsTable-conducted', 'selectedRows', allow_duplicate=True),
    Output('finalsTable-conducted', 'rowData', allow_duplicate=True),
    Output('finalsTable-conducted', 'selectedRows', allow_duplicate=True),
    Output('limits_table_conducted_wire', 'rowData', allow_duplicate=True),
    Output('limits_table_conducted_wire', 'selectedRows', allow_duplicate=True),
    Input('emission_conducted_wire', 'restyleData'),
    State('emission_conducted_wire', 'figure'),
    State('markers', 'data'),
    State('activate-marker_conducted', 'on'),
    State('suspectsTable-conducted', 'rowData'),
    State('finalsTable-conducted', 'rowData'),
    State('limits_table_conducted_wire', 'rowData'),
    State('limits_table_conducted_wire', 'selectedRows'),
    prevent_initial_call=True)

def update_conducted_wire(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected):
    return update(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected)

@app.callback(
    Output('emission_radiated_horizontal', 'figure', allow_duplicate=True),
    Output('emission_radiated_horizontal', 'restyleData', allow_duplicate=True),
    Output('input_x_min_radiated_horizontal', 'value', allow_duplicate=True),
    Output('input_x_max_radiated_horizontal', 'value', allow_duplicate=True),
    Output('suspectsTable-radiated', 'rowData', allow_duplicate=True),
    Output('suspectsTable-radiated', 'selectedRows', allow_duplicate=True),
    Output('finalsTable-radiated', 'rowData', allow_duplicate=True),
    Output('finalsTable-radiated', 'selectedRows', allow_duplicate=True),
    Output('limits_table_radiated_horizontal', 'rowData', allow_duplicate=True),
    Output('limits_table_radiated_horizontal', 'selectedRows', allow_duplicate=True),
    Input('emission_radiated_horizontal', 'restyleData'),
    State('emission_radiated_horizontal', 'figure'),
    State('markers', 'data'),
    State('activate-marker_radiated', 'on'),
    State('suspectsTable-radiated', 'rowData'),
    State('finalsTable-radiated', 'rowData'),
    State('limits_table_radiated_horizontal', 'rowData'),
    State('limits_table_radiated_horizontal', 'selectedRows'),
    prevent_initial_call=True)

def update_radiated_horizontal(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected):
    return update(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected)

@app.callback(
    Output('emission_radiated_vertical', 'figure', allow_duplicate=True),
    Output('emission_radiated_vertical', 'restyleData', allow_duplicate=True),
    Output('input_x_min_radiated_vertical', 'value', allow_duplicate=True),
    Output('input_x_max_radiated_vertical', 'value', allow_duplicate=True),
    Output('suspectsTable-radiated', 'rowData', allow_duplicate=True),
    Output('suspectsTable-radiated', 'selectedRows', allow_duplicate=True),
    Output('finalsTable-radiated', 'rowData', allow_duplicate=True),
    Output('finalsTable-radiated', 'selectedRows', allow_duplicate=True),
    Output('limits_table_radiated_vertical', 'rowData', allow_duplicate=True),
    Output('limits_table_radiated_vertical', 'selectedRows', allow_duplicate=True),
    Input('emission_radiated_vertical', 'restyleData'),
    State('emission_radiated_vertical', 'figure'),
    State('markers', 'data'),
    State('activate-marker_radiated', 'on'),
    State('suspectsTable-radiated', 'rowData'),
    State('finalsTable-radiated', 'rowData'),
    State('limits_table_radiated_vertical', 'rowData'),
    State('limits_table_radiated_vertical', 'selectedRows'),
    prevent_initial_call=True)

def update_radiated_vertical(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected):
    return update(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected)

@app.callback(
    Output('emission_radiated_horizontal_vertical', 'figure', allow_duplicate=True),
    Output('emission_radiated_horizontal_vertical', 'restyleData', allow_duplicate=True),
    Output('input_x_min_radiated_horizontal_vertical', 'value', allow_duplicate=True),
    Output('input_x_max_radiated_horizontal_vertical', 'value', allow_duplicate=True),
    Output('suspectsTable-radiated', 'rowData', allow_duplicate=True),
    Output('suspectsTable-radiated', 'selectedRows', allow_duplicate=True),
    Output('finalsTable-radiated', 'rowData', allow_duplicate=True),
    Output('finalsTable-radiated', 'selectedRows', allow_duplicate=True),
    Output('limits_table_radiated_horizontal_vertical', 'rowData', allow_duplicate=True),
    Output('limits_table_radiated_horizontal_vertical', 'selectedRows', allow_duplicate=True),
    Input('emission_radiated_horizontal_vertical', 'restyleData'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    State('markers', 'data'),
    State('activate-marker_radiated', 'on'),
    State('suspectsTable-radiated', 'rowData'),
    State('finalsTable-radiated', 'rowData'),
    State('limits_table_radiated_horizontal_vertical', 'rowData'),
    State('limits_table_radiated_horizontal_vertical', 'selectedRows'),
    prevent_initial_call=True)

def update_radiated_horizontal_vertical(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected):
    return update(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected)

def update(legend, figure, markers, activate_markers, suspectsTable_rowData, finalsTable_rowData, limitsTable_rowData, limitsTable_selected):
    if legend != []:
        legend_index = legend[1][0]
        meta = figure['data'][legend_index]['meta']
        visible = legend[0]['visible'][0]

        for trace in figure['data']:
            if trace['name'] in meta['Suspects']:
                trace['visible'] = visible

        select_suspect = []
        if suspectsTable_rowData != []:
            for suspect in suspectsTable_rowData:
                if suspect["Test Name"] == figure['data'][legend_index]['name'].split('-')[0]:
                    if suspect['disabled'] == 'False':
                        suspect['disabled'] = 'True'
                    else:
                        suspect['disabled'] = 'False'
                        select_suspect.append(suspect)
                else:
                    select_suspect.append(suspect)

        select_final = []
        if finalsTable_rowData != []:
            for final in finalsTable_rowData:
                if final["Test Name"] == figure['data'][legend_index]['name'].split('-')[0]:
                    if final['disabled'] == 'False':
                        final['disabled'] = 'True'
                    else:
                        final['disabled'] = 'False'
                        select_final.append(final)
                else:
                    select_final.append(final)
        new_limitsTable_selected = copy.deepcopy(limitsTable_selected)
        new_limitsTable_rowData = copy.deepcopy(limitsTable_rowData)
        for limit in new_limitsTable_rowData:
            if limit['Name'] in meta['Limits']:
                if limit['disabled'] == 'False':
                    list = []
                    for trace in figure['data']:
                        if trace['meta']['Type'] == 'Line' and limit['Name'] in trace['meta']['Limits']:
                            list.append(trace['visible'])
                    if True not in list:
                        limit['disabled'] = 'True'
                else:
                    limit['disabled'] = 'False'
                    if limit not in new_limitsTable_selected:
                        new_limitsTable_selected.append(limit)
        if new_limitsTable_rowData == limitsTable_rowData:
            new_limitsTable_rowData = no_update
        if new_limitsTable_selected == limitsTable_selected:
            new_limitsTable_selected = no_update

        if markers != []:
            for marker in markers:
                if marker['line_index'] == legend_index:
                    for trace in figure['data']:
                        if marker['name'] == trace['name'] and activate_markers == True:
                            trace['visible'] = visible
                            break
                    for annotation in figure['layout']['annotations']:
                        if marker['name'] == annotation['name'] and activate_markers == True:
                            if visible == 'legendonly':
                                annotation['visible'] = False
                            else:
                                annotation['visible'] = True
                            break

        x_min, x_max, y_min, y_max = no_update, no_update, no_update, no_update
        for trace in figure['data']:
            if trace['visible'] == True and trace['meta']['Type'] == 'Line':
                x_max_data, y_max, x_min_data, y_min = find_min_max(figure)
                if figure['layout']['xaxis']['type'] == 'log':
                    x_min, x_max = math.log10(x_min_data), math.log10(x_max_data)
                else:
                    x_min, x_max = x_min_data, x_max_data
                figure['layout']['xaxis']['range'] = [x_min, x_max]
                figure['layout']['yaxis']['autorange'] = True
                x_min, x_max, y_min, y_max = round(x_min_data, 2), round(x_max_data, 2), round(y_min, 2), round(y_max, 2)
                break
        return figure, None, x_min, x_max, suspectsTable_rowData, select_suspect, finalsTable_rowData, select_final, new_limitsTable_rowData, new_limitsTable_selected
    else:
        raise PreventUpdate

@app.callback(Output('emission_conducted_phase', 'figure', allow_duplicate = True),
    Input('limits_table_conducted_phase', 'selectedRows'),
    State('emission_conducted_phase', 'figure'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def display_limit_conducted_phase(selectedRows, figure):
    return display_limit_tab (selectedRows, figure)

@app.callback(Output('emission_conducted_wire', 'figure', allow_duplicate = True),
    Input('limits_table_conducted_wire', 'selectedRows'),
    State('emission_conducted_wire', 'figure'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def display_limit_conducted_wire(selectedRows, figure):
    return display_limit_tab (selectedRows, figure)

@app.callback(Output('emission_radiated_horizontal', 'figure', allow_duplicate = True),
    Input('limits_table_radiated_horizontal', 'selectedRows'),
    State('emission_radiated_horizontal', 'figure'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def display_limit_radiated_horizontal(selectedRows, figure):
    return display_limit_tab (selectedRows, figure)

@app.callback(Output('emission_radiated_vertical', 'figure', allow_duplicate = True),
    Input('limits_table_radiated_vertical', 'selectedRows'),
    State('emission_radiated_vertical', 'figure'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def display_limit_radiated_vertical(selectedRows, figure):
    return display_limit_tab (selectedRows, figure)

@app.callback(Output('emission_radiated_horizontal_vertical', 'figure', allow_duplicate = True),
    Input('limits_table_radiated_horizontal_vertical', 'selectedRows'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def display_limit_radiated_horizontal_vertical(selectedRows, figure):
    return display_limit_tab (selectedRows, figure)

def display_limit_tab(selectedRows, figure):
    if 'ids' not in selectedRows and figure['data'] != []:
        names = []
        for row in selectedRows:
            names.append(row['Name'])
        for trace in figure['data']:
            if trace['meta']['Type'] == 'Limit':
                if trace['name'] in names:
                    trace['visible'] = True
                else:
                    trace['visible'] = False
        return figure
    else:
        raise PreventUpdate

@app.callback(Output('emission_conducted_phase', 'figure', allow_duplicate = True),
    Input('line_table_conducted_phase', 'cellValueChanged'),
    State('emission_conducted_phase', 'figure'),
    State('line_table_conducted_phase', 'virtualRowData'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def update_line_conducted_phase(cell, figure, line_table):
    return update_line(cell, figure, line_table)

@app.callback(Output('emission_conducted_wire', 'figure', allow_duplicate = True),
    Input('line_table_conducted_wire', 'cellValueChanged'),
    State('emission_conducted_wire', 'figure'),
    State('line_table_conducted_wire', 'virtualRowData'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def update_line_conducted_wire(cell, figure, line_table):
    return update_line(cell, figure, line_table)

@app.callback(Output('emission_radiated_horizontal', 'figure', allow_duplicate = True),
    Input('line_table_radiated_horizontal', 'cellValueChanged'),
    State('emission_radiated_horizontal', 'figure'),
    State('line_table_radiated_horizontal', 'virtualRowData'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def update_line_radiated_horizontal(cell, figure, line_table):
    return update_line(cell, figure, line_table)

@app.callback(Output('emission_radiated_vertical', 'figure', allow_duplicate = True),
    Input('line_table_radiated_vertical', 'cellValueChanged'),
    State('emission_radiated_vertical', 'figure'),
    State('line_table_radiated_vertical', 'virtualRowData'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def update_line_radiated_vertical(cell, figure, line_table):
    return update_line(cell, figure, line_table)

@app.callback(Output('emission_radiated_horizontal_vertical', 'figure', allow_duplicate = True),
    Input('line_table_radiated_horizontal_vertical', 'cellValueChanged'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    State('line_table_radiated_horizontal_vertical', 'virtualRowData'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def update_line_radiated_horizontal_vertical(cell, figure, line_table):
    return update_line(cell, figure, line_table)

def update_line(cell, figure, line_table):
    row = cell[0]['data']
    for trace in figure['data']:
        if trace['meta']['Name'] == row['Name']:
            Color = trace['line']['color']
            color_list = generate_gradient(3, Gradient[row['Color']])
            trace['line']['color'] = color_list[0] if trace['meta']['Bandwidth'] == '9 kHz' else color_list[1] if trace['meta']['Bandwidth'] == '120 kHz' or  trace['meta']['Bandwidth'] == '200 kHz' else color_list[2] if trace['meta']['Bandwidth'] == '1 MHz' else None
            trace['meta']['Color'] = [trace['line']['color'], row['Color']]
            trace['line']['width'] = row['Width']
            trace['line']['dash'] = row['Type']
            # for trace_2 in figure['data']:
            #     if trace_2['name'] in trace['meta']['Limits']:
            #         trace_2['fillcolor'] = trace['line']['color']
            set_color(figure)
            if 'shapes' in figure['layout'] and 'annotations' in figure['layout']:
                for i in range(len(figure['layout']['shapes'])):
                    if figure['layout']['shapes'][i]['line']['color'] == Color:
                        figure['layout']['shapes'][i]['line']['color'] = trace['line']['color']
                        for j in range(len(figure['layout']['annotations'])):
                            if figure['layout']['shapes'][i]['name'] == figure['layout']['annotations'][j]['name']:
                                figure['layout']['annotations'][j]['bgcolor'] = trace['line']['color']
            figure['data'][figure['data'].index(trace)] = trace
            emphasize_chart(line_table, figure)
    return figure

@app.callback(Output('emission_conducted_phase', 'figure', allow_duplicate = True),
    Input('line_table_conducted_phase', 'virtualRowData'),
    State('emission_conducted_phase', 'figure'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def emphasize_chart_conducted_phase(line_table, figure):
    if line_table:
        result = emphasize_chart(line_table, figure)
        return result
    else:
        raise PreventUpdate

@app.callback(Output('emission_conducted_wire', 'figure', allow_duplicate = True),
    Input('line_table_conducted_wire', 'virtualRowData'),
    State('emission_conducted_wire', 'figure'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def emphasize_chart_conducted_wire(line_table, figure):
    if line_table:
        return emphasize_chart(line_table, figure)
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_horizontal', 'figure', allow_duplicate = True),
    Input('line_table_radiated_horizontal', 'virtualRowData'),
    State('emission_radiated_horizontal', 'figure'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def emphasize_chart_radiated_horizontal(line_table, figure):
    if line_table:
        return emphasize_chart(line_table, figure)
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_vertical', 'figure', allow_duplicate = True),
    Input('line_table_radiated_vertical', 'virtualRowData'),
    State('emission_radiated_vertical', 'figure'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def emphasize_chart_radiated_vertical(line_table, figure):
    if line_table:
        return emphasize_chart(line_table, figure)
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_horizontal_vertical', 'figure', allow_duplicate = True),
    Input('line_table_radiated_horizontal_vertical', 'virtualRowData'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def emphasize_chart_radiated_horizontal_vertical(line_table, figure):
    if line_table:
        return emphasize_chart(line_table, figure)
    else:
        raise PreventUpdate

def returnSum(myDict):
    list = []
    for i in myDict:
        list = list + myDict[i]
    return list

def emphasize_chart(line_table, figure):
    color_to_color_gradient = {'Blue': {}, 'Orange': {}, 'Green': {}, 'Red': {}, 'Purple': {}, 'Brown': {}, 'Pink': {},
                               'Gray': {}}
    for index, trace in enumerate(figure['data']):
        if 'Limit' not in trace['name'] and 'Suspect' not in trace['name'] and 'Marker' not in trace['name']:
            if trace['meta']['Color'][0] in color_to_color_gradient[trace['meta']['Color'][1]]:
                color_to_color_gradient[trace['meta']['Color'][1]][trace['meta']['Color'][0]].append(index)
            else:
                color_to_color_gradient[trace['meta']['Color'][1]][trace['meta']['Color'][0]] = [index]

    key_index = []
    for color, list_color in color_to_color_gradient.items():
        val = returnSum(list_color)
        if len(val) > 1:
            for item_init in val:
                for item in val:
                    if item_init != item:
                        if len(set(figure['data'][item_init]['x']) & set(figure['data'][item]['x'])) > 1:
                            key_index.append(item_init)
                            key_index.append(item)
                            break

    if key_index != []:
        color_order = {}
        for color, color_list in color_to_color_gradient.items():
            for key in list(color_list.keys()):
                for index in color_list[key]:
                    if index in key_index:
                        code_list = key.replace('rgb(', '').replace(')', '').split(',')
                        b = [int(item) for item in code_list]
                        sum_code = sum(b)
                        color_order[key] = sum_code
        color_order = dict(sorted(color_order.items(), key=lambda item: item[1]))
        color_order = list(color_order.keys())
        index = 0
        for row in line_table:
            for trace_index, trace in enumerate(figure['data']):
                if row['Name'] == trace['meta']['Name'] and trace_index in key_index:
                    trace['line']['color'] = color_order[index]
                    trace['meta']['Color'][0] = color_order[index]

                    for cursor in trace['meta']['Cursors']:
                        for shape in figure['layout']['shapes']:
                            if shape['name'] == cursor:
                                shape['line']['color'] = trace['meta']['Color'][0]
                        for annotation in figure['layout']['annotations']:
                            if annotation['name'] == cursor:
                                annotation['bgcolor'] = trace['meta']['Color'][0]

                    # for trace in figure['data']:
                    #     if trace['name'] in figure['data'][trace_index]['meta']['Limits']:
                    #         trace['fillcolor'] = color_order[index]
                    index += 1

    return figure

@app.callback(Output('emission_conducted_phase', 'figure', allow_duplicate = True),
    Output('emission_conducted_phase', 'relayoutData', allow_duplicate = True),
    Output('input_x_min_conducted_phase', 'value', allow_duplicate = True),
    Output('input_x_max_conducted_phase', 'value', allow_duplicate = True),
    Output('input_y_min_conducted_phase', 'value', allow_duplicate = True),
    Output('input_y_max_conducted_phase', 'value', allow_duplicate = True),
    Input('emission_conducted_phase', 'relayoutData'),
    Input('input_x_min_conducted_phase', 'n_blur'),
    Input('input_x_max_conducted_phase', 'n_blur'),
    Input('input_y_min_conducted_phase', 'n_blur'),
    Input('input_y_max_conducted_phase', 'n_blur'),
    Input('input_x_min_conducted_phase', 'n_submit'),
    Input('input_x_max_conducted_phase', 'n_submit'),
    Input('input_y_min_conducted_phase', 'n_submit'),
    Input('input_y_max_conducted_phase', 'n_submit'),
    Input('input_x_min_conducted_phase', 'value'),
    Input('input_x_max_conducted_phase', 'value'),
    Input('input_y_min_conducted_phase', 'value'),
    Input('input_y_max_conducted_phase', 'value'),
    State('emission_conducted_phase', 'figure'),
    State('xaxis_emission_conducted_phase', 'value'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def axes_param_conducted_phase(relayoutData, n_blur_x_min, n_blur_x_max, n_blur_y_min, n_blur_y_max, n_submit_x_min, n_submit_x_max, n_submit_y_min, n_submit_y_max, x_min, x_max, y_min, y_max, figure, log):
    if figure['data'] != []:
        return axes_param(relayoutData, x_min, x_max, y_min, y_max, figure, log)
    else:
        raise PreventUpdate

@app.callback(Output('emission_conducted_wire', 'figure', allow_duplicate = True),
    Output('emission_conducted_wire', 'relayoutData', allow_duplicate = True),
    Output('input_x_min_conducted_wire', 'value', allow_duplicate = True),
    Output('input_x_max_conducted_wire', 'value', allow_duplicate = True),
    Output('input_y_min_conducted_wire', 'value', allow_duplicate = True),
    Output('input_y_max_conducted_wire', 'value', allow_duplicate = True),
    Input('emission_conducted_wire', 'relayoutData'),
    Input('input_x_min_conducted_wire', 'n_blur'),
    Input('input_x_max_conducted_wire', 'n_blur'),
    Input('input_y_min_conducted_wire', 'n_blur'),
    Input('input_y_max_conducted_wire', 'n_blur'),
    Input('input_x_min_conducted_wire', 'n_submit'),
    Input('input_x_max_conducted_wire', 'n_submit'),
    Input('input_y_min_conducted_wire', 'n_submit'),
    Input('input_y_max_conducted_wire', 'n_submit'),
    Input('input_x_min_conducted_wire', 'value'),
    Input('input_x_max_conducted_wire', 'value'),
    Input('input_y_min_conducted_wire', 'value'),
    Input('input_y_max_conducted_wire', 'value'),
    State('emission_conducted_wire', 'figure'),
    State('xaxis_emission_conducted_wire', 'value'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def axes_param_conducted_wire(relayoutData, n_blur_x_min, n_blur_x_max, n_blur_y_min, n_blur_y_max, n_submit_x_min, n_submit_x_max, n_submit_y_min, n_submit_y_max, x_min, x_max, y_min, y_max, figure, log):
    if figure['data'] != []:
        return axes_param(relayoutData, x_min, x_max, y_min, y_max, figure, log)
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_horizontal', 'figure', allow_duplicate = True),
    Output('emission_radiated_horizontal', 'relayoutData', allow_duplicate = True),
    Output('input_x_min_radiated_horizontal', 'value', allow_duplicate = True),
    Output('input_x_max_radiated_horizontal', 'value', allow_duplicate = True),
    Output('input_y_min_radiated_horizontal', 'value', allow_duplicate = True),
    Output('input_y_max_radiated_horizontal', 'value', allow_duplicate = True),
    Input('emission_radiated_horizontal', 'relayoutData'),
    Input('input_x_min_radiated_horizontal', 'n_blur'),
    Input('input_x_max_radiated_horizontal', 'n_blur'),
    Input('input_y_min_radiated_horizontal', 'n_blur'),
    Input('input_y_max_radiated_horizontal', 'n_blur'),
    Input('input_x_min_radiated_horizontal', 'n_submit'),
    Input('input_x_max_radiated_horizontal', 'n_submit'),
    Input('input_y_min_radiated_horizontal', 'n_submit'),
    Input('input_y_max_radiated_horizontal', 'n_submit'),
    Input('input_x_min_radiated_horizontal', 'value'),
    Input('input_x_max_radiated_horizontal', 'value'),
    Input('input_y_min_radiated_horizontal', 'value'),
    Input('input_y_max_radiated_horizontal', 'value'),
    State('emission_radiated_horizontal', 'figure'),
    State('xaxis_emission_radiated_horizontal', 'value'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def axes_param_radiated_horizontal(relayoutData, n_blur_x_min, n_blur_x_max, n_blur_y_min, n_blur_y_max, n_submit_x_min, n_submit_x_max, n_submit_y_min, n_submit_y_max, x_min, x_max, y_min, y_max, figure, log):
    if figure['data'] != []:
        return axes_param(relayoutData, x_min, x_max, y_min, y_max, figure, log)
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_vertical', 'figure', allow_duplicate = True),
    Output('emission_radiated_vertical', 'relayoutData', allow_duplicate = True),
    Output('input_x_min_radiated_vertical', 'value', allow_duplicate = True),
    Output('input_x_max_radiated_vertical', 'value', allow_duplicate = True),
    Output('input_y_min_radiated_vertical', 'value', allow_duplicate = True),
    Output('input_y_max_radiated_vertical', 'value', allow_duplicate = True),
    Input('emission_radiated_vertical', 'relayoutData'),
    Input('input_x_min_radiated_vertical', 'n_blur'),
    Input('input_x_max_radiated_vertical', 'n_blur'),
    Input('input_y_min_radiated_vertical', 'n_blur'),
    Input('input_y_max_radiated_vertical', 'n_blur'),
    Input('input_x_min_radiated_vertical', 'n_submit'),
    Input('input_x_max_radiated_vertical', 'n_submit'),
    Input('input_y_min_radiated_vertical', 'n_submit'),
    Input('input_y_max_radiated_vertical', 'n_submit'),
    Input('input_x_min_radiated_vertical', 'value'),
    Input('input_x_max_radiated_vertical', 'value'),
    Input('input_y_min_radiated_vertical', 'value'),
    Input('input_y_max_radiated_vertical', 'value'),
    State('emission_radiated_vertical', 'figure'),
    State('xaxis_emission_radiated_vertical', 'value'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def axes_param_radiated_vertical(relayoutData, n_blur_x_min, n_blur_x_max, n_blur_y_min, n_blur_y_max, n_submit_x_min, n_submit_x_max, n_submit_y_min, n_submit_y_max, x_min, x_max, y_min, y_max, figure, log):
    if figure['data'] != []:
        return axes_param(relayoutData, x_min, x_max, y_min, y_max, figure, log)
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_horizontal_vertical', 'figure', allow_duplicate = True),
    Output('emission_radiated_horizontal_vertical', 'relayoutData', allow_duplicate = True),
    Output('input_x_min_radiated_horizontal_vertical', 'value', allow_duplicate = True),
    Output('input_x_max_radiated_horizontal_vertical', 'value', allow_duplicate = True),
    Output('input_y_min_radiated_horizontal_vertical', 'value', allow_duplicate = True),
    Output('input_y_max_radiated_horizontal_vertical', 'value', allow_duplicate = True),
    Input('emission_radiated_horizontal_vertical', 'relayoutData'),
    Input('input_x_min_radiated_horizontal_vertical', 'n_blur'),
    Input('input_x_max_radiated_horizontal_vertical', 'n_blur'),
    Input('input_y_min_radiated_horizontal_vertical', 'n_blur'),
    Input('input_y_max_radiated_horizontal_vertical', 'n_blur'),
    Input('input_x_min_radiated_horizontal_vertical', 'n_submit'),
    Input('input_x_max_radiated_horizontal_vertical', 'n_submit'),
    Input('input_y_min_radiated_horizontal_vertical', 'n_submit'),
    Input('input_y_max_radiated_horizontal_vertical', 'n_submit'),
    Input('input_x_min_radiated_horizontal_vertical', 'value'),
    Input('input_x_max_radiated_horizontal_vertical', 'value'),
    Input('input_y_min_radiated_horizontal_vertical', 'value'),
    Input('input_y_max_radiated_horizontal_vertical', 'value'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    State('xaxis_emission_radiated_horizontal_vertical', 'value'),
    prevent_initial_call=True,
    cancel=[Input("Test-table", "selectedRows")])

def axes_param_radiated_horizontal_vertical(relayoutData, n_blur_x_min, n_blur_x_max, n_blur_y_min, n_blur_y_max, n_submit_x_min, n_submit_x_max, n_submit_y_min, n_submit_y_max, x_min, x_max, y_min, y_max, figure, log):
    if figure['data'] != []:
        return axes_param(relayoutData, x_min, x_max, y_min, y_max, figure, log)
    else:
        raise PreventUpdate

def axes_param (relayoutData, x_min, x_max, y_min, y_max, figure, log):
    triggered_id = ctx.triggered_id
    if relayoutData and 'annotations' not in list(relayoutData.keys())[0] or triggered_id == 'input_x_min_conducted_phase' or triggered_id == 'input_x_max_conducted_phase' or triggered_id == 'input_y_min_conducted_phase' or triggered_id == 'input_y_max_conducted_phase' or triggered_id == 'input_x_min_conducted_wire' or triggered_id == 'input_x_max_conducted_wire' or triggered_id == 'input_y_min_conducted_wire' or triggered_id == 'input_y_max_conducted_wire' or triggered_id == 'input_x_min_radiated_horizontal' or triggered_id == 'input_x_max_radiated_horizontal' or triggered_id == 'input_y_min_radiated_horizontal' or triggered_id == 'input_y_max_radiated_horizontal' or triggered_id == 'input_x_min_radiated_vertical' or triggered_id == 'input_x_max_radiated_vertical' or triggered_id == 'input_y_min_radiated_vertical' or triggered_id == 'input_y_max_radiated_vertical' or triggered_id == 'input_x_min_radiated_horizontal_vertical' or triggered_id == 'input_x_max_radiated_horizontal_vertical' or triggered_id == 'input_y_min_radiated_horizontal_vertical' or triggered_id == 'input_y_max_radiated_horizontal_vertical':
        if relayoutData and 'yaxis.autorange' in list(relayoutData.keys()) or relayoutData and 'autosize' in list(relayoutData.keys())[0]:
            x_max, y_max, x_min, y_min = find_min_max(figure)
            if log == 'log':
                x_min, x_max = math.log(x_min,10), math.log(x_max,10)
            figure['layout']['xaxis']['range'] = (x_min, x_max)
            if log == 'log':
                x_min = 10 ** x_min
                x_max = 10 ** x_max
            y_min, y_max = figure['layout']['yaxis']['range']
            x_min, x_max, y_min, y_max = round(x_min, 2), round(x_max, 2), round(y_min, 2), round(y_max, 2)

        elif triggered_id == 'emission_conducted_phase' or triggered_id == 'emission_conducted_wire' or triggered_id == 'emission_radiated_horizontal' or triggered_id == 'emission_radiated_vertical' or triggered_id == 'emission_radiated_horizontal_vertical':
            figure, x_min, x_max, y_min, y_max = get_axes_range(figure, log, relayoutData)

        elif triggered_id == 'input_x_min_conducted_phase' or triggered_id == 'input_x_max_conducted_phase' or triggered_id == 'input_y_min_conducted_phase' or triggered_id == 'input_y_max_conducted_phase' or triggered_id == 'input_x_min_conducted_wire' or triggered_id == 'input_x_max_conducted_wire' or triggered_id == 'input_y_min_conducted_wire' or triggered_id == 'input_y_max_conducted_wire' or triggered_id == 'input_x_min_radiated_horizontal' or triggered_id == 'input_x_max_radiated_horizontal' or triggered_id == 'input_y_min_radiated_horizontal' or triggered_id == 'input_y_max_radiated_horizontal' or triggered_id == 'input_x_min_radiated_vertical' or triggered_id == 'input_x_max_radiated_vertical' or triggered_id == 'input_y_min_radiated_vertical' or triggered_id == 'input_y_max_radiated_vertical' or triggered_id == 'input_x_min_radiated_horizontal_vertical' or triggered_id == 'input_x_max_radiated_horizontal_vertical' or triggered_id == 'input_y_min_radiated_horizontal_vertical' or triggered_id == 'input_y_max_radiated_horizontal_vertical':
            figure, x_min, x_max, y_min, y_max = Set_axes_range(x_min, x_max, y_min, y_max, figure, log)

        figure['layout']['xaxis']['autorange'] = False
        figure['layout']['yaxis']['autorange'] = False
        return figure, None, x_min, x_max, y_min, y_max
    else:
        raise PreventUpdate

def get_axes_range(figure, log, relayoutData):
    x_min, x_max = figure['layout']['xaxis']['range']
    y_min, y_max = figure['layout']['yaxis']['range']
    if log == 'log':
        x_min = 10 ** x_min
        x_max = 10 ** x_max
    if log == 'linear' and relayoutData and 'yaxis.autorange' in list(relayoutData.keys()):
        figure['layout']['xaxis']['range'] = [x_min, x_max]
    x_min, x_max, y_min, y_max = round(x_min, 2), round(x_max, 2), round(y_min, 2), round(y_max, 2)
    return figure, x_min, x_max, y_min, y_max

def Set_axes_range(x_min, x_max, y_min, y_max, figure, log):
    if log == 'log':
        input_x_min = math.log(x_min,10)
        input_x_max = math.log(x_max,10)
    else:
        input_x_min, input_x_max = x_min, x_max
    figure['layout']['xaxis']['range'] = [input_x_min, input_x_max]
    figure['layout']['yaxis']['range'] = [y_min, y_max]
    return figure, x_min, x_max, y_min, y_max

@app.callback(Output('emission_conducted_phase', 'figure',allow_duplicate = True),
    Input('xaxis_emission_conducted_phase', 'value'),
    State('emission_conducted_phase', 'figure'),
    State('input_x_min_conducted_phase', 'value'),
    State('input_x_max_conducted_phase', 'value'),
    prevent_initial_call=True)

def figure_conducted_phase(option, figure, input_x_min, input_x_max):
    if figure['data'] != []:
        return figure_param(option, figure, input_x_min, input_x_max)
    else:
        raise PreventUpdate

@app.callback(Output('emission_conducted_wire', 'figure',allow_duplicate = True),
    Input('xaxis_emission_conducted_wire', 'value'),
    State('emission_conducted_wire', 'figure'),
    State('input_x_min_conducted_wire', 'value'),
    State('input_x_max_conducted_wire', 'value'),
    prevent_initial_call=True)

def figure_conducted_wire(option, figure, input_x_min, input_x_max):
    if figure['data'] != []:
        return figure_param(option, figure, input_x_min, input_x_max)
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_horizontal', 'figure',allow_duplicate = True),
    Input('xaxis_emission_radiated_horizontal', 'value'),
    State('emission_radiated_horizontal', 'figure'),
    State('input_x_min_radiated_horizontal', 'value'),
    State('input_x_max_radiated_horizontal', 'value'),
    prevent_initial_call=True)

def figure_radiated_horizontal(option, figure, input_x_min, input_x_max):
    if figure['data'] != []:
        return figure_param(option, figure, input_x_min, input_x_max)
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_vertical', 'figure',allow_duplicate = True),
    Input('xaxis_emission_radiated_vertical', 'value'),
    State('emission_radiated_vertical', 'figure'),
    State('input_x_min_radiated_vertical', 'value'),
    State('input_x_max_radiated_vertical', 'value'),
    prevent_initial_call=True)

def figure_radiated_vertical(option, figure, input_x_min, input_x_max):
    if figure['data'] != []:
        return figure_param(option, figure, input_x_min, input_x_max)
    else:
        raise PreventUpdate

@app.callback(Output('emission_radiated_horizontal_vertical', 'figure',allow_duplicate = True),
    Input('xaxis_emission_radiated_horizontal_vertical', 'value'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    State('input_x_min_radiated_horizontal_vertical', 'value'),
    State('input_x_max_radiated_horizontal_vertical', 'value'),
    prevent_initial_call=True)

def figure_radiated_horizontal_vertical(option, figure, input_x_min, input_x_max):
    if figure['data'] != []:
        return figure_param(option, figure, input_x_min, input_x_max)
    else:
        raise PreventUpdate

def figure_param(option, figure, input_x_min, input_x_max):
    if option == 'linear':
        figure['layout']['xaxis']['type'] = option
        figure['layout']['xaxis']['range'] = (input_x_min, input_x_max)
        if 'annotations' in figure['layout']:
            for i in range(len(figure['layout']['annotations'])):
                figure['layout']['annotations'][i]['x'] = 10 ** figure['layout']['annotations'][i]['x']
    else:
        figure['layout']['xaxis']['range'] = math.log(input_x_min, 10), math.log(input_x_max, 10)
        figure['layout']['xaxis']['type'] = option
        if 'annotations' in figure['layout']:
            for i in range(len(figure['layout']['annotations'])):
                figure['layout']['annotations'][i]['x']=math.log(figure['layout']['annotations'][i]['x'], 10)
    return figure

@app.callback(Output('emission_conducted_phase', 'figure',allow_duplicate = True),
    Output('cursor_list_conducted_phase', 'style',allow_duplicate = True),
    Output('cursor_output_conducted_phase','style',allow_duplicate = True),
    Input('activate_cursor_conducted_phase', 'on'),
    State('emission_conducted_phase', 'figure'),
    State('cursor_list_conducted_phase', 'style'),
    State('cursor_output_conducted_phase','style'),
    prevent_initial_call=True)

def activate_cursors_conducted_phase(on,figure,cursor_list,cursor_output):
    return activate_cursors(on,figure,cursor_list,cursor_output)

@app.callback(Output('emission_conducted_wire', 'figure',allow_duplicate = True),
    Output('cursor_list_conducted_wire', 'style',allow_duplicate = True),
    Output('cursor_output_conducted_wire','style',allow_duplicate = True),
    Input('activate_cursor_conducted_wire', 'on'),
    State('emission_conducted_wire', 'figure'),
    State('cursor_list_conducted_wire', 'style'),
    State('cursor_output_conducted_wire','style'),
    prevent_initial_call=True)

def activate_cursors_conducted_wire(on,figure,cursor_list,cursor_output):
    return activate_cursors(on,figure,cursor_list,cursor_output)

@app.callback(Output('emission_radiated_horizontal', 'figure',allow_duplicate = True),
    Output('cursor_list_radiated_horizontal', 'style',allow_duplicate = True),
    Output('cursor_output_radiated_horizontal','style',allow_duplicate = True),
    Input('activate_cursor_radiated_horizontal', 'on'),
    State('emission_radiated_horizontal', 'figure'),
    State('cursor_list_radiated_horizontal', 'style'),
    State('cursor_output_radiated_horizontal','style'),
    prevent_initial_call=True)

def activate_cursors_horizontal(on,figure,cursor_list,cursor_output):
    return activate_cursors(on,figure,cursor_list,cursor_output)

@app.callback(Output('emission_radiated_vertical', 'figure',allow_duplicate = True),
    Output('cursor_list_radiated_vertical', 'style',allow_duplicate = True),
    Output('cursor_output_radiated_vertical','style',allow_duplicate = True),
    Input('activate_cursor_radiated_vertical', 'on'),
    State('emission_radiated_vertical', 'figure'),
    State('cursor_list_radiated_vertical', 'style'),
    State('cursor_output_radiated_vertical','style'),
    prevent_initial_call=True)

def activate_cursors_vertical(on,figure,cursor_list,cursor_output):
    return activate_cursors(on,figure,cursor_list,cursor_output)

@app.callback(Output('emission_radiated_horizontal_vertical', 'figure',allow_duplicate = True),
    Output('cursor_list_radiated_horizontal_vertical', 'style',allow_duplicate = True),
    Output('cursor_output_radiated_horizontal_vertical','style',allow_duplicate = True),
    Input('activate_cursor_radiated_horizontal_vertical', 'on'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    State('cursor_list_radiated_horizontal_vertical', 'style'),
    State('cursor_output_radiated_horizontal_vertical','style'),
    prevent_initial_call=True)

def activate_cursors_horizontal_vertical(on,figure,cursor_list,cursor_output):
    return activate_cursors(on,figure,cursor_list,cursor_output)

def activate_cursors(on,figure,cursor_list,cursor_output):
    if figure:
        if on is True:
            cursor_list['display'] = 'block'
            cursor_output['display'] = 'block'
            figure['layout']['hovermode']='x unified'
            if 'shapes' in figure['layout']:
                for i in range(len(figure['layout']['shapes'])):
                    if figure['layout']['shapes'][i]['name']=='Cursor 1' or figure['layout']['shapes'][i]['name']=='Cursor 2':
                        figure['layout']['shapes'][i]['visible'] = True
                for i in range(len(figure['layout']['annotations'])):
                    if figure['layout']['annotations'][i]['name'] == 'Cursor 1' or figure['layout']['annotations'][i]['name'] == 'Cursor 2':
                        figure['layout']['annotations'][i]['visible'] = True
        if on is False:
            cursor_list['display'] = 'none'
            cursor_output['display'] = 'none'
            figure['layout']['hovermode']='closest'
            if 'shapes' in figure['layout']:
                for i in range(len(figure['layout']['shapes'])):
                    if figure['layout']['shapes'][i]['name']=='Cursor 1' or figure['layout']['shapes'][i]['name']=='Cursor 2':
                        figure['layout']['shapes'][i]['visible'] = 'legendonly'
                for i in range(len(figure['layout']['annotations'])):
                    if figure['layout']['annotations'][i]['name'] == 'Cursor 1' or figure['layout']['annotations'][i]['name'] == 'Cursor 2':
                        figure['layout']['annotations'][i]['visible'] = False
    return figure,cursor_list,cursor_output

@app.callback(Output('emission_conducted_phase', 'figure',allow_duplicate = True),
    Output('cursor_output_conducted_phase', 'children',allow_duplicate = True),
    Output('markers', 'data',allow_duplicate = True),
    Output('cursor_data', 'data', allow_duplicate=True),
    Input('emission_conducted_phase', 'clickData'),
    State('cursor_data','data'),
    State('emission_conducted_phase', 'figure'),
    State('cursor_list_conducted_phase', 'value'),
    State('cursor_list_conducted_phase', 'options'),
    State('xaxis_emission_conducted_phase', 'value'),
    State('markers', 'data'),
    State('cursor_output_conducted_phase', 'children'),
    State('activate-marker_conducted', 'on'),
    prevent_initial_call=True)

def cursors_conducted_phase(click_data, cursor_data, figure, value, options, log, markers, cursor_output, activate_marker):
    return cursors(click_data, cursor_data, figure, value, options, log, markers, cursor_output, activate_marker)

@app.callback(Output('emission_conducted_wire', 'figure',allow_duplicate = True),
    Output('cursor_output_conducted_wire', 'children',allow_duplicate = True),
    Output('markers', 'data',allow_duplicate = True),
    Output('cursor_data', 'data', allow_duplicate=True),
    Input('emission_conducted_wire', 'clickData'),
    State('cursor_data','data'),
    State('emission_conducted_wire', 'figure'),
    State('cursor_list_conducted_wire', 'value'),
    State('cursor_list_conducted_wire', 'options'),
    State('xaxis_emission_conducted_wire', 'value'),
    State('markers', 'data'),
    State('cursor_output_conducted_wire', 'children'),
    State('activate-marker_conducted', 'on'),
    prevent_initial_call=True)

def cursors_conducted_wire(click_data, cursor_data, figure, value, options, log, markers, cursor_output, activate_marker):
    return cursors(click_data, cursor_data, figure, value, options, log, markers, cursor_output, activate_marker)

@app.callback(Output('emission_radiated_horizontal', 'figure',allow_duplicate = True),
    Output('cursor_output_radiated_horizontal', 'children',allow_duplicate = True),
    Output('markers', 'data',allow_duplicate = True),
    Output('cursor_data', 'data', allow_duplicate=True),
    Input('emission_radiated_horizontal', 'clickData'),
    State('cursor_data','data'),
    State('emission_radiated_horizontal', 'figure'),
    State('cursor_list_radiated_horizontal', 'value'),
    State('cursor_list_radiated_horizontal', 'options'),
    State('xaxis_emission_radiated_horizontal', 'value'),
    State('markers', 'data'),
    State('cursor_output_radiated_horizontal', 'children'),
    State('activate-marker_radiated', 'on'),
    prevent_initial_call=True)

def cursors_radiated_horizontal(click_data, cursor_data, figure, value, options, log, markers, cursor_output, activate_marker):
    return cursors(click_data, cursor_data, figure, value, options, log, markers, cursor_output, activate_marker)

@app.callback(Output('emission_radiated_vertical', 'figure',allow_duplicate = True),
    Output('cursor_output_radiated_vertical', 'children',allow_duplicate = True),
    Output('markers', 'data',allow_duplicate = True),
    Output('cursor_data', 'data', allow_duplicate=True),
    Input('emission_radiated_vertical', 'clickData'),
    State('cursor_data','data'),
    State('emission_radiated_vertical', 'figure'),
    State('cursor_list_radiated_vertical', 'value'),
    State('cursor_list_radiated_vertical', 'options'),
    State('xaxis_emission_radiated_vertical', 'value'),
    State('markers', 'data'),
    State('cursor_output_radiated_vertical', 'children'),
    State('activate-marker_radiated', 'on'),
    prevent_initial_call=True)

def cursors_radiated_vertical(click_data, cursor_data, figure, value, options, log, markers, cursor_output, activate_marker):
    return cursors(click_data, cursor_data, figure, value, options, log, markers, cursor_output, activate_marker)

@app.callback(Output('emission_radiated_horizontal_vertical', 'figure',allow_duplicate = True),
    Output('cursor_output_radiated_horizontal_vertical', 'children',allow_duplicate = True),
    Output('markers', 'data',allow_duplicate = True),
    Output('cursor_data', 'data', allow_duplicate=True),
    Input('emission_radiated_horizontal_vertical', 'clickData'),
    State('cursor_data','data'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    State('cursor_list_radiated_horizontal_vertical', 'value'),
    State('cursor_list_radiated_horizontal_vertical', 'options'),
    State('xaxis_emission_radiated_horizontal_vertical', 'value'),
    State('markers', 'data'),
    State('cursor_output_radiated_horizontal_vertical', 'children'),
    State('activate-marker_radiated', 'on'),
    prevent_initial_call=True)

def cursors_radiated_horizontal_vertical(click_data, cursor_data, figure, value, options, log, markers, cursor_output, activate_marker):
    return cursors(click_data, cursor_data, figure, value, options, log, markers, cursor_output, activate_marker)

def cursors(click_data, cursor_data, figure, value, options, log, markers, cursor_calculation, activate_marker):
    if figure['layout']['hovermode'] == 'closest' and figure['data'] != [] and click_data is not None and activate_marker is True:
        figure, markers = add_marker(click_data, figure, markers, log)


    elif click_data and figure and figure['layout']['hovermode'] == 'x unified':
        triggered_id = ctx.triggered_id
        graph_name = triggered_id.split('_')[1] + '_' + triggered_id.split('_')[2]

        chart_name = ''
        for item in click_data['points']:
            chart_index = item['curveNumber']
            if figure['data'][chart_index]['meta']['Name'] == value:
                chart_name = figure['data'][chart_index]['meta']['Name']
                break
        if chart_name == value:
            x = click_data['points'][0]['x']
            y = click_data['points'][0]['y']
            if log == 'log':
                x_log = math.log(x, 10)
            else:
                x_log = x
            x_max, y_max, x_min, y_min = find_min_max(figure)

            if graph_name not in list(cursor_data['left'].keys()):
                cursor_data['left'] = {graph_name: {'chart_index': chart_index, 'x': x, 'y': y}}
                shape = dict(type='line', name='Cursor 1', x0=x, x1 = x, y0=y_min - 4, y1=y_max + 4,
                             line=dict(color=figure['data'][chart_index]['line']['color'], dash='dash'), visible=True)
                annotation = dict(name='Cursor 1', x=x_log, y=1, xref="x", yref="paper",
                                  text=f"<b> {figure['data'][chart_index]['name']}<br> Frequency (MHz):</b> {x:.2f}<br> <b>Level (dBµV/m):</b> {y:.2f}",
                                  xanchor='left', yanchor='top', showarrow=False, bordercolor="#c7c7c7",
                                  bgcolor=figure['data'][chart_index]['line']['color'], font=dict(color="#ffffff"),
                                  visible=True, align='left')

            elif graph_name not in list(cursor_data['right'].keys()) and x > cursor_data['left'][graph_name]['x']:
                cursor_data['right'] = {graph_name: {'chart_index': chart_index, 'x': x, 'y': y}}
                shape = dict(type='line', name='Cursor 2', x0=x, x1 = x, y0=y_min - 4, y1=y_max + 4,
                             line=dict(color=figure['data'][chart_index]['line']['color'], dash='dash'), visible=True)
                annotation = dict(name='Cursor 2', x=x_log, y=1, xref="x", yref="paper",
                                  text=f"<b> {figure['data'][chart_index]['name']}<br> Frequency (MHz):</b> {x:.2f}<br> <b>Level (dBµV/m):</b> {y:.2f}",
                                  xanchor='left', yanchor='top', showarrow=False, bordercolor="#c7c7c7",
                                  bgcolor=figure['data'][chart_index]['line']['color'], font=dict(color="#ffffff"),
                                  visible=True, align='left')

            else:
                new_shapes = figure['layout']['shapes']
                for shape in figure['layout']['shapes'].copy():
                    if shape['name'] == 'Cursor 1':
                        new_shapes.remove(shape)
                    elif shape['name'] == 'Cursor 2':
                        new_shapes.remove(shape)
                        break
                figure['layout']['shapes'] = new_shapes
                new_annotations = figure['layout']['annotations']
                for annotation in figure['layout']['annotations'].copy():
                    if annotation['name'] == 'Cursor 1':
                        new_annotations.remove(annotation)
                    elif annotation['name'] == 'Cursor 2':
                        new_annotations.remove(annotation)
                        break
                figure['layout']['annotations'] = new_annotations

                figure['data'][cursor_data['left'][graph_name]['chart_index']]['meta']['Cursors'].remove('Cursor 1')
                cursor_data['left'] = {graph_name: {'chart_index': chart_index, 'x': x, 'y': y}}
                if graph_name in list(cursor_data['right'].keys()):
                    figure['data'][cursor_data['right'][graph_name]['chart_index']]['meta']['Cursors'].remove('Cursor 2')
                    cursor_data['right'].pop(graph_name)
                shape = dict(type='line', name='Cursor 1', x0=x, x1=x, y0=y_min - 4, y1=y_max + 4,
                             line=dict(color=figure['data'][chart_index]['line']['color'], dash='dash'), visible=True)
                annotation = dict(name='Cursor 1', x=x_log, y=1, xref="x", yref="paper",
                                  text=f"<b> {figure['data'][chart_index]['name']}<br> Frequency (MHz):</b> {x:.2f}<br> <b>Level (dBµV/m):</b> {y:.2f}",
                                  xanchor='left', yanchor='top', showarrow=False, bordercolor="#c7c7c7",
                                  bgcolor=figure['data'][chart_index]['line']['color'], font=dict(color="#ffffff"),
                                  visible=True, align='left')

            figure['layout']['shapes'].append(shape)
            figure['layout']['annotations'].append(annotation)
            figure['data'][chart_index]['meta']['Cursors'].append(shape['name'])

            if graph_name in cursor_data['left'] and graph_name in cursor_data['right']:
                diff_x = cursor_data['right'][graph_name]['x'] - cursor_data['left'][graph_name]['x']
                diff_y = cursor_data['right'][graph_name]['y'] - cursor_data['left'][graph_name]['y']
                cursor_calculation = f'ΔFrequency (MHz) = {diff_x:.2f} \n ΔLevel (dBμV/m) = {diff_y:.2f}'
            else:
                cursor_calculation = f'ΔFrequency (MHz) = - \n ΔLevel (dBμV/m) = -'

    else:
        raise PreventUpdate

    return figure, cursor_calculation, markers, cursor_data

@app.callback(Output('emission_conducted_phase', 'figure', allow_duplicate = True),
    Output('markers', 'data', allow_duplicate = True),
    Input('emission_conducted_phase', 'relayoutData'),
    State('emission_conducted_phase', 'figure'),
    State('markers', 'data'),
    prevent_initial_call=True)

def remove_marker_conducted_phase(relayoutData, figure, markers):
    return remove_marker(relayoutData, figure, markers)

@app.callback(Output('emission_conducted_wire', 'figure', allow_duplicate = True),
    Output('markers', 'data', allow_duplicate = True),
    Input('emission_conducted_wire', 'relayoutData'),
    State('emission_conducted_wire', 'figure'),
    State('markers', 'data'),
    prevent_initial_call=True)

def remove_marker_conducted_wire(relayoutData, figure, markers):
    return remove_marker(relayoutData, figure, markers)

@app.callback(Output('emission_radiated_horizontal', 'figure', allow_duplicate = True),
    Output('markers', 'data', allow_duplicate = True),
    Input('emission_radiated_horizontal', 'relayoutData'),
    State('emission_radiated_horizontal', 'figure'),
    State('markers', 'data'),
    prevent_initial_call=True)

def remove_marker_radiated_horizontal(relayoutData, figure, markers):
    return remove_marker(relayoutData, figure, markers)

@app.callback(Output('emission_radiated_vertical', 'figure', allow_duplicate = True),
    Output('markers', 'data', allow_duplicate = True),
    Input('emission_radiated_vertical', 'relayoutData'),
    State('emission_radiated_vertical', 'figure'),
    State('markers', 'data'),
    prevent_initial_call=True)

def remove_marker_radiated_vertical(relayoutData, figure, markers):
    return remove_marker(relayoutData, figure, markers)

@app.callback(Output('emission_radiated_horizontal_vertical', 'figure', allow_duplicate = True),
    Output('markers', 'data', allow_duplicate = True),
    Input('emission_radiated_horizontal_vertical', 'relayoutData'),
    State('emission_radiated_horizontal_vertical', 'figure'),
    State('markers', 'data'),
    prevent_initial_call=True)

def remove_marker_radiated_horizontal_vertical(relayoutData, figure, markers):
    return remove_marker(relayoutData, figure, markers)

def remove_marker(relayoutData, figure, markers):
    if relayoutData and 'annotations' in list(relayoutData.keys())[0] and 'Marker' in str(list(relayoutData.values())[0]):
        name = list(relayoutData.values())[0][4:12]
        for trace in figure['data']:
            if trace['name'] == name:
                figure['data'].remove(trace)
                break
        for annotation in figure['layout']['annotations']:
            if annotation['name'] == name:
                figure['layout']['annotations'].remove(annotation)
                break
        for marker in markers:
            if marker['name'] == name:
                markers.remove(marker)
                break
        return figure, markers
    else:
        raise PreventUpdate

@app.callback(
    Output("sidebar", "style"),
    Output("toggle-button", "style"),
    Output('toggle-button', 'disabled'),
    Output('line_table_container_conducted_phase', 'style', allow_duplicate = True),
    Output('line_table_container_conducted_wire', 'style', allow_duplicate = True),
    Output('line_table_container_radiated_horizontal', 'style', allow_duplicate = True),
    Output('line_table_container_radiated_vertical', 'style', allow_duplicate = True),
    Output('line_table_container_radiated_horizontal_vertical', 'style', allow_duplicate = True),
    Output('line_table_btn_conducted_phase', 'children', allow_duplicate = True),
    Output('line_table_btn_conducted_wire', 'children', allow_duplicate = True),
    Output('line_table_btn_radiated_horizontal', 'children', allow_duplicate = True),
    Output('line_table_btn_radiated_vertical', 'children', allow_duplicate = True),
    Output('line_table_btn_radiated_horizontal_vertical', 'children', allow_duplicate = True),
    Input('Test-table', 'selectedRows'),
    Input("toggle-button", "n_clicks"),
    State("sidebar", "style"),
    State("toggle-button", "style"),
    State('toggle-button', 'disabled'),
    State('line_table_container_conducted_phase', 'style'),
    State('line_table_container_conducted_wire', 'style'),
    State('line_table_container_radiated_horizontal', 'style'),
    State('line_table_container_radiated_vertical', 'style'),
    State('line_table_container_radiated_horizontal_vertical', 'style'),
    prevent_initial_call=True
)
def toggle_sidebar(selectedRows, n_clicks, style_sidebar, style_toggle_button, sidebar_btn, line_table_container_conducted_phase, line_table_container_conducted_wire, line_table_container_radiated_horizontal, line_table_container_radiated_vertical, line_table_container_radiated_horizontal_vertical):
    triggered_id = ctx.triggered_id
    line_table_btn_conducted_phase, line_table_btn_conducted_wire, line_table_btn_radiated_horizontal, line_table_btn_radiated_vertical, line_table_btn_radiated_horizontal_vertical = no_update, no_update, no_update, no_update, no_update,
    if triggered_id == 'Test-table':
        if selectedRows == []:
            sidebar_btn = True
            style_sidebar["transform"] = "translateX(100%)"
            style_toggle_button["transform"] = "translateX(0%)"
            line_table_container_conducted_phase['display'], line_table_container_conducted_wire['display'], line_table_container_radiated_horizontal['display'], line_table_container_radiated_vertical['display'], line_table_container_radiated_horizontal_vertical['display'] = 'none', 'none', 'none', 'none', 'none'
            line_table_btn_conducted_phase, line_table_btn_conducted_wire, line_table_btn_radiated_horizontal, line_table_btn_radiated_vertical, line_table_btn_radiated_horizontal_vertical = 'Show Line Display Parameters', 'Show Line Display Parameters', 'Show Line Display Parameters', 'Show Line Display Parameters', 'Show Line Display Parameters'
        else:
            sidebar_btn = False
    elif triggered_id == "toggle-button":
        if n_clicks % 2 == 1:  # Show the sidebar
            style_sidebar["transform"] = "translateX(0)"
            style_toggle_button["transform"] = "translateX(-175%)"
        else:
            style_sidebar["transform"] = "translateX(100%)"
            style_toggle_button["transform"] = "translateX(0%)"
            line_table_container_conducted_phase['display'], line_table_container_conducted_wire['display'], line_table_container_radiated_horizontal['display'], line_table_container_radiated_vertical['display'], line_table_container_radiated_horizontal_vertical['display'] = 'none', 'none', 'none', 'none', 'none'
            line_table_btn_conducted_phase, line_table_btn_conducted_wire, line_table_btn_radiated_horizontal, line_table_btn_radiated_vertical, line_table_btn_radiated_horizontal_vertical = 'Show Line Display Parameters', 'Show Line Display Parameters', 'Show Line Display Parameters', 'Show Line Display Parameters', 'Show Line Display Parameters'
    return style_sidebar, style_toggle_button, sidebar_btn, line_table_container_conducted_phase, line_table_container_conducted_wire, line_table_container_radiated_horizontal, line_table_container_radiated_vertical, line_table_container_radiated_horizontal_vertical, line_table_btn_conducted_phase, line_table_btn_conducted_wire, line_table_btn_radiated_horizontal, line_table_btn_radiated_vertical, line_table_btn_radiated_horizontal_vertical

# Callback to show/hide the emission submenu
@app.callback([Output("conducted-voltage-submenu", "style",allow_duplicate = True),
    Output("radiated-electric-submenu", "style",allow_duplicate = True),
    Output("emission_conducted_param_btn", "n_clicks",allow_duplicate = True),
    Output("emission_radiated_param_btn", "n_clicks",allow_duplicate = True)],
    Input("emission_conducted_param_btn", "n_clicks"),
    Input("emission_radiated_param_btn", "n_clicks"),
    prevent_initial_call=True
)
def toggle_submenus(emission_clicks, immunity_clicks):
    ctx = dash.callback_context

    # Check which button was clicked
    if ctx.triggered:
        clicked_button = ctx.triggered[0]["prop_id"].split(".")[0]  # get the button ID

        # Initially set both submenus to hidden
        emission_style = submenu_style
        immunity_style = submenu_style

        # Logic to show/hide the appropriate submenu
        if clicked_button == "emission_conducted_param_btn":
            if emission_clicks % 2 == 1:  # Emission button clicked an odd number of times
                emission_style = submenu_active_style
                immunity_clicks = 0
            else:  # Emission button clicked an even number of times
                emission_style = submenu_style
                immunity_style = submenu_style  # Hide Immunity submenu

        elif clicked_button == "emission_radiated_param_btn":
            if immunity_clicks % 2 == 1:  # Immunity button clicked an odd number of times
                immunity_style = submenu_active_style
                emission_clicks = 0
            else:  # Immunity button clicked an even number of times
                immunity_style = submenu_style
                emission_style = submenu_style  # Hide Emission submenu

        return emission_style, immunity_style, emission_clicks, immunity_clicks
    else:
        raise PreventUpdate

@app.callback(Output('suspectsTable-conducted', 'style', allow_duplicate = True),
    Output('minimize_suspectTable_conducted_btn', "children"),
    Input('minimize_suspectTable_conducted_btn', "n_clicks"),
    State('suspectsTable-conducted', 'style'),
    State('suspectsTable-conducted', 'rowData'),
    prevent_initial_call=True)

def minimize_suspectTable_conducted(n_clicks, style, rowData):
    return minimize_suspectTable(n_clicks, style, rowData)

@app.callback(Output('suspectsTable-radiated', 'style', allow_duplicate = True),
    Output('minimize_suspectTable_radiated_btn', "children"),
    Input('minimize_suspectTable_radiated_btn', "n_clicks"),
    State('suspectsTable-radiated', 'style'),
    State('suspectsTable-radiated', 'rowData'),
    prevent_initial_call=True)

def minimize_suspectTable_radiated(n_clicks, style, rowData):
    return minimize_suspectTable(n_clicks, style, rowData)

def minimize_suspectTable(n_clicks, style, rowData):
    if rowData != []:
        if n_clicks % 2 == 1:
            style['display'], children = 'block', 'Hide Suspects Table'
        else:
            style['display'], children = 'none', 'Show Suspects Table'
        return style, children
    else:
        raise PreventUpdate

@app.callback(Output('finalsTable-conducted', 'style', allow_duplicate = True),
    Output('minimize_finalTable_conducted_btn', "children"),
    Input('minimize_finalTable_conducted_btn', "n_clicks"),
    State('finalsTable-conducted', 'style'),
    State('finalsTable-conducted', 'rowData'),
    prevent_initial_call=True)

def minimize_finalsTable_conducted(n_clicks, style, rowData):
    return minimize_finalsTable(n_clicks, style, rowData)

@app.callback(Output('finalsTable-radiated', 'style', allow_duplicate = True),
    Output('minimize_finalTable_radiated_btn', "children"),
    Input('minimize_finalTable_radiated_btn', "n_clicks"),
    State('finalsTable-radiated', 'style'),
    State('finalsTable-radiated', 'rowData'),
    prevent_initial_call=True)

def minimize_finalsTable_radiated(n_clicks, style, rowData):
    return minimize_finalsTable(n_clicks, style, rowData)

def minimize_finalsTable(n_clicks, style, rowData):
    if rowData != []:
        if n_clicks % 2 == 1:
            style['display'], children = 'block', 'Hide Finals Table'
        else:
            style['display'], children = 'none', 'Show Finals Table'
        return style, children
    else:
        raise PreventUpdate

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, port= 8050)