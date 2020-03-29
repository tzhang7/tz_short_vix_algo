import dash
from dash.dependencies import Output, Input
import dash_core_components as dcc
import dash_html_components as html
import plotly
import plotly.graph_objs as go
from collections import deque
from signal_notifier import RealTradeEngine
from config.user import User
import datetime

user1 = User('tao', 'tzshortvix@gmail.com')
engine = RealTradeEngine([user1])

X = deque(maxlen=6000)
X.append(datetime.datetime.now())
Y = deque(maxlen=6000)
Y.append(engine.return_signal(datetime.datetime.now()))

app = dash.Dash(__name__)
app.layout = html.Div(children=[
    html.Div(children='''
            VIX Trading Signal
        '''),
    dcc.Input(id='input_month1_ticker', value='VIJ20', type='text'),
    dcc.Graph(id='live-graph', animate=True),
    dcc.Interval(
        id='graph-update',
        interval=5000,
        n_intervals=0
    ),
]
)


@app.callback(Output('live-graph', 'figure'),
              [Input('graph-update', 'n_intervals'), Input('input_month1_ticker', 'value')])
def update_graph_scatter(n, month1_ticker):
    print(month1_ticker)

    trade_time = datetime.datetime.now()
    wa_ratio = engine.return_signal(trade_time)

    X.append(trade_time)
    Y.append(wa_ratio)

    data = plotly.graph_objs.Scatter(
        x=list(X),
        y=list(Y),
        name='Scatter',
        mode='lines+markers'
    )

    return {'data': [data], 'layout': go.Layout(xaxis=dict(range=[min(X), max(X)]),
                                                yaxis=dict(range=[min(Y), max(Y)]), )}


if __name__ == '__main__':
    app.run_server(debug=True)
