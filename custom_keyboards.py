from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Записать Голос", callback_data='voice_get')]])
kb2 = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Да", callback_data='voice_get')]])