from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import SignUpForm

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('users:dashboard')
        else:
            messages.error(request, 'Correct the errors below')
    else:
        form = SignUpForm()

    return render(request, 'app/signup.html', {'form': form})


@login_required
def dashboard_view(request):
    #Importing libraries
    import numpy as np
    import pandas as pd
    import requests
    import xlsxwriter
    import math
    from scipy import stats

    #Reading data
    stocks = pd.read_csv('/Users/meetbhanu/djangoalgo/Django-Signup-master/users/sp_500_stocks.csv')
    #from secrets import IEX_CLOUD_API_TOKEN
    IEX_CLOUD_API_TOKEN = 'Tpk_059b97af715d417d9f49f50b51b1c448'

    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]   
    symbol_groups = list(chunks(stocks['Ticker'], 100))
    symbol_strings = []
    for i in range(0, len(symbol_groups)):
        symbol_strings.append(','.join(symbol_groups[i]))
    my_columns = ['Ticker', 'Price', 'Price-to-Earnings Ratio', 'Number of Shares to Buy']

    #mainlogic
    rv_columns = [
    'Ticker',
    'Price',
    'Number of Shares to Buy', 
    'Price-to-Earnings Ratio',
    'PE Percentile',
    'Price-to-Book Ratio',
    'PB Percentile',
    'Price-to-Sales Ratio',
    'PS Percentile',
    'EV/EBITDA',
    'EV/EBITDA Percentile',
    'EV/GP',
    'EV/GP Percentile',
    'RV Score'
    ]
    rv_dataframe = pd.DataFrame(columns = rv_columns)

    for symbol_string in symbol_strings:
        batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch?symbols={symbol_string}&types=quote,advanced-stats&token={IEX_CLOUD_API_TOKEN}'
        data = requests.get(batch_api_call_url).json()
        for symbol in symbol_string.split(','):
            enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
            ebitda = data[symbol]['advanced-stats']['EBITDA']
            gross_profit = data[symbol]['advanced-stats']['grossProfit']
            
            try:
                ev_to_ebitda = enterprise_value/ebitda
            except TypeError:
                ev_to_ebitda = np.NaN
            
            try:
                ev_to_gross_profit = enterprise_value/gross_profit
            except TypeError:
                ev_to_gross_profit = np.NaN
                
            rv_dataframe = rv_dataframe.append(
                pd.Series([
                    symbol,
                    data[symbol]['quote']['latestPrice'],
                    'N/A',
                    data[symbol]['quote']['peRatio'],
                    'N/A',
                    data[symbol]['advanced-stats']['priceToBook'],
                    'N/A',
                    data[symbol]['advanced-stats']['priceToSales'],
                    'N/A',
                    ev_to_ebitda,
                    'N/A',
                    ev_to_gross_profit,
                    'N/A',
                    'N/A'
            ],
            index = rv_columns),
                ignore_index = True
            )

    #Deadling with missing data
    for column in ['Price-to-Earnings Ratio', 'Price-to-Book Ratio','Price-to-Sales Ratio',  'EV/EBITDA','EV/GP']:
        rv_dataframe[column].fillna(rv_dataframe[column].mean(),inplace =True)
    
    metrics = {
            'Price-to-Earnings Ratio': 'PE Percentile',
            'Price-to-Book Ratio':'PB Percentile',
            'Price-to-Sales Ratio': 'PS Percentile',
            'EV/EBITDA':'EV/EBITDA Percentile',
            'EV/GP':'EV/GP Percentile'
    }

    for row in rv_dataframe.index:
        for metric in metrics.keys():
            rv_dataframe.loc[row, metrics[metric]] = stats.percentileofscore(rv_dataframe[metric], rv_dataframe.loc[row, metric])/100

    # Print each percentile score to make sure it was calculated properly
    for metric in metrics.values():
        rv_dataframe[metric]

    from statistics import mean
    for row in rv_dataframe.index:
        value_percentiles = []
        for metric in metrics.keys():
            value_percentiles.append(rv_dataframe.loc[row, metrics[metric]])
        rv_dataframe.loc[row, 'RV Score'] = mean(value_percentiles)

    rv_dataframe.sort_values(by = 'RV Score', inplace = True)
    rv_dataframe = rv_dataframe[:50]
    rv_dataframe.reset_index(drop = True, inplace = True)

    return render(request, 'app/dashboard.html')


def home_view(request):
    return render(request, 'app/home.html')
