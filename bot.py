import os
import telebot

TOKEN = "8419293835:AAFTBIyv1Wh06ik0GJyg9yExLMOcNEOfH9Y"
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.reply_to(message, "أهلاً بك! البوت يعمل بنجاح 24/7.")


bot.infinity_polling()

