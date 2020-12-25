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
from scipy.signal import find_peaks
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
from datetime import date, datetime
import sqlite3
from subprocess import call
from kivy.properties import ListProperty

#=============================================================================
conn = sqlite3.connect('tests.db')
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS results (sample_id TEXT,batch_id TEXT,date TEXT,time TEXT,conc_result REAL,test_image BLOB,peak_image BLOB)")
conn.commit()
conn.close()
#------------------------------------------------------------------------------

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
     index1 = 0
     diff = 0
     neg_array = 0
     while(index1<n):
         diff=dataNew[base]-dataNew[index1]
         neg_array = np.append(neg_array, diff)
         index1=index1+1
     peaks1, _ = find_peaks(neg_array, prominence=2)
     plt.plot(neg_array)
     plt.plot(peaks1, neg_array[peaks1], 'x')
     plt.savefig('peaks.png')
     peak_image = cv2.imread('/home/pi/view/peaks.png')
     conn = sqlite3.connect('tests.db')
     cursor = conn.cursor()
     cursor.execute("INSERT INTO results(peak_image) VALUES (peak_image) WHERE sample_id=?",(self.manager.get_screen('sampleid').ids.new_sampledid.text,))
     conn.commit()
     conn.close()
     index2 = 0
     points_array = 0
     while(index2<len(peaks)):
         point =  peaks[index2]
         points_array = np.append(points_array, neg_array[point])
         index2=index2+1
     points_array.sort()
     n = len(points_array)-1
     print(points_array[n], points_array[n-1])
     peak_ratio = points_array[n-1]/points_array[n]
     return peak_ratio

def calconc(peakratio, batch_id):
    x = batch_id.split("_")
    intercept = int(x[0])/1000
    slope = int(x[1])/10000
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

def PopUp(self,msg,title):
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
        conn = sqlite3.connect('tests.db')
        cursor = conn.cursor()
        sample_id = self.ids["new_sampleid"].text
        cursor.execute("SELECT sample_id FROM results WHERE sample_id=?",(sample_id,))
        check = cursor.fetchone()
        if check == None:
            print('no sampleids found')
            cursor.execute("INSERT INTO results(sample_id) VALUES (sample_id);")
            conn.commit()
            conn.close()
            self.manager.current='batchid'
        else:
            title = "Existing SampleID"
            msg = "SampleID already exists. Please enter a different id"
            Popup(self,msg,title)

    def close(self):
        shutdown(self)
    pass

class enterbatchid(Screen):
    def decode_batchid(self):
        try:
            conn = sqlite3.connect('tests.db')
            cursor = conn.cursor()
            batch_id = self.ids["new_batchid"].text
            x = batch_id.split("_")
            intercept = int(x[0])/1000
            slope = int(x[1])/10000
            self.manager.current = 'instruction'
            cursor.execute("INSERT INTO results(batch_id) VALUES (batch_id) WHERE sample_id=?",(self.manager.get_screen('sampleid').ids.new_sampledid.text,))
            conn.commit()
            conn.close()
        except:
            title = "Invalid BatchID"
            msg = "Please enter correct batch identification"
            Popup(self,msg,title)

    def close(self):
        shutdown(self)
    pass

class instruction(Screen):
    def camcapture(self):
         batch_id = self.manager.get_screen('batchid').ids.new_batchid.text
         GPIO.setwarnings(False)
         GPIO.setmode(GPIO.BOARD)
         GPIO.setup(40, GPIO.OUT)
         GPIO.output(40, True)
         GPIO.cleanup
         camera.start_preview()
         time.sleep(5)
         camera.capture('/home/pi/view/capturedimage.jpg')
         camera.stop_preview()
         GPIO.output(40,False)
         input_image = cv2.imread('/home/pi/view/capturedimage.jpg')
         roi = input_image[170:400, 350:390]
         cv2.imwrite('/home/pi/view/roi.jpg',roi)
         title = "Error reading test"
         msg = "Please ensure test has run properly"
         roi = cv2.imread('/home/pi/view/roi.jpg')
         conn = sqlite3.connect('tests.db')
         cursor = conn.cursor()
         cursor.execute("INSERT INTO results(test_image) VALUES (roi) WHERE sample_id=?",(self.manager.get_screen('sampleid').ids.new_sampledid.text,))
         conn.commit()
         conn.close()
         try:
             results_array = mov_avgscan(roi)
             concentration = calc_ratio(results_array)
             #concentration = int(calconc(peakratio, batch_id))
             self.ids['peakratio'].text = str(concentration)
         except:
             title = "Unable to read value"
             msg = "Please reinsert the assay"
             Popup(self,msg,title)

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
        conn = sqlite3.connect('tests.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO results(date,time,conc_result) VALUES (datenow,timenow,conc_result) WHERE sample_id=?",(self.manager.get_screen('sampleid').ids.new_sampledid.text,))
        conn.commit()
        conn.close()

    def saveresults(self):
        self.manager.current='instruction'

    def discardresults(self):
        conn = sqlite3.connect('tests.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM results WHERE sample_id=?",(sample_id,))
        conn.commit()
        conn.close()
        self.manager.current='instruction'
    pass

class resultview(Screen):
    rows = ListProperty([("Sample_Id","Batch_Id","Date","Time","Value")])
    def get_data(self):
        try:
            conn = sqlite3.connect('tests.db')
            cursor = conn.cursor()
            cursor.execute("SELECT sample_id,batch_id,date,time,conc_result FROM results")
            self.rows = cursor.fetchall()
            conn.close()
            print(self.rows)
        except:
             title = "Unable to fetch history"
             msg = "Please ensure the device is connected"
             Popup(self,msg,title)
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
