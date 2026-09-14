import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from pytgcalls import idle
from yt_dlp import YoutubeDL

BOT_TOKEN=os.environ["BOT_TOKEN"]
API_ID=int(os.environ["API_ID"])
API_HASH=os.environ["API_HASH"]
SESSION_STRING=os.environ["SESSION_STRING"]

app_pyro=Client("vc_music",api_id=API_ID,api_hash=API_HASH,session_string=SESSION_STRING)
calls=PyTgCalls(app_pyro)
queues={}

def get_audio(query):
    opts={"format":"bestaudio/best","noplaylist":True,"quiet":True,"default_search":"ytsearch1"}
    with YoutubeDL(opts) as ydl:
        info=ydl.extract_info(query,download=False)
    if "entries" in info: info=info["entries"][0]
    return info["url"],info.get("title","Unknown")

async def play(update:Update,context:ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Usage: /play song name")
        return
    query=" ".join(context.args)
    try:
        url,title=await asyncio.to_thread(get_audio,query)
        q=queues.setdefault(chat_id,[])
        q.append((url,title))
        if len(q)==1:
            await calls.join_group_call(chat_id,AudioPiped(url))
            await update.message.reply_text(f"▶️ Playing: {title}")
        else:
            await update.message.reply_text(f"➕ Added: {title}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def skip(update,context):
    chat_id=update.effective_chat.id
    q=queues.get(chat_id,[])
    if len(q)>1:
        q.pop(0)
        url,title=q[0]
        await calls.change_stream(chat_id,AudioPiped(url))
        await update.message.reply_text(f"⏭️ Playing: {title}")
    else:
        queues.pop(chat_id,None)
        await calls.leave_group_call(chat_id)
        await update.message.reply_text("Queue finished.")

async def stop(update,context):
    chat_id=update.effective_chat.id
    queues.pop(chat_id,None)
    try: await calls.leave_group_call(chat_id)
    except: pass
    await update.message.reply_text("⏹️ Stopped.")

async def leave(update,context):
    await stop(update,context)

async def queue(update,context):
    q=queues.get(update.effective_chat.id,[])
    await update.message.reply_text("\n".join(f"{i+1}. {x[1]}" for i,x in enumerate(q)) or "Queue empty.")

async def start():
    tg=Application.builder().token(BOT_TOKEN).build()
    tg.add_handler(CommandHandler("play",play))
    tg.add_handler(CommandHandler("skip",skip))
    tg.add_handler(CommandHandler("stop",stop))
    tg.add_handler(CommandHandler("leave",leave))
    tg.add_handler(CommandHandler("queue",queue))
    await tg.initialize(); await tg.start(); await tg.updater.start_polling()
    await app_pyro.start(); await calls.start()
    await idle()

if __name__=="__main__":
    asyncio.run(start())
