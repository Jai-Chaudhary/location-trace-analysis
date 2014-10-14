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


def minuteTransform(dateStr):
    struct_time = time.strptime(dateStr, "%Y%m%dT%H%M%S-0400")
    return int(time.mktime(struct_time))/60

def timeSpentPerDay(segments):
    timeSpentDay = {"Time at Home": 0, "Time at Work": 0, "Other": 0}
    for segmentData in segments:
        timeSpent = {"Time at Home": 0, "Time at Work": 0, "Other": 0}
        if segmentData["type"] == 'place':
            stationaryLocation = segmentData["place"]["location"]
            if isLocPrimary(stationaryLocation["lat"], stationaryLocation["lon"]):
                timeSpent["Time at Home"] = minuteTransform(segmentData["endTime"]) - minuteTransform(segmentData["startTime"])
            elif isLocSecondary(stationaryLocation["lat"], stationaryLocation["lon"]):
                timeSpent["Time at Work"] = minuteTransform(segmentData["endTime"]) - minuteTransform(segmentData["startTime"])
            else:
                timeSpent["Other"] = minuteTransform(segmentData["endTime"]) - minuteTransform(segmentData["startTime"])
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
                elif minuteTransform(segmentData["endTime"]) > minuteTransform(latestWorkEndTime):
                    latestWorkEndTime = segmentData["endTime"]
                if earliestWorkStartTime == None:
                    earliestWorkStartTime = segmentData["startTime"]
                if minuteTransform(segmentData["startTime"]) < minuteTransform(earliestWorkStartTime):
                    earliestWorkStartTime = segmentData["startTime"]

    # then the Time Left Home is the endtime of the Latest home segment before it and similarly for Time Back Home
    for segmentData in segments:
        if segmentData["type"] == "place":
            if isLocPrimary(segmentData["place"]["location"]["lat"], segmentData["place"]["location"]["lon"]):
                if earliestWorkStartTime != None and minuteTransform(segmentData["endTime"]) < minuteTransform(earliestWorkStartTime):
                    if homeEndTime == None:
                        homeEndTime = segmentData["endTime"]
                    elif minuteTransform(homeEndTime) < minuteTransform(segmentData["endTime"]):
                        homeEndTime = segmentData["endTime"]
                if latestWorkEndTime != None and minuteTransform(latestWorkEndTime) < minuteTransform(segmentData["startTime"]):
                    if homeStartTime == None:
                        homeStartTime = segmentData["startTime"]
                    elif minuteTransform(segmentData["startTime"]) < minuteTransform(homeStartTime):
                        homeStartTime = segmentData["startTime"]

    timeLeft["Time Left Home"] =  None if homeEndTime == None else datetime.strptime(homeEndTime, "%Y%m%dT%H%M%S-0400")
    timeLeft["Time Back Home"] =  None if homeStartTime == None else datetime.strptime(homeStartTime, "%Y%m%dT%H%M%S-0400")
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


def main():
    jsonData = json.load(open('processed.json'))
    aggregateStats = []
    meanStats = []
    varianceStats = []
    stdDevStats =[]

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
        perDayStats.append(typeOfday)

        segments = dayJson['segments']

        if segments != None:
            perDayStats += (timeSpentPerDay(segments).values())
            perDayStats += (timeLeftPrimaryOrReturned(segments).values())
            perDayStats += (geoDiameterPerDay(segments).values())

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


        aggregateStats.append(perDayStats)

    # Compute Aggregate Stats
    meanStats.append(np.mean(geoDiameterWeekday, axis = 0))
    meanStats.append(np.mean(timeSpentWeekday, axis = 0))
    # meanStats.append(sum(filter(None, timeLeftWeekday), axis = 0))
    pprint.pprint(meanStats)
    with open('LocationTraceAnalysis.csv', 'wb') as f:
        writer = csv.writer(f)
        writer.writerow(['Day', 'Weekday', 'Time at Home', 'Time at Work', 'Other Time', 'Time Left Home', 'Time Back Home', 'Geodiameter'])
        writer.writerows(aggregateStats)
        writer.writerows(meanStats)

if __name__ == "__main__":
    # plot_topic_words()
    main()