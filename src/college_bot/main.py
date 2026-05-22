import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from college_bot.config import load_settings
from college_bot.db import Database
from college_bot.handlers import router


async def send_lesson_reminders(bot: Bot, db: Database) -> None:
    while True:
        try:
            reminders = await db.get_due_lesson_reminders()
            for item in reminders:
                teacher = " ".join(
                    part
                    for part in [
                        item["teacher_last_name"],
                        item["teacher_first_name"],
                        item["teacher_patronymic"],
                    ]
                    if part
                )
                with suppress(Exception):
                    await bot.send_message(
                        chat_id=item["telegram_user_id"],
                        text=(
                            "Нагадування про заняття\n"
                            f"Через приблизно 30 хвилин: {item['subject_name']}\n"
                            f"Початок: {item['starts_at']:%H:%M}\n"
                            f"Викладач: {teacher}\n"
                            f"Аудиторія: {item['room']}"
                        ),
                    )
                await db.mark_lesson_reminder_sent(
                    student_id=item["student_id"],
                    schedule_id=item["schedule_id"],
                    lesson_date=item["lesson_date"],
                )

            consultation_reminders = await db.get_due_consultation_reminders()
            for item in consultation_reminders:
                teacher = " ".join(
                    part
                    for part in [
                        item["teacher_last_name"],
                        item["teacher_first_name"],
                        item["teacher_patronymic"],
                    ]
                    if part
                )
                student = " ".join(
                    part
                    for part in [item["student_last_name"], item["student_first_name"]]
                    if part
                )
                student_chat_id = item["student_telegram_user_id"]
                teacher_chat_id = item["teacher_telegram_user_id"]
                if student_chat_id:
                    with suppress(Exception):
                        await bot.send_message(
                            chat_id=student_chat_id,
                            text=(
                                "Нагадування про консультацію\n"
                                f"Через приблизно 30 хвилин: {item['starts_at']:%H:%M}-{item['ends_at']:%H:%M}\n"
                                f"Викладач: {teacher}\n"
                                f"Тема: {item['topic']}"
                            ),
                        )
                if teacher_chat_id:
                    with suppress(Exception):
                        await bot.send_message(
                            chat_id=teacher_chat_id,
                            text=(
                                "Нагадування про консультацію\n"
                                f"Через приблизно 30 хвилин: {item['starts_at']:%H:%M}-{item['ends_at']:%H:%M}\n"
                                f"Студент: {student}\n"
                                f"Тема: {item['topic']}"
                            ),
                        )
                await db.mark_consultation_reminder_sent(item["request_id"])
        except Exception:
            logging.exception("Failed to send reminders")

        await asyncio.sleep(60)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()

    db = Database(settings.database_url)
    await db.connect()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage(), db=db)
    dispatcher.include_router(router)
    reminder_task = asyncio.create_task(send_lesson_reminders(bot, db))

    try:
        await dispatcher.start_polling(bot)
    finally:
        reminder_task.cancel()
        with suppress(asyncio.CancelledError):
            await reminder_task
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
