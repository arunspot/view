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
from kivy.properties import ObjectProperty
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
from datetime import date
from datetime import datetime
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
         test_type TEXT
         assay_type TEXT
         conc_result REAL
         unit TEXT
         test_image BLOB
     )
     """)

cursor.execute("""CREATE TABLE IF NOT EXISTS calibrations (
         batch_number TEXT
         test_type TEXT
         assay_type TEXT
         unit TEXT
         pt_1 REAL
         val_1 REAL
         pt_2 REAL
         val_2 REAL
         pt_3 REAL
         val_3 REAL
         pt_4 REAL
         val_4 REAL
         pt_5 REAL
         val_5 REAL
 )""")

 #dynamically create calibrations table; dynamic number of rows

conn.commit()

camera = PiCamera()

class mainsplash(Screen):
    pass

class enteruserid(Screen):

    def verify_username(self):
        title = "Wrong UserId"
        msg = "Userid is incorrect for Deviceid: VIEAS2003"
        if self.ids["new_userid"].text == "IDSB":
            self.manager.current='password'
        else:
            PopUp(self,msg,title)
    pass

class enterpassword(Screen):

    def verify_password(self):
        title = "Wrong Password"
        msg = "Password is incorrect for Deviceid: VIEAS2003"
        if self.ids["new_password"].text == "IDS2897":
            self.manager.current='modes'
        else:
            PopUp(self,msg,title)
    pass

class choosemode(Screen):
    # add a screen after choose mode for which test
    pass

class entersampleid(Screen):
    global sample_id
    title = "Existing SampleID"
    msg = "SampleID already exists. Please enter a different id"

    def verify_sampleid(self):
        sample_id = self.ids["new_sampleid"].text
        cursor.execute("""SELECT sample_id
                   FROM results
                   WHERE sample_id=?""",
                (sample_id))
        check = cursor.fetchone()
        if result:
            Popup(self,msg,title)
        else:
            self.manager.current='testtype'
    pass

class entertesttype(Screen):
    pass

class enterbatchcode(Screen):
    global batchid
    global std_curve
    global datenow
    global timenow
    today = date.today()
    datenow = today.strftime("%B %d, %Y")
    timenow = datetime.now()
    title = "Batchid Error"
    msg = "Error reading Batchid, please reenter"
    def read_batchid(self):
        try:
            batchid = self.ids["new_batchid"].text
            std_curve = decode(batchid)
            cursor.execute("INSERT INTO results (sample_id, batch_id, date, time, test_type, assay_type, unit) VALUES (?, ?, ?, ?, ?, ?, ?)", (sample_id, batchid, datenow, timenow, testtype, assaytype, unit))
            conn.commit()
            self.manager.current='instruction'
        except:
            Popup(self,msg,title)
    pass

class instruction(Screen):

    def camcapture(self):
         global concentration
         global peak_ratio
         try:
             GPIO.setwarnings(False)
             GPIO.setmode(GPIO.BOARD)
             GPIO.setup(40, GPIO.OUT)
             GPIO.output(40, True)
             GPIO.cleanup
             camera.start_preview()
             time.sleep(3)
             camera.capture('/home/pi/view/capturedimage.jpg')
             camera.stop_preview()
             GPIO.output(40,False)
         except:
             title = "Camera Error"
             msg = "Error starting camera, please call support"
             Popup(self,msg,title)
         input_image = cv2.imread('/home/pi/view/capturedimage.jpg')
         roi = input_image[30:290, 375:425]
         cv2.imwrite('/home/pi/view/roi.jpg',roi)
         try:
             results_array = mov_avgscan(roi)
             peak_ratio = calc_ratio(results_array)
             concentration = calconc(peak_ratio, std_curve)
         except:
             title = "Error reading test"
             msg = "Please ensure test has run properly"
             Popup(self,msg,title)
         return concentration

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
         peakratio = points_array[n-1]/points_array[n]
         return peakratio

    def calconc(peakratio, stdcurve):
         slope = stdcurve[0]
         intercept = stdcurve[1]
         conc = slope*peakratio+intercept
         if (conc<0):
             conc = 0
         return conc

    def decode(batchid):
         global unit
         mainstr = int(batchid, 16)
         number = str(number)
         conc1 = int(number[0:1])
         au1 = float(number[2:4])/100
         conc2 = int(number[5:6])
         au2 = float(number[7:9])/100
         conc3 = int(number[10:11])
         au3 = float(number[12:14])/100
         unit = "10^-"+number[15]+"mg/ml"
         x=np.array([conc1, conc2, conc3])
         y=np.array([au1, au2, au3])
         m,b = np.polyfit(x, y, 1)
         decoded = [m,b]
         return decoded

    pass

class resultcardtest(Screen):
    changelabels()
    def changelabels(self):
        self.sample_id.text = self.manager.get_screen('sampleid').sample_id
        self.results.text = self.manager.get_screen('instruction').concentration
    def saveresults(self):
            cursor.execute("INSERT INTO results (conc_result) VALUES (?)", (concentration))
            conn.commit()
            self.manager.current='modes'

    def discardresults(self):
            cursor.execute("""DELETE
                       FROM results
                       WHERE sample_id=?""",
                    (sample_id))
            conn.commit()
            self.manager.current='modes'
    pass

class instructionc(Screen):
    pass

class enterconccard(Screen):
    global cal_conc
    global cal_au
    global batchid
    def pkratio():
        input_image = startcam()
        roi = input_image[30:290, 375:425]
        cv2.imwrite('/home/pi/view/roi.jpg',roi)
        results_array = mov_avgscan(roi)
        peak_ratio = calc_ratio(results_array)
        rndpr = float("{0:.2f}".format(peak_ratio))
        return rndpr

    def read_testassay(self):
        cal_conc = np.append(cal_conc, self.ids["new_concid"].text)
        peak_ratio = pkratio()
        cal_au = np.append(cal_au, peak_ratio)
        self.ids["new_concid"].text = ""

    def gencode():
        [m,b] = np.polyfit(cal_conc, cal_au, 1)
        batchid = str(m)+"/"+str(b)
        print(batchid)
        self.manager.current = 'newcode'
    pass

class generatebatchcode(Screen):
    pass

class resultview(Screen):
    rows = ListProperty([("Sample_Id","Batch_Id","Test_type","Value","Unit")])
    def get_data(self):
        cursor.execute("SELECT (sample_id, batch_id, test_type, conc_result, unit) FROM results")
        self.rows = cursor.fetchall()
        print(self.rows)
    pass

def PopUp(self, msg, title):
    box = BoxLayout(orientation = 'vertical', padding = (10))
    box.add_widget(Label(text = msg))
    btn1 = Button(text = "Ok")
    box.add_widget(btn1)
    popup = Popup(title=title, content = box,size_hint=(None, None), size=(430, 200), auto_dismiss = True)
    btn1.bind(on_press = popup.dismiss)
    popup.open()
pass

def shutdown():
    box = BoxLayout(orientation = 'vertical', padding = (10))
    box.add_widget(Label(text = "Do you want to shutdown the system?"))
    btn1 = Button(text = "Yes")
    btn1 = Button(text = "No")
    box.add_widget(btn1)
    box.add_widget(btn2)
    popup = Popup(title="Shutdown", content = box, size_hint=(None, None), size=(430, 200), auto_dismiss = True)
    btn1.bind(on_press = call("sudo nohup shutdown -h now", shell=True))
    btn2.bind(on_press = popup.dismiss)
    popup.open()
pass

kv = Builder.load_file("mainsplash.kv")
sm = ScreenManager()
sm.add_widget(mainsplash(name='splash'))
sm.add_widget(enteruserid(name='userid'))
sm.add_widget(enterpassword(name='password'))
sm.add_widget(choosemode(name='modes'))
sm.add_widget(entersampleid(name='sampleid'))
#sm.add_widget(entertesttype(name='testtype'))
sm.add_widget(enterbatchcode(name='batchcode'))
sm.add_widget(instruction(name='instruction'))
sm.add_widget(resultcardtest(name='resultcard'))
sm.add_widget(instructionc(name='instructionc'))
sm.add_widget(enterconccard(name='concentration'))
sm.add_widget(generatebatchcode(name='newcode'))
sm.add_widget(resultview(name='history'))

class MainApp(App):
    def build(self):
        Window.size = (800, 500)
        return sm

if __name__=="__main__":
    sa = MainApp()
    sa.run()
