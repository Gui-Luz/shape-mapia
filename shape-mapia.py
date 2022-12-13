# -*- coding: utf-8 -*-
# V1.4

import urllib3
import json
import webbrowser
import math
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterString,
                       QgsProcessingParameterFeatureSink,
                       QgsFeature,
                       QgsGeometry,
                       QgsPointXY,
                       QgsWkbTypes,
                       QgsField,
                       QgsFields,
                       QgsCoordinateReferenceSystem)
from qgis.utils import iface


class ShapeMapia(QgsProcessingAlgorithm):
    WIKI_ID = 'WIKI_ID'
    WIKI_KEY = 'WIKI_KEY'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ShapeMapia()

    def name(self):

        return 'shapemapia'

    def displayName(self):

        return self.tr('Shapemapia')

    def group(self):

        return self.tr('My tools')

    def groupId(self):

        return 'mytools'

    def shortHelpString(self):

        return self.tr(
            """
            Shapemapia is a python script that helps you extract shapes from wikimapia.com an import it into QGIS.
            """)

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterString(
                self.WIKI_ID,
                self.tr('Wikimapia id')
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.WIKI_KEY,
                self.tr('Wikimapia api key'),
                defaultValue=''
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):

        log = feedback.setProgressText
        input_title = self.parameterAsString(parameters, self.WIKI_ID, context)
        input_key = self.parameterAsString(parameters, self.WIKI_KEY, context)

        if input_title is None or input_key is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.WIKI_ID))

        http = urllib3.PoolManager()
        key = input_key
        id = input_title
        url = f"http://api.wikimapia.org/?key={key}&function=place.getbyid&id={id}&format=json&language=en"
        r = http.request('GET', url)
        if r.status != 200:
            raise Exception(r.status)

        j = json.loads(r.data.decode('utf-8'))

        try:
            title = j["title"]
            description = j["description"]
            country = j["location"]["country"]
            state = j["location"]["state"]
            place = j["location"]["place"]
            lat = j["location"]["lat"]
            lon = j["location"]["lon"]

            x = [x['x'] for x in j['polygon']]
            y = [y['y'] for y in j['polygon']]
            tuples = (zip(x, y))
            coordinates = [list(item) for item in tuples]

            feature = QgsFeature()
            feature.setGeometry(
                QgsGeometry.fromPolygonXY([[QgsPointXY(pair[0], pair[1]) for pair in coordinates]])
            )

            new_fields = QgsFields()
            new_fields.append(QgsField('title', QVariant.String))
            new_fields.append(QgsField('description', QVariant.String))
            new_fields.append(QgsField('country', QVariant.String))
            new_fields.append(QgsField('state', QVariant.String))
            new_fields.append(QgsField('place', QVariant.String))
            new_fields.append(QgsField('lat', QVariant.String))
            new_fields.append(QgsField('lon', QVariant.String))
            feature.setFields(new_fields)
            feature.setAttributes([title, description, country, state, place, lat, lon])

            (sink, dest_id) = self.parameterAsSink(
                parameters,
                self.OUTPUT,
                context,
                feature.fields(),
                QgsWkbTypes.Polygon,
                QgsCoordinateReferenceSystem("EPSG:4326")
            )

            sink.addFeature(feature, QgsFeatureSink.FastInsert)

        except Exception as e:
            raise Exception(e)

        return {self.OUTPUT: dest_id}

    def calculate_zoom_level(self):
        scale = iface.mapCanvas().scale()
        dpi = iface.mainWindow().physicalDpiX()
        maxScalePerPixel = 156543.04
        inchesPerMeter = 39.37
        zoomlevel = int(round(math.log(((dpi * inchesPerMeter * maxScalePerPixel) / scale), 2), 0)) - 1
        return zoomlevel

    def open_website(self):
        zoom = self.calculate_zoom_level()
        canvas_center = iface.mapCanvas().extent().center()
        webbrowser.open(f'https://wikimapia.org/#lang=pt&lat={canvas_center[1]}&lon={canvas_center[0]}&z={zoom}&m=w')
