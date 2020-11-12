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
cursor.execute("""CREATE TABLE IF NOT EXISTS results (
         sample_id TEXT
         batch_id TEXT
         date TEXT
         time TEXT
         conc_result REAL
         test_image BLOB
     )
     """)

##maybe the calibrations table is not required
cursor.execute("""CREATE TABLE IF NOT EXISTS calibrations (
         test_type TEXT
         assay_type TEXT
         batch_id TEXT
         )""")
conn.commit()
conn.close()
#------------------------------------------------------------------------------

#================================================================================
def PopUp(self,msg,title):
    box = BoxLayout(orientation = 'vertical', padding = (10))
    box.add_widget(Label(text = msg))
    btn1 = Button(text = "Ok")
    box.add_widget(btn1)
    popup = Popup(title=title, content = box,size_hint=(None, None), size=(430, 200), auto_dismiss = False)
    btn1.bind(on_press = popup.dismiss)
    popup.open()


def mov_avgscan(final_image):
     input=final_image
     [a, b] = input.shape[:2]
     result_array = 0
     x = 1
     y = 1
     sum = 0
     while (y<(a-3)):
         line = input[y:y+3, x:x+b]
         avg_color_per_row = np.average(line, axis=0)
         avg_color = np.average(avg_color_per_row, axis=0)
         sum = avg_color[0]+avg_color[1]+avg_color[2]
         print(sum)
         result_array = np.append(result_array, sum)
         y = y+1
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
     peaks, _ = find_peaks(neg_array, height=1)
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

def calconc(peakratio, slope, intercept):
     conc = (peakratio-intercept)/slope
     if (conc<0):
         conc = 0
     return conc

def shutdown():
    box = BoxLayout(orientation = 'vertical', padding = (10))
    box.add_widget(Label(text = "Do you want to shutdown the system?"))
    btn1 = Button(text = "Yes")
    btn2 = Button(text = "No")
    box.add_widget(btn1)
    box.add_widget(btn2)
    btn1.bind(on_press = os.system("shutdown now -h"))
    btn2.bind(on_press = popup.dismiss)
    popup = Popup(title="Shutdown", content = box, size_hint=(None, None), size=(430, 200), auto_dismiss = True)
    popup.open()

#==============================================================================
camera = PiCamera()

class mainsplash(Screen):
    def close(self):
        shutdown()
    pass

class enteruserid(Screen):
    def verify_username(self):
        title = "Wrong UserId"
        msg = "Userid is incorrect for Deviceid: VIEAS2003"
        if self.ids["new_userid"].text == "IDS":
            self.manager.current='password'
        else:
            PopUp(self,msg,title)

    def close(self):
        shutdown()
    pass

class enterpassword(Screen):
    def verify_password(self):
        title = "Wrong Password"
        msg = "Password is incorrect for Deviceid: VIEAS2003"
        if self.ids["new_password"].text == "IDS2897":
            self.manager.current='modes'
        else:
            PopUp(self,msg,title)

    def close(self):
        shutdown()
    pass

class choosemode(Screen):
    pass

class entersampleid(Screen):
    sample_id = StringProperty('')
    def verify_sampleid(self):
        conn = sqlite3.connect('tests.db')
        cursor = conn.cursor()
        self.sample_id = self.ids["new_sampleid"].text
        cursor.execute('SELECT sample_id FROM results WHERE sample_id=?',(self.sample_id,))
        check = cursor.fetchone()
        conn.close()
        if check == None:
            print('no sampleids found')
            self.manager.current='batchid'
        else:
            title = "Existing SampleID"
            msg = "SampleID already exists. Please enter a different id"
            Popup(self,msg,title)

    def close(self):
        shutdown()
    pass

class enterbatchid(Screen):
    slope = NumericProperty(1.0)
    intercept = NumericProperty(1.0)
    batch_id = StringProperty('')
    def decode_batchid(self):
        try:
            self.batch_id = self.ids["new_batchid"].text
            x = self.batch_id.split("_")
            self.intercept = int(x[0])/1000
            print(self.intercept)
            self.slope = int(x[1])/1000
            print(self.slope)
            self.manager.current = 'instruction'
        except:
            title = "Invalid BatchID"
            msg = "Please enter correct batch identification"
            Popup(self,msg,title)
    def close(self):
        shutdown()
    pass

class instruction(Screen):
    batchval = enterbatchid()
    concentration = NumericProperty(1.0)
    def camcapture(self):
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
         roi = input_image[30:290, 405:460]
         cv2.imwrite('/home/pi/view/roi.jpg',roi)
         print("images saved")
         title = "Error reading test"
         msg = "Please ensure test has run properly"
         slope1 = self.batchval.slope
         intercept1 = self.batchval.intercept
         print(slope1,intercept1)
         try:
             results_array = mov_avgscan(roi)
             print("results array generated")
             peakratio = calc_ratio(results_array)
             print("peak ratio calculated")
             self.concentration = int(calconc(peakratio, slope1, intercept1))
             print("concentration calculated", self.concentration)

         except:
             Popup(self,msg,title)

    def close(self):
        shutdown()
    pass

class resultcardtest(Screen):
    sample_value = entersampleid()
    batch_value = enterbatchid()
    result_value = instruction()
    datenow = StringProperty('')
    timenow = StringProperty('')
    def getresults(self):
        today = date.today()
        now = datetime.now()
        self.datenow = today.strftime("%B %d, %Y")
        self.timenow = now.strftime("%H:%M:%S")
        input_image = cv2.imread('/home/pi/view/roi.jpg')
        self.ids["date"].text = self.datenow
        self.ids["time"].text = self.timenow
        self.ids["sample_id"].text = self.sample_value.sample_id
        print(self.sample_value.sample_id)
        self.ids["batchid"].text = self.batch_value.batch_id
        print(self.batch_value.batch_id)
        self.ids["results"].text = str(self.result_value.concentration)
    def saveresults(self):
        conn = sqlite3.connect('tests.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO results (sample_id, batch_id, date, time, conc_result, test_image) VALUES (?)", (self.sample_value.sample_id, self.batch_value.batch_id, self.datenow, self.timenow, self.result_value.concentration, input_image))
        conn.commit()
        conn.close()
        self.manager.current='modes'
    def discardresults(self):
        self.manager.current='modes'
    pass

class resultview(Screen):
    rows = ListProperty([("Sample_Id","Batch_Id","Date","Time","Value")])
    def get_data(self):
        conn = sqlite3.connect('tests.db')
        cursor = conn.cursor()
        cursor.execute("SELECT (sample_id, batch_id, date, time, conc_result) FROM results")
        self.rows = cursor.fetchall()
        conn.close()
        print(self.rows)
    pass

kv = Builder.load_file("mainsplash.kv")
sm = ScreenManager()
sm.add_widget(mainsplash(name='splash'))
sm.add_widget(enteruserid(name='userid'))
sm.add_widget(enterpassword(name='password'))
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
