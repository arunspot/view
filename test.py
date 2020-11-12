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

camera = PiCamera()

camcapture()

def camcapture():
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
         input_image = cv2.imread('/home/pi/view/capturedimage.jpg')
         roi = input_image[30:290, 375:425]
         cv2.imwrite('/home/pi/view/roi.jpg',roi)

     except:
         title = "Camera Error"
         msg = "Error starting camera, please call support"
         print(msg)
     try:
         results_array = mov_avgscan(roi)
         peakratio = calc_ratio(results_array)
         print('peakratio', peakratio)
         concentration = calconc(peakratio, stdcurve)
     except:
         title = "Error reading test"
         msg = "Please ensure test has run properly"
         print(msg)

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
