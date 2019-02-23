import traceback
import telegram
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Filters

from config import config

from commands.balance import balance
from commands.consume import drink
from commands.send import send
from commands.communism import communism, communismQuery
from commands.pay import pay, payQuery

updater = Updater(config["bot-token"])
filter = Filters.chat(config["chat-id"])

def tryWrap(func):
	def wrapper(*args, **kwargs):
		try:
			func(*args, **kwargs)
		except:
			print(traceback.format_exc())

	return wrapper

updater.dispatcher.add_handler(CommandHandler("balance", tryWrap(balance)))
updater.dispatcher.add_handler(CommandHandler("drink", tryWrap(drink), filters=filter))
updater.dispatcher.add_handler(CommandHandler("send", tryWrap(send), filters=filter))
updater.dispatcher.add_handler(CommandHandler("communism", tryWrap(communism), filters=filter))
updater.dispatcher.add_handler(CommandHandler("pay", tryWrap(pay), filters=filter))

updater.dispatcher.add_handler(CallbackQueryHandler(tryWrap(communismQuery), pattern="^communism"))
updater.dispatcher.add_handler(CallbackQueryHandler(tryWrap(payQuery), pattern="^pay"))

updater.start_polling()
updater.idle()
