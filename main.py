import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
import subprocess
from script import pollinations_generate
from aiogram.types import CallbackQuery
import json
from datetime import datetime
import custom_keyboards as cs
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

SAVE_DIR = "audio"
os.makedirs(SAVE_DIR, exist_ok=True)

REGISTRY_PATH = "records.json"

# если файла нет — создаём пустой
if not os.path.exists(REGISTRY_PATH):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)


def load_registry():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_registry(registry):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


async def convert_to_wav(input_path, output_path):
    """Конвертация через ffmpeg"""
    cmd = [
        "ffmpeg", "-i", input_path,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm16le", output_path,
        "-y"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@dp.message(F.voice)
async def handle_voice(message: Message):
    file = await bot.get_file(message.voice.file_id)
    file_path = file.file_path
    file_ext = ".ogg"

    base_name = f"{message.from_user.id}_{message.message_id}"
    raw_path = os.path.join(SAVE_DIR, base_name + file_ext)
    wav_path = os.path.join(SAVE_DIR, base_name + ".wav")

    # скачать voice
    await bot.download_file(file_path, raw_path)
    await convert_to_wav(raw_path, wav_path)

    # обновляем запись в реестре (последнюю без audio)
    registry = load_registry()
    for rec in reversed(registry):  # идём с конца
        if rec["user_id"] == message.from_user.id and rec["audio"] is None:
            rec["audio"] = wav_path
            break
    save_registry(registry)

    await message.answer(f"✅ Ваш голос успешно сохранен! Спасибо за вклад в проект!")
    await message.answer(f"Хотите попробовать ещё?", reply_markup=cs.kb2)


@dp.callback_query(lambda c: c.data == "voice_get")
async def handle_voice_button(callback: CallbackQuery):
    text = pollinations_generate()
    # отвечаем на сам callback, чтобы Telegram не ругался
    await callback.answer()

    # создаём запись в реестре
    registry = load_registry()
    rec_id = f"{callback.from_user.id}_{len(registry)}"

    record = {
        "id": rec_id,
        "user_id": callback.from_user.id,
        "text": text,
        "audio": None,
        "created_at": datetime.utcnow().isoformat()
    }

    registry.append(record)
    save_registry(registry)

    # отправляем сообщение с текстом
    await callback.message.answer("Отлично, пожалуйста озвучьте следующий текст на казахском языке:")
    await callback.message.answer(text)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🎙 Привет! TilDos — это исследовательский проект, цель которого — собрать разнообразные образцы казахской речи."
                         " Голоса участников помогут создать и обучить системы распознавания и синтеза речи на казахском языке, "
                         "которые будут полезны детям и взрослым с особенностями речи (например, при ДЦП или аутизме).", reply_markup=cs.kb)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

