import json
import time
import numpy as np
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

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
RADIUS = 2000

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

def timeSpentAtPointOfInterest(segmentData):
    timeSpent = {"home": 0, "work": 0, "other": 0}
    if segmentData["type"] == 'place':
        stationaryLocation = segmentData["place"]["location"]
        if isLocPrimary(stationaryLocation["lat"], stationaryLocation["lon"]):
            timeSpent["home"] = minuteTransform(segmentData["endTime"]) - minuteTransform(segmentData["startTime"])
        elif isLocSecondary(stationaryLocation["lat"], stationaryLocation["lon"]):
            timeSpent["work"] = minuteTransform(segmentData["endTime"]) - minuteTransform(segmentData["startTime"])
        else:
            timeSpent["other"] = minuteTransform(segmentData["endTime"]) - minuteTransform(segmentData["startTime"])
    return timeSpent

def main():
    jsonData = json.load(open('processed.json'))
    for dayJson in jsonData:
        dateObject = datetime.strptime(dayJson["date"], "%Y%m%d")
        typeOfday = 'Weekday' if dateObject.weekday() < 5 else 'Weekend'
        print typeOfday

        segments = dayJson['segments']

        if segments != None:
            timeSpentDay = {"home": 0, "work": 0, "other": 0}
            timeLeft = {"home4work": 0, "work4home": 0}
            timeLeftPrimartyLocation = []

            for segmentData in segments:
                timeSpentSegment = timeSpentAtPointOfInterest(segmentData)
                timeSpentDay["home"] += timeSpentSegment["home"]
                timeSpentDay["work"] += timeSpentSegment["work"]
                timeSpentDay["other"] += timeSpentSegment["other"]
            print timeSpentDay


            for segmentGroupData in zip(segments[:-2], segments[1:-1], segments[2:]):
                if segmentGroupData[0]["type"] == 'place' and segmentGroupData[1]["type"] == 'move' and segmentGroupData[2]["type"] == "place":
                    startLocation = segmentGroupData[0]["place"]["location"]
                    endLocation = segmentGroupData[2]["place"]["location"]
                    if isLocPrimary(startLocation["lat"], startLocation["lon"]) and isLocSecondary(endLocation["lat"], endLocation["lon"]):
                        print "LeftHome@ " + segmentGroupData[0]["endTime"]

                    if isLocPrimary(endLocation["lat"], endLocation["lon"]) and isLocSecondary(startLocation["lat"], startLocation["lon"]):
                        print "LeftWork@ " + segmentGroupData[0]["endTime"]


            # GeoDiameter
            GeoDiameter = 0
            for firstSegmentData in segments:
                if firstSegmentData["type"] == 'place':
                    firstLocation = firstSegmentData["place"]["location"]
                    for secondSegmentData in segments:
                        if secondSegmentData["type"] == 'place':
                            secondLocation = secondSegmentData["place"]["location"]
                            distance = haversine(firstLocation["lat"], firstLocation["lon"], secondLocation["lat"], secondLocation["lon"])
                            if distance > GeoDiameter:
                                GeoDiameter = distance

            print GeoDiameter





if __name__ == "__main__":
    # plot_topic_words()
    main()