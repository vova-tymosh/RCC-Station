import sys
import time
import struct
import logging
from dash import Dash, Patch, dcc, html, ctx
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import dash_bootstrap_components as dbc

import Command


log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
command = Command.command


SIDEBAR_STYLE = {
  "position": "fixed",
  "top": 0,
  "left": 0,
  "bottom": 0,
  "width": "110px",
  "padding": "30px 16px",
  "background-color": "#f8f9fa",
  "font-family": "Arial, Helvetica, sans-serif",
}

CONTENT_STYLE = {
  "margin": "2rem 1rem 0rem 7rem",
  "font-family": "Arial, Helvetica, sans-serif",
}


figure = fig = go.Figure()
for i in range(10):
  fig.add_trace(go.Scatter(x=[], y=[], name=''))
fig.update_layout(
  height=400,
  margin=dict( l=0, r=0, t=10, b=0 ),
  legend=dict( yanchor="top", y=0.99, xanchor="left", x=0.01 ))

app = Dash(__name__, external_stylesheets=[dbc.themes.SPACELAB, dbc.icons.BOOTSTRAP], update_title=None)

content = html.Div([
  dbc.Row(
    dbc.Col([ dcc.Slider(0, 100, id='throttle', marks=None),
              html.Div(id='container-throttle'), ]),
    ),
  dbc.Row([
    dbc.Col([ dbc.RadioItems(id='gear', className="mx-0 btn-group", inputClassName="btn-check",
                labelClassName="btn btn-outline-primary", labelCheckedClassName="active",
                options=[
                  {"label": html.I(className="bi-rewind-fill"), "value": "REVERSE"},
                  {"label": html.I(className="bi-pause-fill"), "value": "STOP"},
                  {"label": html.I(className="bi-fast-forward-fill"), "value": "FORWARD"},
                ],
                style={"padding":0, "margin":0}),
              html.Div(id='container-gear'),],
            width=6),
    dbc.Col([ dbc.InputGroup([
                dbc.Input(id='cmd-value', type='text', autoFocus=True, debounce=True),
                dbc.Button('+', id='cmd-click', n_clicks=0) ],),
              html.Div(id='container-command'), ],
            width="auto"),
  ],className="g-0",),
  dbc.Row([
    dbc.Col([  dcc.Graph(id='graph', figure=figure),
               dcc.Interval(id="interval", interval=500), ]
    )
  ]),
  dbc.Row([
    dbc.Col([ dbc.Button('Light on', id='liton', n_clicks=0, style = {'margin-left': '2rem'}),
              dbc.Button('Light off', id='litoff', n_clicks=0, style = {'margin-left': '1rem'}),
              dbc.Button('Acc', id='acc', n_clicks=0, style = {'margin-left': '1rem'}),
              dbc.Button('Dec', id='dec', n_clicks=0, style = {'margin-left': '1rem'}),
              html.Div(id='container-buttons'), ],
    )
  ]),
  ], style=CONTENT_STYLE)




@app.callback(
  Output('container-buttons', 'children'),
  Input('liton', 'n_clicks'),
  Input('litoff', 'n_clicks'),
  Input('acc', 'n_clicks'),
  Input('dec', 'n_clicks'))
def on_button_click(b1, b2, b3, b4):
  changed_id = ctx.triggered_id
  if 'liton' == changed_id:
    logging.error('Lights on')
    command.get().setFunction(0, 'ON')
  elif 'litoff' == changed_id:
    logging.error('Lights off')
    command.get().setFunction(0, 'OFF')
  elif 'acc' == changed_id:
    logging.error('Acc')
  elif 'dec' == changed_id:
    logging.error('Dec')

@app.callback(
  Output('container-command', 'children'),
  Output('cmd-value', 'value'),
  Input('cmd-click', 'n_clicks'),
  Input('cmd-value', 'value'))
def on_command(n_clicks, value):
  if value and len(value) > 0:
    cmd, value = (value[0], value[1:])
    logging.error('Command: %s/%s'%(cmd, value))
    command.get().setCommand(cmd, value)
  return '', ''

@app.callback(
  [Output('gear', 'value'),
   Output('throttle', 'value'),
   Output('container-gear', 'children')],
  [Input('gear', 'value'),
   Input('throttle', 'value')])
def on_gear(gearNew, throttleNew):
  loco = command.get()
  gearOld = loco.getDirection()
  throttleOld = loco.getThrottle()
  if gearNew is None:
    gearNew = gearOld
  if throttleNew is None:
    throttleNew = throttleOld
  if gearOld != 'STOP' and gearOld != gearNew:
    gearNew = 'STOP'
  if gearNew == 'STOP':
    throttleNew = 0
  loco.setDirection(gearNew)
  loco.setThrottle(throttleNew)
  return (gearNew, throttleNew, [])


@app.callback(
   Output("container-sidebar", "children"),
   Input("url", "pathname"))
def on_page_content(index):
  index = index[1:]
  logging.error('Select Loco: %s'%index)
  command.set(index)

@app.callback(
  Output("graph", "figure"), Input('interval', 'n_intervals'))
def update_name(n_intervals):
  patched_figure = Patch()
  names = command.get().getFieldNames()

  for i, name in enumerate(names[1:]):
    patched_figure["data"][i]["name"] = name
  return patched_figure

@app.callback(
  Output('graph', 'extendData'), 
  [Input('interval', 'n_intervals')])
def update_data(n_intervals):
  x = []
  y = []
  index = []
  client = command.get()
  if client:
    for i, d in enumerate(client.data[1:]):
      x.append( [client.data[0]] )
      y.append( [d] )
      index.append( i )
  return dict(x=x, y=y), index, 50

def getLocosInNavbar():
  navBar = []
  logging.error('getLocosInNavbar %s %s'%(command, command.getLocoMap().items()))
  for addr,loco in command.getLocoMap().items():
    navBar.append(dbc.NavLink(loco.name, href=F"/{addr}", active="exact", external_link=True))
  return navBar

def webServer():
  sidebar = html.Div([
    html.H4("Railroad Station"),
    html.Hr(),
    html.P("Locos:"),
    dbc.Nav(
      getLocosInNavbar(),
      vertical=True,
      pills=True,
      ),
      html.Div(id='container-sidebar'),
    ],
    style=SIDEBAR_STYLE,
  )
  app.layout = html.Div([dcc.Location(id="url"), sidebar, content])
  app.run(debug=False, host='0.0.0.0')



logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    filename='station.log',
                    filemode='a')
logging.error('Start')

command = Command.command
command.start()
# Wait to mqtt to start and pull Loco info
time.sleep(1)

webServer()
