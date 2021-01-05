import sys
import os
import numpy as np
import cv2
import PIL
from picamera import PiCamera
import RPi.GPIO as GPIO
import matplotlib
import time
from time import sleep
import scipy
from scipy.signal import find_peaks, peak_widths, peak_prominences
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import NumericProperty, StringProperty, ListProperty
from kivy.lang import Builder
from random import random
import matplotlib.pyplot as plt
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.config import Config
from kivy.uix.popup import Popup
from kivy.uix.dropdown import DropDown
from datetime import date, datetime, timezone
# import sqlite3
from subprocess import call
import base64
from dotenv import load_dotenv
from boto3

#=============================================================================
load_dotenv() # LOAD .env file

dynamo_client = boto3.client('dynamodb')
dynamo_db = boto3.resource('dynamodb')

# CHECK FOR EXACT TABLE
for tableName in dynamo_client.list_tables()['TableNames']:
	if(tableName.split('-')[0] == "Requisiton"):
		req_table = dynamo_db.Table(tableName)

item_data = {
	'device_id': os.environ.get('DEVICE_ID'),
	'requisition_id': '',
	'calibration_id': '',
	'test_results': {},
	'image': '',
    'createdAt': '',
    'updatedAt': '',
    '_version': 1,
    '_lastChangedAt': ''
}

#================================================================================
def mov_avgscan(final_image):
     input=final_image
     [a, b] = input.shape[:2]
     result_array = 0
     x = 1
     y = 1
     sum = 0
     while (y<(a-3)):
         line = input[y:y+5, x:x+b]
         avg_color_per_row = np.average(line, axis=0)
         avg_color = np.average(avg_color_per_row, axis=0)
         sum = avg_color[0]+avg_color[1]+avg_color[2]
         result_array = np.append(result_array, sum)
         y = y+3
     return result_array

def calc_ratio(result_array):
     dataNew=result_array[1:-1]
     n = len(dataNew)
     base = round(n/2)
     index1 = 1
     diff = 0
     neg_array = 0
     while(index1<n):
         diff=dataNew[base]-dataNew[index1]
         neg_array = np.append(neg_array, diff)
         index1=index1+1
     end = len(neg_array)
     base = neg_array[end-1]
     peaks, _ = find_peaks(neg_array-base, threshold=1, width=(1,10))
     prominences = peak_prominences(neg_array-base, peaks)[0]
     print("prominences", prominences)
     plt.plot(neg_array-base)
     plt.plot(peaks, neg_array[peaks]-base, 'x')
     plt.savefig('peaks.png')
     index2 = 0
     points_array = 0
     while(index2<len(peaks)):
         point =  peaks[index2]
         points_array = np.append(points_array, (neg_array[point]-base))
         index2=index2+1
     points_array.sort()
     n = len(points_array)
     print(points_array)
     if (n==1):
        peak_ratio = 0
     else:
        peak_ratio = points_array[n-2]/points_array[n-1]
        return peak_ratio

def calconc(peakratio, batch_id):
    x = batch_id.split("_")
    intercept = int(x[0])/1000
    slope = int(x[1])/1000
    print(peakratio)
    if (peakratio==0):
        conc = 0
    else:
        conc = (peakratio-intercept)/slope
    if (conc<0):
        conc = 0
    return conc

def shutdown(self):
    box = BoxLayout(orientation = 'vertical', padding = (10))
    box.add_widget(Label(text = "Do you want to shutdown the system?"))
    btn1 = Button(text = "Yes")
    btn2 = Button(text = "No")
    box.add_widget(btn1)
    box.add_widget(btn2)
    popup = Popup(title="Shutdown", content = box, size_hint=(None, None), size=(430, 200), auto_dismiss = True)
    btn1.bind(on_press = os.system("shutdown now -h"))
    btn2.bind(on_press = popup.dismiss)
    popup.open()

def PopUp(msg,title):
    box = BoxLayout(orientation = 'vertical', padding = (10))
    box.add_widget(Label(text = msg))
    btn1 = Button(text = "Ok")
    box.add_widget(btn1)
    popup = Popup(title=title, content = box,size_hint=(None, None), size=(430, 200), auto_dismiss = False)
    btn1.bind(on_press = popup.dismiss)
    popup.open()


#==============================================================================
camera = PiCamera()

class mainsplash(Screen):
    def close(self):
        shutdown(self)
    pass

class choosemode(Screen):
    pass

class entersampleid(Screen):
    def verify_sampleid(self):
        self.manager.current='batchid'

    def close(self):
        shutdown(self)
    pass

class enterbatchid(Screen):
    def decode_batchid(self):
        try:
            # conn = sqlite3.connect('tests.db')
            # cursor = conn.cursor()
            batch_id = self.ids["new_batchid"].text
            x = batch_id.split("_")
            intercept = int(x[0])/1000
            slope = int(x[1])/10000
            self.manager.current = 'instruction'
        except:
            title = "Invalid BatchID"
            msg = "Please enter correct batch identification"
            Popup(msg,title)

    def close(self):
        shutdown(self)
    pass

class instruction(Screen):
    def camcapture(self):
         batch_id = self.manager.get_screen('batchid').ids.new_batchid.text
         sample_id = self.manager.get_screen('sampleid').ids.new_sampleid.text
         GPIO.setwarnings(False)
         GPIO.setmode(GPIO.BOARD)
         GPIO.setup(40, GPIO.OUT)
         GPIO.output(40, True)
         GPIO.cleanup
         camera.start_preview()
         time.sleep(5)
         camera.capture('/home/pi/view/'+sample_id+'captured.jpg')
         camera.stop_preview()
         GPIO.output(40,False)
         input_image = cv2.imread('/home/pi/view/'+sample_id+'captured.jpg')
         roi = input_image[180:500, 350:390]
         cv2.imwrite('/home/pi/view/'+sample_id+'roi.jpg',roi)
         title = "Error reading test"
         msg = "Please ensure test has run properly"
         roi = cv2.imread('/home/pi/view/'+sample_id+'roi.jpg')
         try:
             results_array = mov_avgscan(roi)
             peakratio = calc_ratio(results_array)
             concentration = int(calconc(peakratio, batch_id))
             self.ids['peakratio'].text = str(concentration)
         except:
             title = "Unable to read value"
             msg = "Please reinsert the assay"
             Popup(msg,title)

    def close(self):
        shutdown(self)
    pass

class resultcardtest(Screen):
    def getresults(self):
        sample_id = self.manager.get_screen('sampleid').ids.new_sampleid.text
        batch_id = self.manager.get_screen('batchid').ids.new_batchid.text
        conc_result = self.manager.get_screen('instruction').ids.peakratio.text
        print('conc', conc_result)
        today = date.today()
        now = datetime.now()
        datenow = today.strftime("%B %d, %Y")
        timenow = now.strftime("%H:%M:%S")
        self.ids["date"].text = datenow
        self.ids["time"].text = timenow
        self.ids["sample_id"].text = sample_id
        self.ids["batchid"].text = batch_id
        self.ids["results"].text = str(conc_result)
        
        current_time = datetime.now(timezone.utc)
        item_data['requisition_id'] = sample_id
        item_data['calibration_id'] = batch_id
        item_data['test_results'] = { 'CRP' : str(conc_result) }
        item_data['_lastChangedAt'] = int(time.time() * 1000)
        item_data['createdAt'] = current.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        item_data['updatedAt'] = current.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        with open('/home/pi/view/'+sample_id+'roi.jpg') as roi_image:
            item_data['image'] = base64.b64encode(roi_image.read())
	
        f = open("results.csv", "a")
        string = "sample_id: "+sample_id+" batch_id: "+batch_id+" conc_result: "+conc_result+" date: "+datenow+" time: "+timenow
        f.write(string)
        f.close()
    def saveresults(self):
        req_table.put_item(Item=item_data)
        self.manager.current='sampleid'

    def discardresults(self):
        self.manager.current='sampleid'
    pass

class resultview(Screen):
    rows = ListProperty([("Sample_Id","Calibration_Id","TimeStamp","Value")])
    def get_data(self):
       try:
           req_data = req_table.query(
               KeyConditionExpression=Key('device_id').eq(os.environ.get('DEVICE_ID'))
           )['Items']
           rows['Sample_Id'] = req_data['requisition_id']
           rows['Calibration_Id'] = req_data['calibration_id']
           rows['TimeStamp'] = time.strftime("%m/%d/%Y, %I:%M:%S %p", time.localtime(int(req_data['_lastChangedAt']) / 1000 + 19800))
           rows['Value'] = req_data['test_results']['CRP']
       except:
            title = "Unable to fetch history"
            msg = "Please ensure the device is connected"
            Popup(msg,title)
    pass

kv = Builder.load_file("mainsplash.kv")
sm = ScreenManager()
sm.add_widget(mainsplash(name='splash'))
sm.add_widget(choosemode(name='modes'))
sm.add_widget(entersampleid(name='sampleid'))
sm.add_widget(enterbatchid(name='batchid'))
sm.add_widget(instruction(name='instruction'))
sm.add_widget(resultcardtest(name='resultcard'))
sm.add_widget(resultview(name='history'))

class MainApp(App):
    def build(self):
        Window.size = (800, 500)
        return sm

if __name__=="__main__":
    sa = MainApp()
    sa.run()
