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
    for segmentGroupData in zip(segments[:-2], segments[1:-1], segments[2:]):
        # for each sequence of 3 segments check if the 1st and 3rd segment is a place and 2nd is a move
        if segmentGroupData[0]["type"] == 'place' and segmentGroupData[1]["type"] == 'move' and segmentGroupData[2]["type"] == "place":
            startLocation = segmentGroupData[0]["place"]["location"]
            endLocation = segmentGroupData[2]["place"]["location"]
            if isLocPrimary(startLocation["lat"], startLocation["lon"]) and isLocSecondary(endLocation["lat"], endLocation["lon"]):
                timeLeft["Time Left Home"] =  datetime.strptime(segmentGroupData[0]["endTime"], "%Y%m%dT%H%M%S-0400")

            if isLocPrimary(endLocation["lat"], endLocation["lon"]) and isLocSecondary(startLocation["lat"], startLocation["lon"]):
                timeLeft["Time Back Home"] =  datetime.strptime(segmentGroupData[2]["endTime"], "%Y%m%dT%H%M%S-0400")
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
    meanStats.append(np.mean(filter(None, timeLeftWeekday), axis = 0))
    pprint.pprint(meanStats)
    with open('LocationAnalysis.csv', 'wb') as f:
        writer = csv.writer(f)
        writer.writerows(aggregateStats)
        writer.writerows(meanStats)

if __name__ == "__main__":
    # plot_topic_words()
    main()