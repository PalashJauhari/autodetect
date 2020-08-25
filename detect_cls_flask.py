# -*- coding: utf-8 -*-
"""Flask_Detection+Article_Type_Myntra_Huruko.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Mwd0g8sSb2UutIZsRGsuLk41WEQutGFS
"""


# Commented out IPython magic to ensure Python compatibility.
from werkzeug.wrappers import Request,Response
from flask import Flask
from flask_ngrok import run_with_ngrok
# %tensorflow_version 1.x
import numpy as np
import pandas as pd
import os
import shutil
import cv2
import pymongo
import pandas
import json
import numpy as np
import pandas as pd
import pickle
import urllib.request
import tensorflow as tf
import keras
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
# %matplotlib inline
from keras.models import Sequential, Model
from keras.optimizers import SGD, RMSprop, Adam
from keras.utils import to_categorical
from keras.layers import Dense, Dropout
from keras.layers import Activation, Flatten, Input, BatchNormalization
from keras.layers import Conv2D, MaxPooling2D,GlobalAveragePooling2D
from keras.applications.resnet import ResNet50
import seaborn as sns
import time
from flask import Flask, request, jsonify, url_for, render_template
import uuid
from scipy import ndimage
#from werkzeug import secure_filename
from PIL import Image, ImageFile
from io import BytesIO
import seaborn as sns
import time
from keras.preprocessing import image
from keras.applications.mobilenet import *


def merge(list1, list2): 
  merged_list = list(zip(list1, list2))  
  return merged_list

def get_bbox(bbox,cols,rows):
  x = bbox[1] * cols
  y = bbox[0] * rows
  right = bbox[3] * cols
  bottom = bbox[2] * rows
  return [(int(x), int(y)), (int(right),int(bottom))]

def get_clothe_bbox_batch(img,thr,graph_def_od):
    
    graph2 = tf.Graph()
    with graph2.as_default():
      tf.import_graph_def(graph_def_od)
      sess = tf.Session()
      # Restore session
      sess.graph.as_default()
      tf.import_graph_def(graph_def_od, name='')
      # Read and preprocess an image.
      batch_size=img.shape[0]
      rows = img.shape[1]
      cols = img.shape[2]
      #inp = img[:,:,:,[2, 1, 0]]  # BGR2RGB
      inp = img

      # Run the model
      out = sess.run([sess.graph.get_tensor_by_name('num_detections:0'),sess.graph.get_tensor_by_name('detection_scores:0'),
                      sess.graph.get_tensor_by_name('detection_boxes:0'),sess.graph.get_tensor_by_name('detection_classes:0')],
                      feed_dict={'image_tensor:0':inp.reshape(batch_size, inp.shape[1], inp.shape[2], 3)})

      class_id_matrix = out[3]
      score_matrix = out[1]
      bbox_matrix = out[2]

      pos = np.sum(score_matrix > thr,axis=1)  # chk what happens when sum is zero?-----------------
      
      bound_box_list = []
      class_id=[]
      for i in range(batch_size):
        bound_box_list_l=[]
        if pos[i] !=0:
          class_id.append(list(class_id_matrix[i,0:pos[i]]))
          for k in range(pos[i]):
            bound_box_list_l.append(get_bbox(bbox_matrix[i,k],cols,rows))
        else:
          class_id.append("N")
          bound_box_list_l.append([int(cols/2),int(rows/2),cols,rows])
        
        bound_box_list.append(bound_box_list_l)
      
      return bound_box_list,class_id

def get_cls_batch(img,graph_def_cls):
    
    graph3 = tf.Graph()
    with graph3.as_default():
      tf.import_graph_def(graph_def_cls)
      sess = tf.Session()
      # Restore session
      sess.graph.as_default()
      tf.import_graph_def(graph_def_cls, name='')
      # Read and preprocess an image.
      batch_size=img.shape[0]
      rows = img.shape[1]
      cols = img.shape[2]
      #inp = img[:,:,:,[2, 1, 0]]  # BGR2RGB
      inp = img

      # Run the model
      out = sess.run([sess.graph.get_tensor_by_name('category_output_layer/Softmax:0')],
                      feed_dict={'image_input:0':inp.reshape(batch_size, inp.shape[1], inp.shape[2], 3)})
      
      preds = np.argmax(out)
      return preds 


def extract_cropped_orignal(img,i):
  scale_y=img.shape[0]/300
  scale_x=img.shape[1]/300
  img_cropped = img[int(scale_y*(i[0][1])):int(scale_y*(i[1][1])),int(scale_x*(i[0][0])):int(scale_x*(i[1][0]))]
  img_cropped = cv2.resize(img_cropped,(225,225))
  return img_cropped


#Importing Detection Model
with tf.gfile.FastGFile('frozen_inference_graph.pb','rb') as f:
  graph_def_od = tf.GraphDef()
  graph_def_od.ParseFromString(f.read())

#Importing Article Classification Model
with tf.gfile.FastGFile('model_xception_article.pb','rb') as f:
  graph_def_cls = tf.GraphDef()
  graph_def_cls.ParseFromString(f.read())

import pickle
with open('myntra_article_mapping_dict.pickle', 'rb') as handle:
    article_type_mapping_dict = pickle.load(handle)

ALLOWED_EXTENSION  =set(['png','jpg','jpeg','JPG','JPEG','PNG'])
IMAGE_HEIGHT =225
IMAGE_WIDTH = 225
IMAGE_CHANNELS = 3
def allowed_file(filename):
    return '.' in filename and \
     filename.rsplit('.',1)[1] in ALLOWED_EXTENSION




app = Flask(__name__)
run_with_ngrok(app)

@app.route('/')
def index():
    return render_template('ImageML.html')

@app.route('/api/image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return render_template('ImageML.html', prediction='No posted image. Should be attribute named image')
    file = request.files['image']
    
    if file.filename =='':
        return render_template('ImageML.html', prediction = 'You did not select an image')
    
    if file and allowed_file(file.filename):
        #filename = secure_filename(file.filename)
        print("***"+file.filename)
        #x = []
        ImageFile.LOAD_TRUNCATED_IMAGES = False
        x = np.array(Image.open(BytesIO(file.read()))) 
        
        
        
        #plt.figure()
        #plt.imshow(x)
        # x in rgb format
        im = cv2.resize(x,(300,300))
        im = im.reshape((1,300,300,3))
        
        a,b=get_clothe_bbox_batch(im,0.5,graph_def_od)
        #print(a)
        if len(a[0][0]) == 4:
          a = [[[(0,0),(300,300)]]]
          #print("Detection model failed to Localise")

        response=[]
        for h in range(len(a[0])):
          im1 = extract_cropped_orignal(im.reshape(300,300,3),a[0][h])
          im1 = im1.reshape((1,225,225,3))
          # im1 in RGB Format
          im1=im1/255.0
          pred_cls = get_cls_batch(im1,graph_def_cls)
          response.append(article_type_mapping_dict[pred_cls+1])           
        
        #response = article_type_mapping_dict[np.argmax(preds[0])+1]
        return render_template('ImageML.html', prediction = 'Clothing Category is  {}'.format(response))
    else:
        return render_template('ImageML.html', prediction = 'Invalid File extension')

if __name__ == '__main__':
  app.run()