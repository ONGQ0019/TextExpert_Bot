# -*- coding: utf-8 -*-
"""paraphrase3.ipynb

Automatically generated by Colaboratory.

#install required packages
!pip install transformers sentencepiece
!pip install pyTelegramBotAPI
!pip install --upgrade pyTelegramBotAPI
!pip install easyocr
!pip install opencv-python-headless==4.5.2.52  
!pip install protobuf 
!pip install googletrans==4.0.0-rc1

#import libraries
import googletrans
import telebot
from telebot import types
import random as random
import logging
import sys
import time
import os
from importlib import reload
import time
from flask import Flask, request
from transformers import *
import easyocr
import sqlite3
model = PegasusForConditionalGeneration.from_pretrained("tuner007/pegasus_paraphrase")
tokenizer = PegasusTokenizerFast.from_pretrained("tuner007/pegasus_paraphrase")

#define paraphrasing tool
def get_paraphrased_sentences(model, tokenizer, sentence, num_return_sequences=5, num_beams=10):
  # tokenize the text to be form of a list of token IDs
  inputs = tokenizer([sentence], truncation=True, padding="longest", return_tensors="pt")
  # generate the paraphrased sentences
  outputs = model.generate(
    **inputs,
    num_beams=num_beams,
    max_length=10000,
    num_return_sequences=num_return_sequences,
  )
  # decode the generated sentences using the tokenizer to get them back to text
  return tokenizer.batch_decode(outputs, skip_special_tokens=True)
  
#set telebot and database
API_KEY = '5111426237:AAFEzfGtIn_xHRmqUquFjqaEhyAKYyLa17A'
bot = telebot.TeleBot(API_KEY)
server = Flask(__name__)
global photo_list
photo_list = []
conn = sqlite3.connect('telebot_db.sqlite',check_same_thread=False)
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS experiments11 (id VARCHAR, text VARCHAR)')
conn.commit()

#telebot handlers
@bot.message_handler(commands=['start',"Start","START"])
def send_welcome(message):
	bot.reply_to(message, "Hello, Iwantpara_bot is here to help you paraphrase your texts. \nUse /menu to navigate \nUse /help to seek help \nYou are welcome :)")

@bot.message_handler(commands=['help',"Help","HELP"])
def send_welcome1(message):
  bot.reply_to(message, "Use /textparaphrase to paraphrase any text. \nUse /imgparaphrase to convert any image into text to paraphrase")

@bot.message_handler(commands=['menu',"MENU",'Menu'])
def send_welcome(message):
  markup = types.ReplyKeyboardMarkup(row_width=2)
  itembtn1 = types.KeyboardButton('/textparaphrase')
  itembtn2 = types.KeyboardButton('/imgparaphrase')
  itembtn3 = types.KeyboardButton('/start')
  itembtn4 = types.KeyboardButton('/help')
  markup.add(itembtn1, itembtn2, itembtn3,itembtn4)
  bot.send_message(message.chat.id, "Select one of the options", reply_markup=markup)

@bot.message_handler(commands=['textparaphrase'])
def pp(message):
  sent = bot.send_message(message.chat.id, 'Give me your text')
  bot.register_next_step_handler(sent, pp2)

def pp2(message):
  while True:
    try:
      if translator.translate(message.text).src == "zh-CN":
        bot.send_message(message.chat.id, "Your text is: " + "\n" + message.text+ "\n\nTranslating and pharaphising your text...")
      else: 
        bot.send_message(message.chat.id, "Your text is: " + "\n" + message.text+ "\n\nPharaphising your text...")
      open('problem.txt', 'w').write(str(message.chat.id) + ' | ' + message.text + '||')
      sentence = message.text
      sentence = translator.translate(sentence).text
      sentence_split = sentence.split(".")
      sentence_filtered = list(filter(None, sentence_split))
      gk = str(message.chat.id)
      gg = "filler"
      cur.execute('INSERT INTO experiments11 VALUES (?,?)',(gk,gg))
      cur.execute("UPDATE experiments11 SET text =? WHERE id=?", (sentence,gk))
      listed = []
      for each in sentence_filtered:
          listed.append(get_paraphrased_sentences(model, tokenizer, each, num_beams=10, num_return_sequences=3)[1:2])
      newest = [i[0] for i in listed]
      joined = " ".join(str(item) for item in newest)
      bot.send_message(message.chat.id, joined)
      bot.send_message(message.chat.id, "If you want this to be rephrased, press /rephrase. Else /menu to go back to mainmenu")
      break
    except:
      KeyError
      bot.send_message(message.chat.id, 'Text only')
      pp(message)  
      break

@bot.message_handler(commands=['rephrase'])
def pp3(message):
    conn = sqlite3.connect('telebot_db.sqlite',check_same_thread=False)
    bot.send_message(message.chat.id, "Recaliberating...")
    gk = str(message.chat.id)
    cur.execute('SELECT text FROM experiments11 WHERE id=? LIMIT 1',([gk]))
    data = cur.fetchall()
    newdata = [i[0] for i in data]
    joineddata = " ".join(str(item) for item in newdata)
    sentence = joineddata
    sentence_split = sentence.split(".")
    sentence_filtered = list(filter(None, sentence_split))
    listed = []
    for each in sentence_filtered:
        listed.append(get_paraphrased_sentences(model, tokenizer, each, num_beams=10, num_return_sequences=6)[4:5])
    newest = [i[0] for i in listed]
    joined = " ".join(str(item) for item in newest)
    bot.send_message(message.chat.id, joined)

@bot.message_handler(commands=['imgparaphrase'])
def send_welcome(message):
    send = bot.send_message(message.from_user.id, 'Send your cropped photos')
    bot.register_next_step_handler(send, get_user_pics)
    return

@bot.message_handler(content_types=['photo'])
def get_user_pics(message):
  while True:
    try:
      global photo_list
      if message.text == '/done':
          bot.send_message(message.chat.id, "Converting to text...") 
          process_messages(message)
          return
      elif message.photo[-1].file_id not in photo_list:
          photo_list.append(message.photo[-1].file_id)
      send = bot.send_message(message.from_user.id, "You can send multiple photos, press /done when you are finished")
      bot.register_next_step_handler(send, get_user_pics)
      return
      break
    except:
      KeyError
      bot.send_message(message.chat.id, 'Image only, files/texts not accepted')
      send_welcome(message)  
      break

def process_messages(message):
    global photo_list
    reader = easyocr.Reader(['en','ch_sim'])
    longtext = ''
    for each in photo_list:
      file_info = bot.get_file(each)
      path = each +".jpg"
      downloaded_file = bot.download_file(file_info.file_path)
      with open(path,'wb') as new_file:
        final_file = new_file.write(downloaded_file)
      readtext = reader.readtext(downloaded_file)
      for result in readtext: 
        longtext += result[1] + ''
    longtext_text = longtext
    if translator.translate(longtext_text).src == "zh-CN":
      bot.send_message(message.chat.id, longtext_text + "\n\nTranslating your text...")
    longtext_text = translator.translate(longtext_text).text
    bot.send_message(message.chat.id, longtext_text)
    bot.send_message(message.chat.id, "Pharaphising your text...")
    sentence = longtext_text
    sentence_split = sentence.split(".")
    sentence_filtered = list(filter(None, sentence_split))
    gk = str(message.chat.id)
    gg = "filler"
    cur.execute('INSERT INTO experiments11 VALUES (?,?)',(gk,gg))
    cur.execute("UPDATE experiments11 SET text =? WHERE id=?", (sentence,gk))
    listed = []
    for each in sentence_filtered:
        listed.append(get_paraphrased_sentences(model, tokenizer, each, num_beams=10, num_return_sequences=3)[1:2])
    newest = [i[0] for i in listed]
    joined = " ".join(str(item) for item in newest)
    bot.send_message(message.chat.id, joined)
    send = bot.send_message(message.chat.id, "If you want this to be rephrased, press /rephrase. Else /menu to go back to main menu")
    photo_list = []

#Script to be hosted on ubuntu @AWS
bot.polling()
