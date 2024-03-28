from django.shortcuts import render
from json import load, loads
import urllib.request
from unidecode import unidecode

from openmeteo_py import OWmanager
from openmeteo_py.Daily.DailyHistorical import DailyHistorical
from openmeteo_py.Options.HistoricalOptions import HistoricalOptions
from openmeteo_py.Daily.DailyForecast import DailyForecast
from openmeteo_py.Options.ForecastOptions import ForecastOptions
from openmeteo_py.Utils.constants import *

from datetime import date
from statistics import median
from geopy.geocoders import Nominatim
from dateutil.relativedelta import relativedelta 

def most_common(lst):
    return max(set(lst), key=lst.count)

def get_info_historical(info, options):
    mgr = OWmanager(options,OWmanager.historical,None,info)
    meteo = mgr.get_data(1)
    return meteo

def get_info_forecast(info, options):
    mgr = OWmanager(options,OWmanager.forecast,None,info)
    meteo = mgr.get_data(1)
    return meteo

def decoder(forecast):
    with open('static/description.json', encoding='utf-8') as f:
        d = load(f)
        image = d[str(forecast)]["day"]["image"]
        forecast = d[str(forecast)]["day"]["description"]
    return forecast, image 


def index(request):
    if request.method == 'POST':
        city = request.POST['city']

        city = ''.join(e for e in city if e.isalnum() or e == " ")  #Cleaning city string
        city = city.replace(" ", "%20")
        city = unidecode(city)

        res = urllib.request.urlopen(
            'http://api.openweathermap.org/data/2.5/weather?q=' + city + '&appid=f7e7230efe7bac79d2f4d45f747d544e&lang=fr&units=metric').read()
        json_data = loads(res)
        description = json_data['weather'][0]['description']

        city = city.replace("%20", " ")

        geolocator = Nominatim(user_agent='skyezoff')
        location = geolocator.geocode(city, exactly_one=True, language="fr", namedetails=True, addressdetails=True)
        latitude = float(location.raw["lat"])
        longitude = float(location.raw["lon"])
        country = str(location.raw['address']['country'])

        date_1 = date.today() + relativedelta(days=1)
        date_2 = date_1 + relativedelta(days = 1)
        weather_ten_years=[]
        weather_four_days=[]

        temperature_low_ten_years=[]
        temperature_low_four_days=[]

        temperature_high_ten_years=[]
        temperature_high_four_days=[]

        meteo_forecast = get_info_forecast(DailyForecast().all(), ForecastOptions(latitude,longitude,False,celsius,kmh,mm,iso8601,utc,0))

        for i in range(1,11):
            meteo = get_info_historical(DailyHistorical().all(), HistoricalOptions(latitude,longitude,nan,False,celsius,kmh,mm,iso8601,utc,date_1 - relativedelta(years = i),date_2 - relativedelta(years = i)))
            weather_ten_years.append(meteo["daily"]["weathercode"][str(date_1 - relativedelta(years = i))])
            temperature_low_ten_years.append(meteo["daily"]["temperature_2m_min"][str(date_1 - relativedelta(years = i))])
            temperature_high_ten_years.append(meteo["daily"]["temperature_2m_max"][str(date_1 - relativedelta(years = i))])

        meteo = get_info_forecast(DailyForecast().all(), ForecastOptions(latitude,longitude,False,celsius,kmh,mm,iso8601,utc,1))
        weather_four_days.append(meteo["daily"]["weathercode"][str(date_1 - relativedelta(days = 2))])
        temperature_low_four_days.append(meteo["daily"]["temperature_2m_min"][str(date_1 - relativedelta(days = 2))])
        temperature_high_four_days.append(meteo["daily"]["temperature_2m_max"][str(date_1 - relativedelta(days = 2))])

        for i in range(3,6):
            meteo = get_info_historical(DailyHistorical().all(), HistoricalOptions(latitude,longitude,nan,False,celsius,kmh,mm,iso8601,utc,date_1 - relativedelta(days = i),date_2 - relativedelta(days = i)))
            weather_four_days.append(meteo["daily"]["weathercode"][str(date_1 - relativedelta(days = i))])
            temperature_low_four_days.append(meteo["daily"]["temperature_2m_min"][str(date_1 - relativedelta(days = i))])
            temperature_high_four_days.append(meteo["daily"]["temperature_2m_max"][str(date_1 - relativedelta(days = i))])

        temperature_high = temperature_high_ten_years + temperature_high_four_days*2
        temperature_low = temperature_low_ten_years + temperature_low_four_days*2
        weather = weather_ten_years + weather_four_days*2
        algo_forecast = most_common(weather)
        algo_forecast, algo_forecast_image = decoder(algo_forecast)
        actual_forecast, actual_forecast_image = decoder(meteo_forecast["daily"]["weathercode"][str(date_1)])

        data = {
            "description": str(description.upper()),
            "temp": str(round(json_data['main']['temp'], 1)) + "°C",
            "feels_like": str(round(json_data['main']['feels_like'], 1)) + "°C",
            "wind": str(round(json_data['wind']['speed']*3.6, 1)) + " Km/h",
            "humidity": str(json_data['main']['humidity']) + "%",
            "precipitation": str(json_data['clouds']['all']) + "%",
            "image": "http://openweathermap.org/img/wn/" + str(json_data["weather"][0]["icon"]) + "@2x.png",
            'algo_forecast': algo_forecast,
            'algo_forecast_image': algo_forecast_image,
            'algo_temp_min': str(round(median(temperature_low), 1)) + "°C",
            'algo_temp_max': str(round(median(temperature_high), 1)) + "°C",
            'actual_forecast': actual_forecast,
            'actual_forecast_image': actual_forecast_image,
            'actual_temp_min': str(round(meteo_forecast["daily"]["temperature_2m_min"][str(date_1)],1)) + "°C",
            'actual_temp_max': str(round(meteo_forecast["daily"]["temperature_2m_max"][str(date_1)],1)) + "°C",
            'date' : str(f"{(date.today() + relativedelta(days=1)).day}/{(date.today() + relativedelta(days=1)).month}")
        }

        temperature_ten_years = []
        for i in range(len(temperature_high_ten_years)):
            temp = round((temperature_high_ten_years[i]+temperature_low_ten_years[i])/2,1)
            year = date.today().year
            temperature_ten_years.append((year-i-1, temp))

        minimum = min(temperature_ten_years, key=lambda t: t[1])
        maximum = max(temperature_ten_years, key=lambda t: t[1])   
        minimum = minimum[1]
        maximum = maximum[1]

        chart = {
            "year_0": str(temperature_ten_years[0][0]),
            "year_1": str(temperature_ten_years[1][0]),
            "year_2": str(temperature_ten_years[2][0]),
            "year_3": str(temperature_ten_years[3][0]),
            "year_4": str(temperature_ten_years[4][0]),
            "year_5": str(temperature_ten_years[5][0]),
            "year_6": str(temperature_ten_years[6][0]),
            "year_7": str(temperature_ten_years[7][0]),
            "year_8": str(temperature_ten_years[8][0]),

            "temp_0": str(temperature_ten_years[0][1]),
            "temp_1": str(temperature_ten_years[1][1]),
            "temp_2": str(temperature_ten_years[2][1]),
            "temp_3": str(temperature_ten_years[3][1]),
            "temp_4": str(temperature_ten_years[4][1]),
            "temp_5": str(temperature_ten_years[5][1]),
            "temp_6": str(temperature_ten_years[6][1]),
            "temp_7": str(temperature_ten_years[7][1]),
            "temp_8": str(temperature_ten_years[8][1]),

            "coeff_0": str(round(0.1+(0.8*(temperature_ten_years[0][1]-minimum))/(maximum-minimum),2)),
            "coeff_1": str(round(0.1+(0.8*(temperature_ten_years[1][1]-minimum))/(maximum-minimum),2)),
            "coeff_2": str(round(0.1+(0.8*(temperature_ten_years[2][1]-minimum))/(maximum-minimum),2)),
            "coeff_3": str(round(0.1+(0.8*(temperature_ten_years[3][1]-minimum))/(maximum-minimum),2)),
            "coeff_4": str(round(0.1+(0.8*(temperature_ten_years[4][1]-minimum))/(maximum-minimum),2)),
            "coeff_5": str(round(0.1+(0.8*(temperature_ten_years[5][1]-minimum))/(maximum-minimum),2)),
            "coeff_6": str(round(0.1+(0.8*(temperature_ten_years[6][1]-minimum))/(maximum-minimum),2)),
            "coeff_7": str(round(0.1+(0.8*(temperature_ten_years[7][1]-minimum))/(maximum-minimum),2)),
            "coeff_8": str(round(0.1+(0.8*(temperature_ten_years[8][1]-minimum))/(maximum-minimum),2)),
            "coeff_9": str(round(0.1+(0.8*(temperature_ten_years[9][1]-minimum))/(maximum-minimum),2)),
        }  

        #Formule du coefficient: 0.1+(0.8x(T-Tmin))/(Tmax-Tmin)

    else:
        city = ''
        country = ''
        data = {}
        chart = {}

    return render(request, 'meteo/main.html', {'city': city, 'country': country, 'data': data, 'chart': chart})
    
