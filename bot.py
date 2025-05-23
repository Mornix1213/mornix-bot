import os
import json
import logging
import subprocess
import platform
import socket
import struct
from PIL import ImageGrab
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
import psutil

try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    pycaw_available = True
except ImportError:
    pycaw_available = False

# Константы
MAC_INPUT = 1
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE_DIR, 'temp_files'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'temp_wallpapers'), exist_ok=True)
LOG_FILE = os.path.join(BASE_DIR, 'bot_logs.txt')
COMMANDS_FILE = os.path.join(BASE_DIR, 'user_commands.json')

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот управления ПК.\nby: Mornix\n\nНажмите /help для списка команд."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/wake — Разбудить ПК\n"
        "/screenshot — Сделать скриншот\n"
        "/cpu — Загрузка CPU\n"
        "/shutdown — Выключить ПК\n"
        "/notepad — Запустить блокнот\n"
        "/createfolder <имя> — Создать папку\n"
        "/delete <имя> — Удалить файл/папку\n"
        "/logs — Логи\n"
        "/wallpaper — Изменить обои (отправьте фото)\n"
        "/volume <0-100> — Установить громкость\n"
        "/openurl <ссылка> — Открыть URL\n"
        "/google <запрос> — Поиск в Google\n"
        "\nПользовательские команды:\n"
        "/usercommand <имя> <путь> — Добавить команду\n"
        "/run <имя> — Запустить пользовательскую команду\n"
        "/listcommands — Список пользовательских команд\n"
        "/editcommand <имя> <новый путь> — Изменить команду\n"
        "/deletecommand <имя> — Удалить команду"
    )

async def wake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите MAC-адрес устройства, которое хотите разбудить:")
    return MAC_INPUT

async def receive_mac(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mac = update.message.text
    try:
        mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
        magic = b"\xff" * 6 + mac_bytes * 16
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic, ('<broadcast>', 9))
        await update.message.reply_text("Magic Packet отправлен. Убедитесь, что Wake-on-LAN включён в BIOS.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
    return ConversationHandler.END

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    img = ImageGrab.grab()
    path = os.path.join(BASE_DIR, 'temp_files', 'screenshot.png')
    img.save(path)
    await update.message.reply_photo(photo=open(path, 'rb'))

async def cpu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usage = psutil.cpu_percent()
    await update.message.reply_text(f"Загрузка CPU: {usage}%")

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    os.system("shutdown /s /t 1")

async def notepad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subprocess.Popen(["notepad.exe"])

async def createfolder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name = " ".join(context.args)
        os.makedirs(name, exist_ok=True)
        await update.message.reply_text(f"Папка '{name}' создана.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        path = " ".join(context.args)
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
        await update.message.reply_text(f"'{path}' удалено.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(LOG_FILE, 'rb') as f:
        await update.message.reply_document(f)

async def wallpaper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        path = os.path.join(BASE_DIR, 'temp_wallpapers', 'wall.jpg')
        await file.download_to_drive(path)
        ctypes = __import__('ctypes')
        SPI_SETDESKWALLPAPER = 20
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, path, 3)
        await update.message.reply_text("Обои изменены.")
    else:
        await update.message.reply_text("Отправьте изображение.")

async def volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not pycaw_available:
        await update.message.reply_text("pycaw не установлена. Установи: pip install pycaw")
        return
    try:
        level = int(context.args[0]) / 100
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level, None)
        await update.message.reply_text(f"Громкость установлена на {context.args[0]}%")
    except:
        await update.message.reply_text("Ошибка. Пример: /volume 50")

async def openurl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import webbrowser
    url = " ".join(context.args)
    webbrowser.open(url)
    await update.message.reply_text(f"Открыт URL: {url}")

async def google(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    url = f"https://www.google.com/search?q={query}"
    import webbrowser
    webbrowser.open(url)
    await update.message.reply_text(f"Поиск Google: {url}")

# Работа с пользовательскими командами
def load_user_commands():
    if os.path.exists(COMMANDS_FILE):
        with open(COMMANDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user_commands(data):
    with open(COMMANDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def usercommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name, path = context.args[0], " ".join(context.args[1:])
        commands = load_user_commands()
        commands[name] = path
        save_user_commands(commands)
        await update.message.reply_text(f"Команда '{name}' добавлена.")
    except:
        await update.message.reply_text("Пример: /usercommand editor C:/Windows/notepad.exe")

async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.args[0]
    commands = load_user_commands()
    if name in commands:
        subprocess.Popen(commands[name], shell=True)
        await update.message.reply_text(f"Запущено: {name}")
    else:
        await update.message.reply_text("Команда не найдена.")

async def listcommands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = load_user_commands()
    text = "\n".join(f"{k}: {v}" for k, v in commands.items()) or "Нет команд."
    await update.message.reply_text(text)

async def editcommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name, path = context.args[0], " ".join(context.args[1:])
        commands = load_user_commands()
        if name in commands:
            commands[name] = path
            save_user_commands(commands)
            await update.message.reply_text(f"Команда '{name}' обновлена.")
        else:
            await update.message.reply_text("Команда не найдена.")
    except:
        await update.message.reply_text("Пример: /editcommand editor C:/NewPath/notepad.exe")

async def deletecommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.args[0]
    commands = load_user_commands()
    if name in commands:
        del commands[name]
        save_user_commands(commands)
        await update.message.reply_text(f"Команда '{name}' удалена.")
    else:
        await update.message.reply_text("Команда не найдена.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

# Запуск
def main():
    application = ApplicationBuilder().token("8149263824:AAHUnVBAbmB1EPFJB-Jw74uT19eJvO5DiuQ").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("wake", wake)],
        states={MAC_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_mac)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)

    # Команды
    application.add_handler(CommandHandler("screenshot", screenshot))
    application.add_handler(CommandHandler("cpu", cpu))
    application.add_handler(CommandHandler("shutdown", shutdown))
    application.add_handler(CommandHandler("notepad", notepad))
    application.add_handler(CommandHandler("createfolder", createfolder))
    application.add_handler(CommandHandler("delete", delete))
    application.add_handler(CommandHandler("logs", logs))
    application.add_handler(CommandHandler("wallpaper", wallpaper))
    application.add_handler(CommandHandler("volume", volume))
    application.add_handler(CommandHandler("openurl", openurl))
    application.add_handler(CommandHandler("google", google))

    # Пользовательские
    application.add_handler(CommandHandler("usercommand", usercommand))
    application.add_handler(CommandHandler("run", run))
    application.add_handler(CommandHandler("listcommands", listcommands))
    application.add_handler(CommandHandler("editcommand", editcommand))
    application.add_handler(CommandHandler("deletecommand", deletecommand))

    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
