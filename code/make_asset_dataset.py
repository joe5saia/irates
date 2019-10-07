###############################################################################
"""  
make_series_dataset.py
Author: Joe Saia

Description: This script assembles a dataset with data from Bloomberg, FRED
and the Federal Reserve BOG website. The Bloomberg data needs to be supplied,
the other data will be automatically pulled and updated. 

Inputs: data/raw/bloomberg should have excel sheets with the series and
additional information.

Outputs: data/processed/prices.csv and data/processed/returns.csv. CSV files
with a column for the time series of each asset. Either for prices or returns.
Returns are either log differences or level differences based on how the asset
is quoted.
"""
###############################################################################

import xml.etree.ElementTree as ET
import xml
import zipfile
import urllib.request
import pandas as pd
import re
import datetime as dt
from datetime import datetime as dtdt
from fredapi import Fred
import os


def read_bloom(f, dir):
    """
    function to read in bloomberg data
    Inputs:
        dir - Directory where data is saved
        f - file name
    Returns: pandas dataframe with date and Last Price columns
    """
    data = pd.read_excel(dir + f, usecols=1, index_col=0, names=['Last Price'])
    data.index = pd.DatetimeIndex(data.index)
    data = data.resample('B').asfreq()
    sname = re.sub(r"\.xlsx", "", f)
    sname = re.sub(r"^(\s+)", "", sname)
    sname = re.sub(r" COMDTY", "", sname)
    sname = re.sub(r" CURNCY", "", sname)
    sname = re.sub(r" Index", "", sname)
    return data.rename(index=str, columns={'Last Price': sname})


def bloom(dir):
    # Read in data and merge
    bloom_files = os.listdir(dir)
    print(bloom_files)
    data = read_bloom(bloom_files[0], dir)
    for f in bloom_files[1:]:
        print('Reading in ' + f)
        tmp = read_bloom(f, dir)
        data = data.merge(tmp, how='outer', left_index=True, right_index=True)
    data.index = pd.DatetimeIndex(data.index, freq='B')
    return data


def gss():
    ################################################################################
    # Download GSS data on forward rates and extract them to DataFrame. These are Nominal Bonds
    ################################################################################
    url = 'https://www.federalreserve.gov/econresdata/researchdata/feds200628.zip'
    urllib.request.urlretrieve(url, 'data/feds200628.zip')
    with zipfile.ZipFile("data/feds200628.zip", 'r') as zip_ref:
        zip_ref.extractall('data')

    # Read XML data into a dataframe and the save as CSV
    tree = ET.parse('data/feds200628.xml')
    root = tree.getroot()
    # Each child [j] is a yieldcurve type - maturity. Loop over all of them
    data = pd.DataFrame({root[1][j].attrib['SERIES_NAME']: pd.Series([x.attrib['OBS_VALUE'] for x in root[1][j][1:]], [
                        x.attrib['TIME_PERIOD'] for x in root[1][j][1:]], dtype='float64') for j in range(93)})
    data.index = pd.DatetimeIndex(data.index)
    return data


def gsw():
    ################################################################################
    # Download GSW data on forward rates and extract them to DataFrame. These are TIPS
    ################################################################################
    url = 'https://www.federalreserve.gov/econresdata/researchdata/feds200805.zip'
    urllib.request.urlretrieve(url, 'data/feds200805.zip')
    with zipfile.ZipFile("data/feds200805.zip", 'r') as zip_ref:
        zip_ref.extractall('data')

    # Read XML data into a dataframe and the save as CSV
    tree = ET.parse('data/feds200805.xml')
    root = tree.getroot()
    # Each child [j] is a yieldcurve type - maturity. Loop over all of them
    data = pd.DataFrame({root[1][j].attrib['SERIES_NAME']: pd.Series([x.attrib['OBS_VALUE'] for x in root[1][j][1:]], [
                        x.attrib['TIME_PERIOD'] for x in root[1][j][1:]], dtype='float64') for j in range(120)})
    data.index = pd.DatetimeIndex(data.index)
    data = data.resample('B').asfreq()
    return data


def exrates(fred):
    ################################################################################
    # Download exchange rate data from FRED
    # inputs: fred is a Fred object from the fredapi module
    ################################################################################
    xrates = ['DTWEXM', 'DEXUSEU', 'DEXJPUS',
              'DEXUSUK', 'DEXCAUS', 'DEXMXUS', 'DEXUSAL']
    data = pd.DataFrame({s: fred.get_series(s) for s in xrates})
    data.index = pd.DatetimeIndex(data.index)
    data = data.resample('B').asfreq()
    return data


def fredirates(fred):
    ################################################################################
    # Download interest rate data from FRED
    # inputs: fred is a Fred object from the fredapi module
    ################################################################################
    irates = ['AAA', 'BAA', 'FEDFUNDS',
              'DFEDTARU', 'DFEDTARL', 'DFEDTAR', 'DCPN3M', 'DCPF3M']
    data = pd.DataFrame({s: fred.get_series(s) for s in irates})
    data.index = pd.DatetimeIndex(data.index)
    data = data.resample('B').asfreq()
    # Before December 2008 the fed had a single target, after they had a range
    # upper and lower are missing before 2008, set them equal to the point target
    data['DFEDTARU'].fillna(data['DFEDTAR'], inplace=True)
    data['DFEDTARL'].fillna(data['DFEDTAR'], inplace=True)
    return data


def main():
    # Read in all the data, join, and standarize the column names
    dfbloom = bloom('/app/bloomberg/')
    dfgss = gss()
    dfgsw = gsw()
    fred = Fred('5240bbe3851ef2d1aaffd0877d6048dd')
    dfxrates = exrates(fred)
    dfirates = fredirates(fred)
    df = pd.concat([dfbloom, dfgss, dfgsw, dfxrates,
                    dfirates], join='outer', axis=1)
    df.columns = map(str.upper, df.columns)

    # Convert Eurodollar quotes to implied interest rate
    df.loc[:, "ED1"] = 100 - df["ED1"]
    df.loc[:, "ED2"] = 100 - df["ED2"]
    df.loc[:, "ED3"] = 100 - df["ED3"]

    # These vars will have growth rates as X_2-X_1
    rates = ["ED1", "ED2", "ED3"]
    rates.extend(dfgss.columns)
    rates.extend(dfgsw.columns)
    rates.extend(dfirates.columns)

    # These vars will have growth rates as (X_2-X_1)/X_1
    levels = list(set(df.columns).difference(rates))

    # Calculate growth rates for each group and combine
    dflevels = df[levels].pct_change(periods=1, fill_method=None)
    dfrates = df[rates].pct_change(periods=1, fill_method=None)
    dfchange = pd.concat([dflevels, dfrates], join='outer', axis=1)
    dfchange.to_csv('/app/output/returns.csv')
    df.to_csv('/app/output/prices.csv')


main()
