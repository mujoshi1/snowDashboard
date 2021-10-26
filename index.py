import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from app import app
from app import server

from layouts import regions, keyapps, themes, legacy, sla, compare
import callbacks    
menulinks = {'/SnowDashboard/' : regions,
             '/SnowDashboard/regions' : regions,
              '/SnowDashboard/keyapps' : keyapps,
              '/SnowDashboard/legacy' : legacy,
              '/SnowDashboard/sla' : sla,
              '/SnowDashboard/compare' : compare,
              '/SnowDashboard/themes' : themes,}

#Application Layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
    ])
                
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])

def display_page(pathname):
    try:
        path = menulinks[pathname]
        return path
    except KeyError:
            return "404 Page Error! Please choose a link"
    
if __name__ == '__main__':
    app.run_server(debug=False)