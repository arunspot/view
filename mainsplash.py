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
from datetime import date
from datetime import datetime
import sqlite3

#=============================================================================
conn = sqlite3.connect('tests.db')
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS results (
         sample_id TEXT
         batch_number TEXT
         date TEXT
         time TEXT
         location TEXT
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

conn.commit()
conn.close()

camera = PiCamera()
#
class mainsplash(Screen):
# =============================================================================
    print("mainsplash")
    pass

class enteruserid(Screen):
    print("userid")

    def verify_username(self):
        title = "Wrong Userid"
        msg = "Userid is incorrect for Deviceid: VIEAS2003"
        if self.ids["new_userid"].text == "IDSB":
            self.manager.current='password'
        else:
            PopUp(self,msg,title)

class enterpassword(Screen):
    print("password")
    #check if password is correct; if not give error message
    pass

class choosemode(Screen):
    print("choosemode")
    pass

class entersampleid(Screen):
    print("entersampleid")
    #check if sampleid is new; if already exists create a popup
    pass

class enterbatchcode(Screen):
    print("enterbatchcode")
    #validate batchcode; if not create a popup
    pass

class instruction(Screen):
    print("instructions")
# =============================================================================
    def camcapture(self):
         global concentration
         global peak_ratio
         #std_curve = decode()
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
         concentration = 10
         input_image = cv2.imread('/home/pi/view/capturedimage.jpg')
         roi = input_image[30:290, 375:425]
         cv2.imwrite('/home/pi/view/cropped.jpg',roi)
         results_array = mov_avgscan(roi)
         peak_ratio = calc_ratio(results_array)
         concentration = calconc(peak_ratio, std_curve)
         return concentration

    def mov_avgscan(final_image):
         input=final_image
         [a, b] = input.shape[:2]
         result_array = 0
         x = 1
         y = 1
         sum = 0
         while (y<(a-5)):
             line = input[y:y+3, x:x+b]
             avg_color_per_row = np.average(line, axis=0)
             avg_color = np.average(avg_color_per_row, axis=0)
             sum = avg_color[0]+avg_color[1]+avg_color[2]
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
         global qrval
         global concarray
         global peakarray
         global assaytype
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
         m,b = np.polyfit(x, y, 1) #calculate the intercept and slope here
         std_curve = [m,b]
         return std_curve

# =============================================================================
    #error popups for assays which havent run well
    pass

class resultcardtest(Screen):
    print("resultcard")
    pass

class instructionc(Screen):
    print("calibrated")
    def pkratio1():
        global rndpr1
        input_image = startcam()
        roi = input_image[30:290, 375:425]
        cv2.imwrite('/home/pi/view/cropped.jpg',roi)
        results_array = mov_avgscan(roi)
        peak_ratio1 = calc_ratio(results_array)
        rndpr1 = float("{0:.2f}".format(peak_ratio1))
        print(peak_ratio1)
        pkr1L.configure(text=rndpr1)
        return peak_ratio1

    def gencode():
        global qrstring
        Assayid = AssayE.get()
        Batchid = BatchE.get()
        conc1 = int(Conc1E.get())
        conc2 = int(Conc2E.get())
        conc3 = int(Conc3E.get())
        unit = int(UnitE.get())

        str1 = int(conc1*1000+rndpr1*100)
        str2 = int(conc2*1000+rndpr2*100)
        str3 = int(conc3*1000+rndpr3*100)
        strcode = unit+str3*10^2+str2*10^7+str3*10^12
        batchcode = hex(strcode)

        #make other functions global
    pass

class enterconccard(Screen):
    print("concentration")
    pass

class generatebatchcode(Screen):
    print("generatedcode")
    pass

def PopUp(self, msg, title):
    btn1 = Button(text = "Ok")
    box.add_widget(btn1)
    popup = Popup(title=title, content = (Label(text = msg)),size_hint=(None, None), size=(430, 200), auto_dismiss = True)
    btn1.bind(on_press = popup.dismiss)
    popup.open()
pass

# =============================================================================
# def shutdown():
#     exitlayout =
#     pop = Popup(title='Exit' ,
#                   content = exitlayout, auto_dismiss=False
#                   size_hint = (None, None), size=(400, 400))
#
#     pop.open()
#
# =============================================================================
kv = Builder.load_file("mainsplash.kv")
sm = ScreenManager()
sm.add_widget(mainsplash(name='splash'))
sm.add_widget(enteruserid(name='userid'))
sm.add_widget(enterpassword(name='password'))
sm.add_widget(choosemode(name='modes'))
sm.add_widget(entersampleid(name='sampleid'))
sm.add_widget(enterbatchcode(name='batchcode'))
sm.add_widget(instruction(name='instruction'))
sm.add_widget(resultcardtest(name='resultcard'))

sm.add_widget(instructionc(name='instructionc'))
sm.add_widget(enterconccard(name='concentration'))
sm.add_widget(generatebatchcode(name='newcode'))

class MainApp(App):
    def build(self):
        Window.size = (800, 500)
        return sm

if __name__=="__main__":
    sa = MainApp()
    sa.run()
