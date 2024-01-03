# IMPORT LIRARIES
import pathlib
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objs as go
import pandas as pd

#------------------LOAD DATA-----------------------------------------------#
def load_data(data_file: str) -> pd.DataFrame:
    '''
    Load data from /data directory
    '''
    PATH = pathlib.Path(__file__).parent
    DATA_PATH = PATH.joinpath("data").resolve()
    return pd.read_csv(DATA_PATH.joinpath(data_file))

hospital_df = load_data('hospital.csv')
cases_state_df = load_data('cases_state.csv')

#-----------------PROCESS DATA---------------------------------------------#
# Convert 'date' column to datetime
hospital_df['date'] = pd.to_datetime(hospital_df['date'])
cases_state_df['date'] = pd.to_datetime(cases_state_df['date'])

# Merge dataset
df = pd.merge(cases_state_df,hospital_df, on=['date','state'])

# Extract year and month from date
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month

# Calculate healthcare capacity (bed occupancy rate)
df['healthcare_capacity'] = df['admitted_total'] / df['beds'] * 100

# Display Card: Find the state with the highest healthcare capacity
max_capacity_state = df.loc[df['healthcare_capacity'].idxmax()]['state']
max_capacity_value = df['healthcare_capacity'].max()

# Display Card: Calculate the percentage of beds utilized by COVID patients
beds_utilized_by_covid = df['beds_covid'].sum() / df['beds'].sum() * 100
beds_utilized_by_covid = beds_utilized_by_covid.max()

# Calculate average healthcare capacity for each year and month
heatmap_data = df.groupby(['year', 'month'])['healthcare_capacity'].mean().reset_index()
# handle missing values
heatmap_data = heatmap_data.fillna(0)

#----------------------INITIALIZE APP-----------------------------------------#
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],title="myapp")

# Declare server for Heroku deployment. Needed for Procfile.
server = app.server

# create reusable card component
def get_card_component(title, data):
    component = dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H4(title),
                            html.H4(data)
                        ]), 
                        color="dark", 
                        outline=True,
                        className = 'text-dark',
                        style={'textAlign': 'center', 'margin-bottom': '20px'}
                    ),
                )
    return component

# create color palette
color_discrete_sequence = ['#0a9396','#94d2bd','#e9d8a6','#ee9b00', '#ca6702', '#bb3e03', '#ae2012']

#-------------------SET UP APP LAYOUT-----------------------------------------#
app.layout = html.Div([
    html.H1(children='Healthcare Capacity Analysis in Malaysia', style={'textAlign':'center', 'padding-bottom': '20px'}),
    dbc.Row([
        get_card_component('State', str(max_capacity_state)),
        get_card_component('Highest Capacity', str(max_capacity_value)),
        get_card_component('Beds for COVID19', str(beds_utilized_by_covid)),       
    ]),
    dbc.Row([
        dbc.Col([
            html.H4("State"),
            html.Div(
                dcc.Dropdown(id='state-dropdown',
                 options=[{'label': i, 'value': i} for i in df['state'].unique()],
                 value='Selangor'),
                style = {'margin-top': '20px'},             
            ),
            dcc.Graph(id='line-chart'),          
        ], width=4),
        dbc.Col([
            html.Div(
                dcc.Graph(id='scatter-plot'),
            )   
        ], width=4),
        dbc.Col([
            html.Div(
                dcc.Graph(id='heatmap'),
            )   
        ], width=4),               
    ]),  
], style= {"margin": "50px 50px 50px 50px"})

#-------------------APP CALLBACK-----------------------------------------#
@app.callback(
    [Output('line-chart', 'figure'),
     Output('scatter-plot', 'figure'),
     Output('heatmap', 'figure')],
    [Input('state-dropdown', 'value')]
)
def update_graph(selected_state):
    filtered_df = df[df['state'] == selected_state]

    line_chart = px.line(filtered_df, x='date', y='cases_new', title='New Cases Over Time')
    line_chart.add_trace(go.Scatter(x=filtered_df['date'], y=filtered_df['healthcare_capacity'],
                                    mode='lines', name='Healthcare Capacity', yaxis='y2'))
    line_chart.update_layout(yaxis2=dict(overlaying='y', side='right'))
    line_chart.update_xaxes(showgrid=False)
    line_chart.update_yaxes(showgrid=False)

    # Take a random sample for the scatter plot
    scatter_sample = filtered_df.sample(n=100, random_state=1)

    scatter_plot = px.scatter(scatter_sample, x='cases_new', y='healthcare_capacity', trendline='ols',
                              title='Healthcare Capacity vs New Cases in '+selected_state)
    scatter_plot.update_xaxes(showgrid=False)
    scatter_plot.update_yaxes(showgrid=False)
    heatmap=px.imshow(heatmap_data.pivot(index='year', columns='month', values='healthcare_capacity')
                      ,labels=dict(x="Month", y="Year")
                      ,color_continuous_scale='reds',)
    heatmap.update_xaxes(showgrid=False)
    heatmap.update_yaxes(showgrid=False)
    heatmap.update_coloraxes(colorbar_tickprefix="%")
    heatmap.update_layout(
        plot_bgcolor='white',
        title={
            'text': "Average Healthcare Capacity by Year and Month",
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'},
        title_font=dict(
            family="Times New Roman",
            size=24,
            color="black"
        ),
        coloraxis_colorbar=dict(
            lenmode="pixels", len=400,
            yanchor="bottom", y=1,
            xanchor="center", x=0.5,
            orientation="h"
        ),
    )

    return line_chart, scatter_plot, heatmap

#-------------------RUN WEB SERVER----------------------------------------#
if __name__ == '__main__':
    app.run_server(debug=True)

# To quit run, CTRL+C