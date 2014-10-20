import json
import time
import csv
import numpy as np
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
import pprint

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 

    # 6367 km is the radius of the Earth
    m = 6367 * c * 1000
    return m 

PRIMARY_LOCATION = [40.72539, -74.07099]
SECONDARY_LOCATION = [40.74096, -74.00212]
RADIUS = 500

def isLocPrimary(lat, lon):
    if (haversine(lat, lon, PRIMARY_LOCATION[0], PRIMARY_LOCATION[1]) < RADIUS):
        return True
    else:
        return False

def isLocSecondary(lat, lon):
    if (haversine(lat, lon, SECONDARY_LOCATION[0], SECONDARY_LOCATION[1]) < RADIUS):
        return True
    else:
        return False


def datestring_to_timestamp(dateStr):
    return time.mktime(time.strptime(dateStr, "%Y%m%dT%H%M%S-0400"))

def datestring_to_time_of_day(dateStr):
    datetimeObj = datetime.strptime(dateStr, "%Y%m%dT%H%M%S-0400")
    return datetimeObj.hour * 3600 + datetimeObj.minute * 60 + datetimeObj.second

def mean_time(datetimeObj):
    if filter(None, datetimeObj) == []:
        return ''
    else:
        avg_sec = np.mean(map(datestring_to_time_of_day, filter(None, datetimeObj)))
        return str(int(avg_sec / 3600)) + ':' + str( int(avg_sec % 3600) / 60) + ':' + str(int(avg_sec % 60))

def stdDev_time(datetimeObj):
    if filter(None, datetimeObj) == []:
        return ''
    else:
        avg_sec = np.std(map(datestring_to_time_of_day, filter(None, datetimeObj)))
        return str(int(avg_sec / 3600)) + ':' + str( int(avg_sec % 3600) / 60) + ':' + str(int(avg_sec % 60))

def varDev_time(datetimeObj):
    if filter(None, datetimeObj) == []:
        return ''
    else:
        avg_sec = np.var(map(datestring_to_time_of_day, filter(None, datetimeObj)))
        return str(int(avg_sec / 3600)) + ':' + str( int(avg_sec % 3600) / 60) + ':' + str(int(avg_sec % 60))

def timeSpentPerDay(segments):
    timeSpentDay = {"Time at Home": 0, "Time at Work": 0, "Other": 0}
    for segmentData in segments:
        timeSpent = {"Time at Home": 0, "Time at Work": 0, "Other": 0}
        if segmentData["type"] == 'place':
            stationaryLocation = segmentData["place"]["location"]
            if isLocPrimary(stationaryLocation["lat"], stationaryLocation["lon"]):
                timeSpent["Time at Home"] = int(datestring_to_timestamp(segmentData["endTime"]) - datestring_to_timestamp(segmentData["startTime"]))/60
            elif isLocSecondary(stationaryLocation["lat"], stationaryLocation["lon"]):
                timeSpent["Time at Work"] = int(datestring_to_timestamp(segmentData["endTime"]) - datestring_to_timestamp(segmentData["startTime"]))/60
            else:
                timeSpent["Other"] = int(datestring_to_timestamp(segmentData["endTime"]) - datestring_to_timestamp(segmentData["startTime"]))/60
            timeSpentDay["Time at Home"] += timeSpent["Time at Home"]
            timeSpentDay["Time at Work"] += timeSpent["Time at Work"]
            timeSpentDay["Other"] += timeSpent["Other"]

    return timeSpentDay

def timeLeftPrimaryOrReturned(segments):
    timeLeft = {"Time Left Home": None, "Time Back Home" : None}

    earliestWorkStartTime = None
    homeEndTime = None
    latestWorkEndTime = None
    homeStartTime = None

    # Search work-segments for earliest start time and latest endtime of day
    for segmentData in segments:
        if segmentData["type"] == "place":
            if isLocSecondary(segmentData["place"]["location"]["lat"], segmentData["place"]["location"]["lon"]):
                if latestWorkEndTime == None:
                    latestWorkEndTime = segmentData["endTime"]
                elif datestring_to_timestamp(segmentData["endTime"]) > datestring_to_timestamp(latestWorkEndTime):
                    latestWorkEndTime = segmentData["endTime"]
                if earliestWorkStartTime == None:
                    earliestWorkStartTime = segmentData["startTime"]
                if datestring_to_timestamp(segmentData["startTime"]) < datestring_to_timestamp(earliestWorkStartTime):
                    earliestWorkStartTime = segmentData["startTime"]

    # then the Time Left Home is the endtime of the Latest home segment before it and similarly for Time Back Home
    for segmentData in segments:
        if segmentData["type"] == "place":
            if isLocPrimary(segmentData["place"]["location"]["lat"], segmentData["place"]["location"]["lon"]):
                if earliestWorkStartTime != None and datestring_to_timestamp(segmentData["endTime"]) < datestring_to_timestamp(earliestWorkStartTime):
                    if homeEndTime == None:
                        homeEndTime = segmentData["endTime"]
                    elif datestring_to_timestamp(homeEndTime) < datestring_to_timestamp(segmentData["endTime"]):
                        homeEndTime = segmentData["endTime"]
                if latestWorkEndTime != None and datestring_to_timestamp(latestWorkEndTime) < datestring_to_timestamp(segmentData["startTime"]):
                    if homeStartTime == None:
                        homeStartTime = segmentData["startTime"]
                    elif datestring_to_timestamp(segmentData["startTime"]) < datestring_to_timestamp(homeStartTime):
                        homeStartTime = segmentData["startTime"]

    timeLeft["Time Left Home"] =  None if homeEndTime == None else homeEndTime
    timeLeft["Time Back Home"] =  None if homeStartTime == None else homeStartTime
    return timeLeft

def geoDiameterPerDay(segments):
    # GeoDiameter using stationary Points
    geoDiameter = {"GeoDiameter from Stationary" : 0, "GeoDiameter from All" : 0}
    for firstSegmentData in segments:
        if firstSegmentData["type"] == 'place':
            firstLocation = firstSegmentData["place"]["location"]
            for secondSegmentData in segments:
                if secondSegmentData["type"] == 'place':
                    secondLocation = secondSegmentData["place"]["location"]
                    distance = haversine(firstLocation["lat"], firstLocation["lon"], secondLocation["lat"], secondLocation["lon"])
                    if distance > geoDiameter["GeoDiameter from Stationary"]:
                        geoDiameter["GeoDiameter from Stationary"] = distance

    # geoDiameter using Track Points and stationary Points
    locationPoints = []

    # Parse to get a list of Location points
    for segmentData in segments:
        if segmentData["type"] == 'place':
            locationPoints.append(segmentData["place"]["location"])
        elif segmentData["type"] == 'move':
            for activity in segmentData["activities"]:
                locationPoints += activity["trackPoints"]

    # Compare Distance by brute-force
    for pointA in locationPoints:
        for pointB in locationPoints:
            distance = haversine(pointA["lat"], pointA["lon"], pointB["lat"], pointB["lon"])
            if  distance > geoDiameter["GeoDiameter from All"]:
                geoDiameter["GeoDiameter from All"] = distance

    return geoDiameter

def isAnomaly(value, mean , stdDev):
    if type(mean) == str:
        meanDT = datetime.strptime(mean,'%H:%M:%S')
        mean = meanDT.hour * 3600 + meanDT.minute * 60 + meanDT.second
        stdDevDT = datetime.strptime(stdDev,'%H:%M:%S')
        stdDev = stdDevDT.hour * 3600 + stdDevDT.minute * 60 + stdDevDT.second

    if mean - 2*stdDev < value < mean + 2* stdDev:
        return True
    else:
        return False

def anomalyAnalysis(records, meanStats, stdDevStats, headers):

    recordsFiltered = records[1:-1]
    headersFiltered = headers[1:-1]
    for i in xrange(len(meanStats["Overall"])):
        print recordsFiltered[i], meanStats["Overall"][i], stdDevStats["Overall"][i]
        if isAnomaly(recordsFiltered[i], meanStats["Overall"][i], stdDevStats["Overall"][i]):
            records.append('Yes')
            if records[8] == "Weekday":
                if isAnomaly(recordsFiltered[i], meanStats["Weekday"][i], stdDevStats["Weekday"][i]):
                    records.append(headers[i+1])
                else:
                    records.append('Weekday Model Explains it')
            elif records[8] == "Weekend":
                if isAnomaly(recordsFiltered[i], meanStats["Weekend"][i], stdDevStats["Weekend"][i]):
                    records.append(headers[i+1])
                else:
                    records.append('Weekend Model Explains it')
            return records

    records += ['No','N/A']
    return records




def main():
    jsonData = json.load(open('processed.json'))
    aggregateStats = []
    meanStats = {"Overall": [], "Weekday": [], "Weekend": []}
    stdDevStats = {"Overall": [], "Weekday": [], "Weekend": []}
    varDevStats = {"Overall": [], "Weekday": [], "Weekend": []}
    varianceStats = []

    timeLeft = []
    timeBack = []
    geoDiameter = []
    timeSpent = []


    timeLeftWeekday = []
    timeBackWeekday = []
    geoDiameterWeekday = []
    timeSpentWeekday = []

    timeLeftWeekend = []
    timeBackWeekend = []
    geoDiameterWeekend = []
    timeSpentWeekend = []


    for dayJson in jsonData:
        perDayStats = []
        dateObject = datetime.strptime(dayJson["date"], "%Y%m%d")
        typeOfday = 'Weekday' if dateObject.weekday() < 5 else 'Weekend'

        perDayStats.append(dayJson["date"][:8])
        print dayJson["date"][:8]

        segments = dayJson['segments']

        if segments != None:
            perDayStats += (timeSpentPerDay(segments).values())
            perDayStats += (timeLeftPrimaryOrReturned(segments).values())
            perDayStats += (geoDiameterPerDay(segments).values())

            timeLeft.append(timeLeftPrimaryOrReturned(segments).values()[0])
            timeBack.append(timeLeftPrimaryOrReturned(segments).values()[1])
            geoDiameter.append(geoDiameterPerDay(segments).values())
            timeSpent.append(timeSpentPerDay(segments).values())

            if typeOfday == 'Weekday':
                timeLeftWeekday.append(timeLeftPrimaryOrReturned(segments).values()[0])
                timeBackWeekday.append(timeLeftPrimaryOrReturned(segments).values()[1])
                geoDiameterWeekday.append(geoDiameterPerDay(segments).values())
                timeSpentWeekday.append(timeSpentPerDay(segments).values())
            else:
                timeLeftWeekend.append(timeLeftPrimaryOrReturned(segments).values()[0])
                timeBackWeekend.append(timeLeftPrimaryOrReturned(segments).values()[1])
                geoDiameterWeekend.append(geoDiameterPerDay(segments).values())
                timeSpentWeekend.append(timeSpentPerDay(segments).values())
        else:
            perDayStats += ['', '', '', '', '', '', '']
        perDayStats.append(typeOfday)
        aggregateStats.append(perDayStats)

    # Compute Aggregate Stats
    meanStats["Overall"] = np.mean(timeSpent, axis = 0).tolist()
    meanStats["Overall"].append(mean_time(timeLeft))
    meanStats["Overall"].append(mean_time(timeBack))
    meanStats["Overall"] += np.mean(geoDiameter, axis = 0).tolist()

    meanStats["Weekday"] = np.mean(timeSpentWeekday, axis = 0).tolist()
    meanStats["Weekday"].append(mean_time(timeLeftWeekday))
    meanStats["Weekday"].append(mean_time(timeBackWeekday))
    meanStats["Weekday"] += np.mean(geoDiameterWeekday, axis = 0).tolist()

    meanStats["Weekend"] = np.mean(timeSpentWeekend, axis = 0).tolist()
    meanStats["Weekend"].append(mean_time(timeLeftWeekend))
    meanStats["Weekend"].append(mean_time(timeBackWeekend))
    meanStats["Weekend"] += np.mean(geoDiameterWeekend, axis = 0).tolist()

    stdDevStats["Overall"] = np.std(timeSpent, axis = 0).tolist()
    stdDevStats["Overall"].append(stdDev_time(timeLeft))
    stdDevStats["Overall"].append(stdDev_time(timeBack))
    stdDevStats["Overall"] += np.std(geoDiameter, axis = 0).tolist()


    stdDevStats["Weekday"] = np.std(timeSpentWeekday, axis = 0).tolist()
    stdDevStats["Weekday"].append(stdDev_time(timeLeftWeekday))
    stdDevStats["Weekday"].append(stdDev_time(timeBackWeekday))
    stdDevStats["Weekday"] += np.std(geoDiameterWeekday, axis = 0).tolist()

    stdDevStats["Weekend"] = np.std(timeSpentWeekend, axis = 0).tolist()
    stdDevStats["Weekend"].append(stdDev_time(timeLeftWeekend))
    stdDevStats["Weekend"].append(stdDev_time(timeBackWeekend))
    stdDevStats["Weekend"] += np.std(geoDiameterWeekend, axis = 0).tolist()

    varDevStats["Overall"] = np.var(timeSpent, axis = 0).tolist()
    varDevStats["Overall"].append(varDev_time(timeLeft))
    varDevStats["Overall"].append(varDev_time(timeBack))
    varDevStats["Overall"] += np.var(geoDiameter, axis = 0).tolist()


    varDevStats["Weekday"] = np.var(timeSpentWeekday, axis = 0).tolist()
    varDevStats["Weekday"].append(varDev_time(timeLeftWeekday))
    varDevStats["Weekday"].append(varDev_time(timeBackWeekday))
    varDevStats["Weekday"] += np.var(geoDiameterWeekday, axis = 0).tolist()

    varDevStats["Weekend"] = np.var(timeSpentWeekend, axis = 0).tolist()
    varDevStats["Weekend"].append(varDev_time(timeLeftWeekend))
    varDevStats["Weekend"].append(varDev_time(timeBackWeekend))
    varDevStats["Weekend"] += np.var(geoDiameterWeekend, axis = 0).tolist()

    headers = ['Day', 'Time at Work', 'Time at Home', 'Other Time', 'Time Left Home', 'Time Back Home', 'Geodiameter(place coordinates)', 'Geodiameter(All coordinates)', 'Weekday', 'Anomaly', 'Anomaly Reason']

    aggregateStats = [ anomalyAnalysis(aggregateStat, meanStats, stdDevStats, headers) for aggregateStat in aggregateStats]
    with open('LocationTraceAnalysis.csv', 'wb') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(aggregateStats)
        writer.writerow(['Mean over all'] + meanStats["Overall"])
        writer.writerow(['Std Dev over all'] + stdDevStats["Overall"])
        writer.writerow(['Var over all'] + varDevStats["Overall"]) 
        writer.writerow(['Mean over Weekdays'] + meanStats["Weekday"])
        writer.writerow(['Std Dev over Weekdays'] + stdDevStats["Weekday"])
        writer.writerow(['Var over Weekdays'] + varDevStats["Weekday"])        
        writer.writerow(['Mean over WeekEnds'] + meanStats["Weekend"])
        writer.writerow(['Std Dev over WeekEnds'] + stdDevStats["Weekend"])
        writer.writerow(['Var over WeekEnds'] + varDevStats["Weekend"])

if __name__ == "__main__":
    # plot_topic_words()
    main()