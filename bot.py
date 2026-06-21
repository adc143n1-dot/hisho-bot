"""
秘書G Telegram Bot
Groq APIを使った全機能秘書ボット
"""

import os
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# GroqクライアントをOpenAI互換で使用
from openai import OpenAI

# ログ設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 環境変数から設定を取得
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# Groqクライアントの初期化（OpenAI互換）
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ユーザーごとの会話履歴とメモを保存
user_data = {}

# 秘書のシステムプロンプト
SYSTEM_PROMPT = """あなたは優秀な日本語対応の個人秘書です。以下の役割を担っています：

1. **日常会話・質問対応**：どんな質問にも丁寧に答える
2. **スケジュール管理**：予定の追加・確認・提案ができる
3. **メモ管理**：重要な情報をメモとして記録・呼び出しができる
4. **タスク管理**：やることリストの管理ができる
5. **情報収集・調査**：様々な情報を提供できる
6. **文書作成**：メール・文書・報告書などの作成支援
7. **アドバイス**：ビジネス・プライベートの相談に乗る

常に以下を心がけてください：
- 丁寧で親しみやすい日本語で話す
- わからないことは正直に伝える
- 具体的で実用的なアドバイスをする
- ユーザーの状況を記憶して文脈に合った返答をする

メモやスケジュールの管理は会話の中で自然に行い、ユーザーが「メモして」「予定を追加して」と言ったら確実に記録します。"""


def get_user_context(user_id: int) -> dict:
    """ユーザーデータを取得（なければ初期化）"""
    if user_id not in user_data:
        user_data[user_id] = {
            'history': [],
            'memos': [],
            'schedules': [],
            'tasks': []
        }
    return user_data[user_id]


def build_messages(user_id: int, new_message: str) -> list:
    """APIに送るメッセージリストを構築"""
    context = get_user_context(user_id)
    
    extra_context = ""
    if context['memos']:
        extra_context += f"\n\n【現在のメモ一覧】\n" + "\n".join(
            [f"- {m['content']} ({m['date']})" for m in context['memos']]
        )
    if context['schedules']:
        extra_context += f"\n\n【現在のスケジュール一覧】\n" + "\n".join(
            [f"- {s['content']} ({s['date']})" for s in context['schedules']]
        )
    if context['tasks']:
        extra_context += f"\n\n【現在のタスク一覧】\n" + "\n".join(
            [f"- [{' 完了' if t['done'] else '未完了'}] {t['content']}" for t in context['tasks']]
        )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + extra_context}
    ]
    
    recent_history = context['history'][-10:]
    messages.extend(recent_history)
    messages.append({"role": "user", "content": new_message})
    
    return messages


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"こんにちは、{user.first_name}さん！\n"
        "私は秘書Gです。何でもお気軽にどうぞ！\n\n"
        "📝 できること：\n"
        "・何でも質問に答えます\n"
        "・メモを取ります（「〇〇をメモして」）\n"
        "・スケジュール管理（「〇月〇日に〇〇を追加して」）\n"
        "・タスク管理（「やることに〇〇を追加して」）\n"
        "・文書作成のお手伝い\n\n"
        "/memo - メモ一覧を表示\n"
        "/schedule - スケジュール一覧を表示\n"
        "/task - タスク一覧を表示\n"
        "/clear - 会話履歴をリセット"
    )


async def show_memo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ctx = get_user_context(user_id)
    if not ctx['memos']:
        await update.message.reply_text("📝 現在メモはありません。")
    else:
        memo_text = "📝 メモ一覧\n\n"
        for i, m in enumerate(ctx['memos'], 1):
            memo_text += f"{i}. {m['content']}\n   ({m['date']})\n\n"
        await update.message.reply_text(memo_text)


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ctx = get_user_context(user_id)
    if not ctx['schedules']:
        await update.message.reply_text("📅 現在スケジュールはありません。")
    else:
        schedule_text = "📅 スケジュール一覧\n\n"
        for i, s in enumerate(ctx['schedules'], 1):
            schedule_text += f"{i}. {s['content']}\n   ({s['date']})\n\n"
        await update.message.reply_text(schedule_text)


async def show_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ctx = get_user_context(user_id)
    if not ctx['tasks']:
        await update.message.reply_text("✅ 現在タスクはありません。")
    else:
        task_text = "✅ タスク一覧\n\n"
        for i, t in enumerate(ctx['tasks'], 1):
            status = "✓" if t['done'] else "○"
            task_text += f"{i}. [{status}] {t['content']}\n"
        await update.message.reply_text(task_text)


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_data:
        user_data[user_id]['history'] = []
    await update.message.reply_text("🔄 会話履歴をリセットしました！")


def save_memo_from_response(user_id: int, user_message: str, ai_response: str):
    ctx = get_user_context(user_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if any(word in user_message for word in ['メモして', 'メモ', '覚えて', '記録して']):
        ctx['memos'].append({'content': user_message, 'date': now})
    if any(word in user_message for word in ['予定', 'スケジュール', '日程']):
        ctx['schedules'].append({'content': user_message, 'date': now})
    if any(word in user_message for word in ['タスク', 'やること', 'TODO', 'todo']):
        ctx['tasks'].append({'content': user_message, 'done': False, 'date': now})


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    await update.message.reply_text("⌛ 考え中...")
    try:
        messages = build_messages(user_id, user_message)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=2048,
            temperature=0.7
        )
        ai_response = response.choices[0].message.content
        ctx = get_user_context(user_id)
        ctx['history'].append({"role": "user", "content": user_message})
        ctx['history'].append({"role": "assistant", "content": ai_response})
        save_memo_from_response(user_id, user_message, ai_response)
        await update.message.reply_text(ai_response)
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        await update.message.reply_text("申し訳ありません、エラーが発生しました。\nもう一度試してみてください。")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("memo", show_memo))
    app.add_handler(CommandHandler("schedule", show_schedule))
    app.add_handler(CommandHandler("task", show_task))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("秘書Gボットを起動します...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
