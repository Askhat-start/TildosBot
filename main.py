import os
import asyncio
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from dotenv import load_dotenv

import custom_keyboards as cs
from script import pollinations_generate

# ==============================
# 🔧 Настройки
# ==============================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Добавь его в .env файл")

bot = Bot(token=TOKEN)
dp = Dispatcher()

SAVE_DIR = "audio"
os.makedirs(SAVE_DIR, exist_ok=True)

REGISTRY_PATH = "records.json"

# если файла нет — создаём пустой
if not os.path.exists(REGISTRY_PATH):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)


# ==============================
# 📂 Работа с реестром
# ==============================
def load_registry():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_registry(registry):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


# ==============================
# 🎵 Конвертация
# ==============================
async def convert_to_wav(input_path, output_path):
    """Асинхронная конвертация через ffmpeg"""
    cmd = [
        "ffmpeg", "-i", input_path,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm16le", output_path,
        "-y"
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    await process.communicate()


# ==============================
# 🎙 Обработчики
# ==============================
@dp.message(F.voice)
async def handle_voice(message: Message):
    """Обработка загруженного голосового сообщения"""
    file = await bot.get_file(message.voice.file_id)
    file_path = file.file_path

    file_ext = os.path.splitext(file_path)[1] or ".ogg"

    # создаём поддиректорию по дате
    today = datetime.utcnow().strftime("%Y-%m-%d")
    day_dir = os.path.join(SAVE_DIR, today)
    os.makedirs(day_dir, exist_ok=True)

    base_name = f"{message.from_user.id}_{message.message_id}"
    raw_path = os.path.join(day_dir, base_name + file_ext)
    wav_path = os.path.join(day_dir, base_name + ".wav")

    # скачиваем файл
    await bot.download_file(file_path, raw_path)

    # конвертируем в wav
    await convert_to_wav(raw_path, wav_path)

    # обновляем запись в реестре (последнюю без audio для этого пользователя)
    registry = load_registry()
    updated = False
    for rec in reversed(registry):
        if rec["user_id"] == message.from_user.id and rec["audio"] is None:
            rec["audio"] = wav_path
            updated = True
            break
    save_registry(registry)

    if updated:
        await message.answer("✅ Ваш голос успешно сохранен! Спасибо за вклад в проект!")
    else:
        await message.answer("⚠️ Голос сохранен, но в реестре не найдено активной записи. "
                             "Попробуйте снова через меню.")

    # UX — даём послушать обратно
    await message.answer("🔊 Вот ваш загруженный голос:")
    await message.answer_voice(voice=FSInputFile(raw_path))

    await message.answer("Хотите попробовать ещё?", reply_markup=cs.kb2)


@dp.callback_query(lambda c: c.data == "voice_get")
async def handle_voice_button(callback: CallbackQuery):
    """Пользователь запросил текст для озвучки"""
    text = pollinations_generate()
    await callback.answer()  # ответ на callback, чтобы Telegram не ругался

    # создаём новую запись
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

    await callback.message.answer(
        "📢 Отлично, пожалуйста озвучьте следующий текст на казахском языке:"
    )
    await callback.message.answer(text)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветственное сообщение"""
    await message.answer(
        "🎙 Привет! TilDos — это исследовательский проект, цель которого — собрать разнообразные образцы казахской речи.\n\n"
        "Голоса участников помогут создать и обучить системы распознавания и синтеза речи на казахском языке, "
        "которые будут полезны детям и взрослым с особенностями речи (например, при ДЦП или аутизме).",
        reply_markup=cs.kb
    )


# ==============================
# 🚀 Запуск
# ==============================
async def main():
    print("🤖 TilDos Bot запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

