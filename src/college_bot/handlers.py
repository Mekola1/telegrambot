from __future__ import annotations

from datetime import date, time

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from college_bot.db import WEEKDAYS, Database
from college_bot.keyboards import (
    ADMIN_MENU,
    CONTACT_REQUEST_KEYBOARD,
    MAIN_MENU,
    ROLE_SELECTION_KEYBOARD,
    STAFF_MENU,
    STAFF_ROLE_SELECTION_KEYBOARD,
    admin_account_role_keyboard,
    admin_consultations_keyboard,
    admin_requests_keyboard,
    confirm_action_keyboard,
    consultation_dates_keyboard,
    consultation_slots_keyboard,
    courses_keyboard,
    faq_categories_keyboard,
    refresh_keyboard,
    requests_keyboard,
    support_queue_keyboard,
    support_categories_keyboard,
    teacher_consultations_keyboard,
    teachers_keyboard,
)
from college_bot.ui import field, h, intro_panel, muted, section, title


router = Router()
ADMIN_CONSULTATIONS_PAGE_SIZE = 5
ADMIN_PANEL_CONSULTATIONS_LIMIT = 5


STAFF_ROLE_LABELS = {
    "teacher": "викладача",
    "admin": "адміністратора",
}


HELP_TEXT = """<b>Доступні команди</b>

/start - почати роботу або підтвердити особистість
/login - обрати роль і увійти
/staff - вхід для викладача або адміністратора
/whoami - показати, ким ви зараз увійшли
/logout - вийти з поточного профілю
/help - показати цю довідку
/cancel - скасувати поточну дію

<b>Студентське меню</b>
Мій профіль - ваші дані, група, курс і контакти
Новини - актуальні оголошення коледжу
Мої предмети - список доступних предметів
Мої викладачі - викладачі та контакти
Розклад - розклад занять
Інформація про коледж - адреса, приймальня, бібліотека
Запис на консультацію - вибір викладача, дати й вільного слота
Технічна підтримка - створити звернення з категорією
Мої заявки - статус консультацій і звернень
FAQ - пошук відповідей на типові питання
Оцінки - ваші оцінки
Завдання - дедлайни та домашні завдання
Матеріали - посилання і навчальні матеріали
Нагадування - увімкнути або вимкнути нагадування про пари
Вийти - відвʼязати Telegram від поточного користувача

<b>Меню працівника</b>
Профіль працівника - email, телефон і ролі
Мої консультації викладача - записи студентів до викладача
Додати слот консультації - створити вільний час для запису студентів
Вийти - відвʼязати Telegram від поточного користувача"""


WELCOME_TEXT = intro_panel(
    "Вітаю! Це бот коледжу.",
    """Щоб почати роботу, оберіть вашу роль кнопкою нижче.

Після вибору бот попросить підтвердити особистість:
- студент: номер телефону з бази;
- працівник: номер телефону з бази.""",
)


MENU_TEXTS = {
    "Мій профіль",
    "Новини",
    "Мої предмети",
    "Мої викладачі",
    "Розклад",
    "Інформація про коледж",
    "Запис на консультацію",
    "Технічна підтримка",
    "Мої заявки",
    "FAQ",
    "Оцінки",
    "Завдання",
    "Матеріали",
    "Нагадування",
    "Адмін-панель",
    "Консультації",
    "Додати акаунт",
    "Додати студента",
    "Додати викладача",
    "Профіль працівника",
    "Мої консультації викладача",
    "Додати слот консультації",
    "Черга підтримки",
    "Вийти",
}


class AuthStates(StatesGroup):
    waiting_for_phone = State()


class StaffAuthStates(StatesGroup):
    waiting_for_role = State()
    waiting_for_phone = State()


class ConsultationStates(StatesGroup):
    waiting_for_slot = State()
    waiting_for_topic = State()


class SupportStates(StatesGroup):
    waiting_for_message = State()


class FaqStates(StatesGroup):
    waiting_for_query = State()


class TeacherSlotStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_start = State()
    waiting_for_end = State()


class SupportResolutionStates(StatesGroup):
    waiting_for_comment = State()


class AdminAccountStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_role = State()


class AdminStudentStates(StatesGroup):
    waiting_for_student_id = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_last_name = State()
    waiting_for_first_name = State()
    waiting_for_patronymic = State()
    waiting_for_course = State()


class AdminTeacherStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_last_name = State()
    waiting_for_first_name = State()
    waiting_for_patronymic = State()
    waiting_for_office = State()
    waiting_for_notes = State()


def full_name(row: dict) -> str:
    parts = [row.get("last_name"), row.get("first_name"), row.get("patronymic")]
    return " ".join(part for part in parts if part)


def short_name(last_name: str | None, first_name: str | None) -> str:
    return " ".join(part for part in [last_name, first_name] if part)


def status_uk(status: str) -> str:
    labels = {
        "new": "нова",
        "approved": "підтверджена",
        "rejected": "відхилена",
        "done": "виконана",
        "cancelled": "скасована",
        "in_progress": "в роботі",
        "resolved": "вирішена",
        "closed": "закрита",
    }
    return labels.get(status, status)


def roles_set(row: dict | None) -> set[str]:
    if not row:
        return set()
    return {role.strip() for role in (row.get("roles") or "").split(",") if role.strip()}


def own_contact_phone(message: Message) -> str | None:
    contact = message.contact
    if not contact or contact.user_id != message.from_user.id:
        return None
    return contact.phone_number


def optional_text(value: str) -> str | None:
    value = value.strip()
    if value in {"", "-"}:
        return None
    return value


async def menu_for_user(db: Database, telegram_user_id: int):
    user = await db.get_user_by_telegram(telegram_user_id)
    active_role = user.get("active_role") if user else None
    if active_role == "student":
        return MAIN_MENU
    if active_role == "admin":
        return ADMIN_MENU
    if active_role == "teacher":
        return STAFF_MENU
    return ROLE_SELECTION_KEYBOARD


async def is_active_admin(db: Database, telegram_user_id: int) -> bool:
    return await db.is_active_role(telegram_user_id, "admin")


async def is_active_student(db: Database, telegram_user_id: int) -> bool:
    return await db.is_active_role(telegram_user_id, "student")


async def is_active_teacher(db: Database, telegram_user_id: int) -> bool:
    return await db.is_active_role(telegram_user_id, "teacher")


async def ensure_authenticated(message: Message, db: Database) -> bool:
    if not await is_active_student(db, message.from_user.id):
        await message.answer(
            "Цей розділ доступний тільки у студентському інтерфейсі. Натисніть /logout і увійдіть як студент."
        )
        return False

    student = await db.get_student_by_telegram(message.from_user.id)
    if student:
        return True

    await message.answer(
        "Спочатку потрібно підтвердити особистість. Натисніть /start, оберіть роль і підтвердьте телефон."
    )
    return False


async def ensure_staff_role(message: Message, db: Database, role: str) -> bool:
    if await db.has_role(message.from_user.id, role) and await db.is_active_role(message.from_user.id, role):
        return True
    await message.answer("Цей розділ недоступний для вашої ролі. Для входу працівника натисніть /staff.")
    return False


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await message.answer(
        intro_panel("Дію скасовано", "Поточний сценарій зупинено. Можете обрати іншу дію з меню."),
        reply_markup=await menu_for_user(db, message.from_user.id),
    )


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await message.answer(HELP_TEXT, reply_markup=await menu_for_user(db, message.from_user.id))


@router.message(Command("whoami"))
async def whoami(message: Message, db: Database) -> None:
    user = await db.get_user_by_telegram(message.from_user.id)
    if not user:
        await message.answer(
            intro_panel("Ви не авторизовані", "Натисніть /start або /login і оберіть роль для входу."),
            reply_markup=ROLE_SELECTION_KEYBOARD,
        )
        return

    lines = [
        title("Поточний вхід"),
        field("User ID", user["id"]),
        field("Email", user["email"]),
        field("Телефон", muted(user["phone"])),
        field("Активна роль", muted(user.get("active_role"))),
        field("Ролі", user["roles"] or "не призначено"),
    ]
    student = await db.get_student_by_telegram(message.from_user.id)
    if student:
        lines.extend(
            [
                section("Студент"),
                field("Student ID", student["id"]),
                field("ПІБ", full_name(student)),
                field("Група", student["group_code"]),
            ]
        )
    teacher = await db.get_teacher_profile_by_telegram(message.from_user.id)
    if teacher:
        lines.extend(
            [
                section("Викладач"),
                field("Teacher ID", teacher["id"]),
                field("ПІБ", full_name(teacher)),
                field("Кабінет", muted(teacher["office"])),
            ]
        )
    await message.answer("\n".join(lines), reply_markup=await menu_for_user(db, message.from_user.id))


@router.message(Command("logout"))
@router.message(F.text == "Вийти")
async def logout(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    logged_out = await db.logout_user(message.from_user.id)
    if logged_out:
        await message.answer(
            intro_panel(
                "Ви вийшли",
                "Telegram більше не привʼязаний до користувача.\n\nОберіть роль, щоб увійти знову:",
            ),
            reply_markup=ROLE_SELECTION_KEYBOARD,
        )
    else:
        await message.answer(
            intro_panel("Вхід не знайдено", "Ви ще не були авторизовані. Оберіть роль для входу:"),
            reply_markup=ROLE_SELECTION_KEYBOARD,
        )


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    user = await db.get_user_by_telegram(message.from_user.id)
    active_role = user.get("active_role") if user else None

    if user and active_role == "admin":
        await message.answer(
            intro_panel(
                "Вітаю! Активна роль: адміністратор.",
                f"{field('Email', user['email'])}\n{field('Ролі', user['roles'])}\n\n{HELP_TEXT}",
            ),
            reply_markup=ADMIN_MENU,
        )
        return

    if user and active_role == "teacher":
        await message.answer(
            intro_panel(
                "Вітаю! Активна роль: викладач.",
                f"{field('Email', user['email'])}\n{field('Ролі', user['roles'])}\n\n{HELP_TEXT}",
            ),
            reply_markup=STAFF_MENU,
        )
        return

    if user and active_role == "student":
        student = await db.get_student_by_telegram(message.from_user.id)
        if not student:
            await message.answer(
                intro_panel(
                    "Студентський профіль не знайдено",
                    "Ваш акаунт має активну роль student, але запису в таблиці students немає. Увійдіть іншою роллю або зверніться до адміністратора.",
                ),
                reply_markup=ROLE_SELECTION_KEYBOARD,
            )
            return
        await message.answer(
            intro_panel(
                f"Вітаю, {full_name(student)}!",
                f"{field('Група', student['group_code'])}\n\n{HELP_TEXT}",
            ),
            reply_markup=MAIN_MENU,
        )
        return

    if user and not active_role:
        await message.answer(
            intro_panel(
                "Потрібно обрати активну роль",
                f"{field('Email', user['email'])}\n{field('Ролі', user['roles'])}\n\nНатисніть роль нижче і підтвердьте телефон.",
            ),
            reply_markup=ROLE_SELECTION_KEYBOARD,
        )
        return

    await message.answer(WELCOME_TEXT, reply_markup=ROLE_SELECTION_KEYBOARD)


@router.callback_query(F.data.startswith("auth_role:"))
async def auth_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.split(":")[1]
    await state.clear()

    if role == "student":
        await state.set_state(AuthStates.waiting_for_phone)
        await callback.message.edit_text("<b>Вхід студента</b>")
        await callback.message.answer(
            "Натисніть «Поділитися телефоном». Бот приймає тільки ваш Telegram-контакт, щоб ніхто не міг увійти за чужим номером.",
            reply_markup=CONTACT_REQUEST_KEYBOARD,
        )
        await callback.answer()
        return

    if role not in STAFF_ROLE_LABELS:
        await callback.answer("Невідома роль.", show_alert=True)
        return

    await state.update_data(staff_role=role)
    await state.set_state(StaffAuthStates.waiting_for_phone)
    await callback.message.edit_text(f"<b>Вхід {STAFF_ROLE_LABELS[role]}</b>")
    await callback.message.answer(
        "Натисніть «Поділитися телефоном». Бот приймає тільки ваш Telegram-контакт.",
        reply_markup=CONTACT_REQUEST_KEYBOARD,
    )
    await callback.answer()


@router.message(Command("login"))
async def login(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=ROLE_SELECTION_KEYBOARD)


@router.message(Command("staff"))
async def staff_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(StaffAuthStates.waiting_for_role)
    await message.answer(
        "<b>Вхід працівника</b>\n\nОберіть вашу роль:",
        reply_markup=STAFF_ROLE_SELECTION_KEYBOARD,
    )


@router.message(StaffAuthStates.waiting_for_role)
async def staff_waiting_for_role(message: Message) -> None:
    await message.answer("Оберіть роль кнопкою під повідомленням або натисніть /cancel.")


@router.message(StaffAuthStates.waiting_for_phone)
async def staff_phone(message: Message, state: FSMContext, db: Database) -> None:
    phone = own_contact_phone(message)
    text = (message.text or "").strip()
    if text in MENU_TEXTS:
        await state.clear()
        await message.answer("Вхід працівника скасовано. Для повторного входу натисніть /staff.")
        return

    if message.contact and not phone:
        await message.answer("Надішліть саме свій контакт кнопкою Telegram.")
        return

    if not phone:
        await message.answer("Натисніть кнопку «Поділитися телефоном». Ручне введення номера не приймається.")
        return

    data = await state.get_data()
    role = data.get("staff_role")
    if role not in STAFF_ROLE_LABELS:
        await state.clear()
        await message.answer("Не обрано роль працівника. Почніть вхід з /start або /staff.")
        return

    user = await db.verify_staff_phone_login(
        phone=phone,
        telegram_user_id=message.from_user.id,
        role=role,
    )
    if not user:
        await state.clear()
        await message.answer("Не вдалося підтвердити працівника. Перевірте роль і телефон.")
        return

    await state.clear()
    await message.answer(
        f"<b>Вхід працівника виконано.</b>\nEmail: {h(user['email'])}\nРолі: {h(user['roles'])}",
        reply_markup=await menu_for_user(db, message.from_user.id),
    )


@router.message(AuthStates.waiting_for_phone)
async def auth_phone(message: Message, state: FSMContext, db: Database) -> None:
    phone = own_contact_phone(message)
    text = (message.text or "").strip()
    if text in MENU_TEXTS:
        await state.clear()
        await message.answer(
            "Авторизацію скасовано. Щоб користуватися меню, спочатку натисніть /start і підтвердьте телефон."
        )
        return

    if message.contact and not phone:
        await message.answer("Надішліть саме свій контакт кнопкою Telegram.")
        return

    if not phone:
        await message.answer("Натисніть кнопку «Поділитися телефоном». Ручне введення номера не приймається.")
        return

    student = await db.verify_student_phone_login(
        phone=phone,
        telegram_user_id=message.from_user.id,
    )
    if not student:
        await message.answer(
            "Не вдалося підтвердити студента. Перевірте телефон або зверніться до адміністрації, якщо номер у базі застарів."
        )
        await state.clear()
        return

    await state.clear()
    await message.answer(
        f"<b>Особистість підтверджено.</b>\nВітаю, {h(full_name(student))}!\n\n{HELP_TEXT}",
        reply_markup=MAIN_MENU,
    )


@router.message(F.text == "Мій профіль")
async def my_profile(message: Message, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return
    student = await db.get_student_by_telegram(message.from_user.id)

    await message.answer(
        "\n".join(
            [
                title("Ваш профіль"),
                field("ID", student["id"]),
                field("ПІБ", full_name(student)),
                field("Група", student["group_code"]),
                field("Курс", student["year_number"]),
                field("Спеціальність", student["course_name"]),
                field("Email", student["email"]),
                field("Телефон", muted(student["phone"])),
                field("Ролі", student["roles"] or "не призначено"),
            ]
        )
    )


@router.message(F.text == "Профіль працівника")
async def staff_profile(message: Message, db: Database) -> None:
    user = await db.get_user_by_telegram(message.from_user.id)
    active_role = user.get("active_role") if user else None
    if active_role not in {"teacher", "admin"}:
        await message.answer("Профіль працівника недоступний. Для входу натисніть /staff.")
        return

    await message.answer(
        "\n".join(
            [
                title("Профіль працівника"),
                field("User ID", user["id"]),
                field("Email", user["email"]),
                field("Телефон", muted(user["phone"])),
                field("Ролі", user["roles"]),
            ]
        ),
        reply_markup=await menu_for_user(db, message.from_user.id),
    )


@router.message(F.text == "Додати акаунт")
async def admin_add_account_start(message: Message, state: FSMContext, db: Database) -> None:
    if not await is_active_admin(db, message.from_user.id):
        await message.answer("Додавати користувачів може тільки адміністратор.")
        return
    await state.clear()
    await state.set_state(AdminAccountStates.waiting_for_phone)
    await message.answer(
        "Введіть телефон нового акаунта. Наприклад: +380667148290.",
        reply_markup=await menu_for_user(db, message.from_user.id),
    )


@router.message(AdminAccountStates.waiting_for_phone)
async def admin_add_account_phone(message: Message, state: FSMContext) -> None:
    phone = (message.text or "").strip()
    if len(phone) < 7:
        await message.answer("Телефон виглядає занадто коротким. Введіть номер ще раз.")
        return
    await state.update_data(phone=phone)
    await state.set_state(AdminAccountStates.waiting_for_email)
    await message.answer("Введіть email акаунта. Наприклад: admin@college.local.")


@router.message(AdminAccountStates.waiting_for_email)
async def admin_add_account_email(message: Message, state: FSMContext) -> None:
    email = (message.text or "").strip()
    if "@" not in email:
        await message.answer("Введіть email у правильному форматі.")
        return
    await state.update_data(email=email)
    await state.set_state(AdminAccountStates.waiting_for_role)
    await message.answer(
        "Оберіть роль акаунта:",
        reply_markup=admin_account_role_keyboard(),
    )


@router.callback_query(F.data.startswith("admin_new_account_role:"))
async def admin_add_account_role(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    if not await is_active_admin(db, callback.from_user.id):
        await callback.answer("Недостатньо прав.", show_alert=True)
        return
    role = callback.data.split(":")[1]
    data = await state.get_data()
    user_id = await db.create_user_account(data["email"], data["phone"], role)
    await state.clear()
    if user_id is None:
        await callback.message.edit_text("Не вдалося створити акаунт. Перевірте роль і дані.")
        await callback.answer()
        return
    await callback.message.edit_text(
        "\n".join(
            [
                "Акаунт створено або оновлено.",
                field("User ID", user_id),
                field("Email", data["email"]),
                field("Телефон", data["phone"]),
                field("Роль", role),
            ]
        )
    )
    await callback.answer("Готово.")


@router.message(F.text == "Додати студента")
async def admin_add_student_start(message: Message, state: FSMContext, db: Database) -> None:
    if not await is_active_admin(db, message.from_user.id):
        await message.answer("Додавати студентів може тільки адміністратор.")
        return
    await state.clear()
    await state.set_state(AdminStudentStates.waiting_for_student_id)
    await message.answer("Введіть ID студента числом. Наприклад: 2001.")


@router.message(AdminStudentStates.waiting_for_student_id)
async def admin_add_student_id(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("ID студента має бути числом.")
        return
    await state.update_data(student_id=int(text))
    await state.set_state(AdminStudentStates.waiting_for_phone)
    await message.answer("Введіть телефон студента.")


@router.message(AdminStudentStates.waiting_for_phone)
async def admin_add_student_phone(message: Message, state: FSMContext) -> None:
    phone = (message.text or "").strip()
    if len(phone) < 7:
        await message.answer("Телефон виглядає занадто коротким. Введіть номер ще раз.")
        return
    await state.update_data(phone=phone)
    await state.set_state(AdminStudentStates.waiting_for_email)
    await message.answer("Введіть email студента.")


@router.message(AdminStudentStates.waiting_for_email)
async def admin_add_student_email(message: Message, state: FSMContext) -> None:
    email = (message.text or "").strip()
    if "@" not in email:
        await message.answer("Введіть email у правильному форматі.")
        return
    await state.update_data(email=email)
    await state.set_state(AdminStudentStates.waiting_for_last_name)
    await message.answer("Введіть прізвище студента.")


@router.message(AdminStudentStates.waiting_for_last_name)
async def admin_add_student_last_name(message: Message, state: FSMContext) -> None:
    await state.update_data(last_name=(message.text or "").strip())
    await state.set_state(AdminStudentStates.waiting_for_first_name)
    await message.answer("Введіть імʼя студента.")


@router.message(AdminStudentStates.waiting_for_first_name)
async def admin_add_student_first_name(message: Message, state: FSMContext) -> None:
    await state.update_data(first_name=(message.text or "").strip())
    await state.set_state(AdminStudentStates.waiting_for_patronymic)
    await message.answer("Введіть по батькові або `-`, якщо не потрібно.")


@router.message(AdminStudentStates.waiting_for_patronymic)
async def admin_add_student_patronymic(message: Message, state: FSMContext, db: Database) -> None:
    await state.update_data(patronymic=optional_text(message.text or ""))
    courses = await db.get_courses()
    if not courses:
        await state.clear()
        await message.answer("У базі немає курсів/груп. Спочатку додайте запис у таблицю courses.")
        return
    await state.set_state(AdminStudentStates.waiting_for_course)
    await message.answer("Оберіть групу студента:", reply_markup=courses_keyboard(courses))


@router.callback_query(F.data.startswith("admin_student_course:"))
async def admin_add_student_course(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    if not await is_active_admin(db, callback.from_user.id):
        await callback.answer("Недостатньо прав.", show_alert=True)
        return
    course_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    user_id = await db.create_student_account(
        student_id=int(data["student_id"]),
        email=data["email"],
        phone=data["phone"],
        first_name=data["first_name"],
        patronymic=data.get("patronymic"),
        last_name=data["last_name"],
        course_id=course_id,
    )
    await state.clear()
    if user_id is None:
        await callback.message.edit_text("Не вдалося створити студента. Можливо, ID студента або email уже зайнятий.")
        await callback.answer()
        return
    await callback.message.edit_text(
        "\n".join(
            [
                "Студента створено.",
                field("User ID", user_id),
                field("Student ID", data["student_id"]),
                field("ПІБ", f"{data['last_name']} {data['first_name']} {data.get('patronymic') or ''}".strip()),
                field("Телефон", data["phone"]),
                field("Email", data["email"]),
            ]
        )
    )
    await callback.answer("Готово.")


@router.message(F.text == "Додати викладача")
async def admin_add_teacher_start(message: Message, state: FSMContext, db: Database) -> None:
    if not await is_active_admin(db, message.from_user.id):
        await message.answer("Додавати викладачів може тільки адміністратор.")
        return
    await state.clear()
    await state.set_state(AdminTeacherStates.waiting_for_phone)
    await message.answer("Введіть телефон викладача.")


@router.message(AdminTeacherStates.waiting_for_phone)
async def admin_add_teacher_phone(message: Message, state: FSMContext) -> None:
    phone = (message.text or "").strip()
    if len(phone) < 7:
        await message.answer("Телефон виглядає занадто коротким. Введіть номер ще раз.")
        return
    await state.update_data(phone=phone)
    await state.set_state(AdminTeacherStates.waiting_for_email)
    await message.answer("Введіть email викладача.")


@router.message(AdminTeacherStates.waiting_for_email)
async def admin_add_teacher_email(message: Message, state: FSMContext) -> None:
    email = (message.text or "").strip()
    if "@" not in email:
        await message.answer("Введіть email у правильному форматі.")
        return
    await state.update_data(email=email)
    await state.set_state(AdminTeacherStates.waiting_for_last_name)
    await message.answer("Введіть прізвище викладача.")


@router.message(AdminTeacherStates.waiting_for_last_name)
async def admin_add_teacher_last_name(message: Message, state: FSMContext) -> None:
    await state.update_data(last_name=(message.text or "").strip())
    await state.set_state(AdminTeacherStates.waiting_for_first_name)
    await message.answer("Введіть імʼя викладача.")


@router.message(AdminTeacherStates.waiting_for_first_name)
async def admin_add_teacher_first_name(message: Message, state: FSMContext) -> None:
    await state.update_data(first_name=(message.text or "").strip())
    await state.set_state(AdminTeacherStates.waiting_for_patronymic)
    await message.answer("Введіть по батькові або `-`, якщо не потрібно.")


@router.message(AdminTeacherStates.waiting_for_patronymic)
async def admin_add_teacher_patronymic(message: Message, state: FSMContext) -> None:
    await state.update_data(patronymic=optional_text(message.text or ""))
    await state.set_state(AdminTeacherStates.waiting_for_office)
    await message.answer("Введіть кабінет або `-`, якщо не потрібно.")


@router.message(AdminTeacherStates.waiting_for_office)
async def admin_add_teacher_office(message: Message, state: FSMContext) -> None:
    await state.update_data(office=optional_text(message.text or ""))
    await state.set_state(AdminTeacherStates.waiting_for_notes)
    await message.answer("Введіть примітку щодо консультацій або `-`, якщо не потрібно.")


@router.message(AdminTeacherStates.waiting_for_notes)
async def admin_add_teacher_notes(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    user_id = await db.create_teacher_account(
        email=data["email"],
        phone=data["phone"],
        first_name=data["first_name"],
        patronymic=data.get("patronymic"),
        last_name=data["last_name"],
        office=data.get("office"),
        consultation_notes=optional_text(message.text or ""),
    )
    await state.clear()
    if user_id is None:
        await message.answer("Не вдалося створити викладача. Можливо, email уже привʼязаний до викладача.")
        return
    await message.answer(
        "\n".join(
            [
                "Викладача створено.",
                field("User ID", user_id),
                field("ПІБ", f"{data['last_name']} {data['first_name']} {data.get('patronymic') or ''}".strip()),
                field("Телефон", data["phone"]),
                field("Email", data["email"]),
            ]
        ),
        reply_markup=await menu_for_user(db, message.from_user.id),
    )


@router.message(F.text == "Мої предмети")
async def my_subjects(message: Message, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    subjects = await db.get_student_subjects(message.from_user.id)
    if not subjects:
        await message.answer("Для вас поки не призначено предметів.")
        return

    lines = [title("Ваші предмети")]
    for item in subjects:
        description = item["description"] or "Опис відсутній."
        lines.append(f"\n<b>{h(item['name'])}</b>\n{h(description)}")
    await message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("cancel_consultation:"))
async def cancel_consultation(callback: CallbackQuery, db: Database) -> None:
    if not await is_active_student(db, callback.from_user.id):
        await callback.answer("Спочатку увійдіть як студент.", show_alert=True)
        return
    request_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        f"Підтвердити скасування консультації #{request_id}?",
        reply_markup=confirm_action_keyboard("cancel_consultation", request_id, "cancelled"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_support:"))
async def cancel_support(callback: CallbackQuery, db: Database) -> None:
    if not await is_active_student(db, callback.from_user.id):
        await callback.answer("Спочатку увійдіть як студент.", show_alert=True)
        return
    ticket_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        f"Підтвердити скасування звернення #{ticket_id}?",
        reply_markup=confirm_action_keyboard("cancel_support", ticket_id, "cancelled"),
    )
    await callback.answer()


@router.message(F.text == "Мої консультації викладача")
async def teacher_consultations(message: Message, db: Database) -> None:
    if not await ensure_staff_role(message, db, "teacher"):
        return

    consultations = await db.get_teacher_consultations(message.from_user.id)
    if not consultations:
        await message.answer("У вас немає активних консультацій.", reply_markup=STAFF_MENU)
        return

    lines = [title("Ваші консультації")]
    for item in consultations:
        student = short_name(item["student_last_name"], item["student_first_name"])
        student_info = f"{student}, група {item['group_code']}"
        lines.append(
            f"\n<b>#{item['id']}</b> | {status_uk(item['status'])}"
            f" | {item['requested_date']:%Y-%m-%d}"
            f" {item['starts_at']:%H:%M}-{item['ends_at']:%H:%M}"
            f"\n{field('Студент', student_info)}"
            f"\n{field('Тема', item['topic'])}"
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=teacher_consultations_keyboard(consultations),
    )


@router.callback_query(F.data.startswith("teacher_consultation:"))
async def teacher_consultation_status(callback: CallbackQuery, db: Database) -> None:
    if not await is_active_teacher(db, callback.from_user.id):
        await callback.answer("Недостатньо прав.", show_alert=True)
        return

    _, item_id_text, status = callback.data.split(":")
    await callback.message.edit_text(
        f"Підтвердити зміну статусу консультації #{item_id_text} на «{status_uk(status)}»?",
        reply_markup=confirm_action_keyboard("teacher_consultation", int(item_id_text), status),
    )
    await callback.answer()


@router.message(F.text == "Додати слот консультації")
async def teacher_slot_start(message: Message, state: FSMContext, db: Database) -> None:
    if not await ensure_staff_role(message, db, "teacher"):
        return
    await state.clear()
    await state.set_state(TeacherSlotStates.waiting_for_date)
    await message.answer(
        "\n".join(
            [
                title("Новий слот консультації"),
                "Введіть дату у форматі РРРР-ММ-ДД.",
                "Наприклад: 2026-05-29",
            ]
        )
    )


@router.message(TeacherSlotStates.waiting_for_date)
async def teacher_slot_date(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    try:
        slot_date = date.fromisoformat(text)
    except ValueError:
        await message.answer("Дата має бути у форматі РРРР-ММ-ДД. Наприклад: 2026-05-29.")
        return
    if slot_date < date.today():
        await message.answer("Дата не може бути в минулому. Введіть іншу дату.")
        return
    await state.update_data(slot_date=slot_date.isoformat())
    await state.set_state(TeacherSlotStates.waiting_for_start)
    await message.answer("Введіть час початку у форматі ГГ:ХХ. Наприклад: 14:00.")


@router.message(TeacherSlotStates.waiting_for_start)
async def teacher_slot_start_time(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    try:
        starts_at = time.fromisoformat(text)
    except ValueError:
        await message.answer("Час має бути у форматі ГГ:ХХ. Наприклад: 14:00.")
        return
    await state.update_data(starts_at=starts_at.isoformat(timespec="minutes"))
    await state.set_state(TeacherSlotStates.waiting_for_end)
    await message.answer("Введіть час завершення у форматі ГГ:ХХ. Наприклад: 14:20.")


@router.message(TeacherSlotStates.waiting_for_end)
async def teacher_slot_end_time(message: Message, state: FSMContext, db: Database) -> None:
    text = (message.text or "").strip()
    try:
        ends_at = time.fromisoformat(text)
    except ValueError:
        await message.answer("Час має бути у форматі ГГ:ХХ. Наприклад: 14:20.")
        return
    data = await state.get_data()
    slot_date = date.fromisoformat(data["slot_date"])
    starts_at = time.fromisoformat(data["starts_at"])
    if starts_at >= ends_at:
        await message.answer("Час завершення має бути пізніше за час початку.")
        return
    slot_id = await db.create_teacher_consultation_slot(
        message.from_user.id,
        slot_date,
        starts_at,
        ends_at,
    )
    await state.clear()
    if slot_id is None:
        await message.answer(
            "Не вдалося створити слот. Можливо, такий час уже існує або дата некоректна.",
            reply_markup=STAFF_MENU,
        )
        return
    await message.answer(
        "\n".join(
            [
                "Слот консультації створено.",
                field("ID слота", slot_id),
                field("Дата", f"{slot_date:%d.%m.%Y}"),
                field("Час", f"{starts_at:%H:%M}-{ends_at:%H:%M}"),
            ]
        ),
        reply_markup=STAFF_MENU,
    )


@router.message(F.text == "Черга підтримки")
async def support_queue(message: Message, db: Database) -> None:
    if not await is_active_admin(db, message.from_user.id):
        await message.answer("Черга підтримки доступна тільки адміністратору.")
        return

    tickets = await db.get_support_queue()
    if not tickets:
        await message.answer(
            "Немає відкритих звернень у техпідтримку.",
            reply_markup=await menu_for_user(db, message.from_user.id),
        )
        return

    lines = [title("Черга технічної підтримки")]
    for item in tickets:
        student = short_name(item["student_last_name"], item["student_first_name"])
        lines.append(
            f"\n<b>#{item['id']}</b> | {status_uk(item['status'])} | {h(item['category'])}"
            f"\n{field('Студент', student)}"
            f"\n{h(item['message'])}"
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=support_queue_keyboard(tickets),
    )


@router.callback_query(F.data.startswith("support_ticket:"))
async def support_ticket_status(callback: CallbackQuery, db: Database) -> None:
    if not await is_active_admin(db, callback.from_user.id):
        await callback.answer("Недостатньо прав.", show_alert=True)
        return

    _, item_id_text, status = callback.data.split(":")
    await callback.message.edit_text(
        f"Підтвердити зміну статусу звернення #{item_id_text} на «{status_uk(status)}»?",
        reply_markup=confirm_action_keyboard("support_ticket", int(item_id_text), status),
    )
    await callback.answer()


@router.message(F.text == "Мої викладачі")
async def my_teachers(message: Message, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    teachers = await db.get_student_teachers(message.from_user.id)
    if not teachers:
        await message.answer("Для ваших предметів поки не призначено викладачів.")
        return

    lines = [title("Ваші викладачі")]
    for teacher in teachers:
        lines.append(
            section(full_name(teacher))
            + "\n"
            + "\n".join(
                [
                    field("ID", teacher["id"]),
                    field("Email", teacher["email"]),
                    field("Телефон", muted(teacher["phone"])),
                    field("Кабінет", muted(teacher["office"])),
                    field("Консультації", muted(teacher["consultation_notes"])),
                ]
            )
        )
    await message.answer("\n".join(lines))


@router.message(F.text == "Розклад")
async def schedule(message: Message, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    rows = await db.get_schedule(message.from_user.id)
    if not rows:
        await message.answer("Розклад для вашої групи поки не заповнений.")
        return

    lines = [title("Ваш розклад")]
    for row in rows:
        teacher = " ".join(
            part
            for part in [
                row["teacher_last_name"],
                row["teacher_first_name"],
                row["teacher_patronymic"],
            ]
            if part
        )
        lines.append(
            section(f"{WEEKDAYS[row['weekday']]}, {row['starts_at']:%H:%M}-{row['ends_at']:%H:%M}")
            + f"\n<b>{h(row['subject_name'])}</b>"
            + f"\n{field('Викладач', teacher)}"
            + f"\n{field('Аудиторія', row['room'])}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == "Інформація про коледж")
async def college_info(message: Message, db: Database) -> None:
    info = await db.get_college_info()
    if not info:
        await message.answer("Загальна інформація про коледж поки не заповнена.")
        return

    lines = ["Інформація про коледж:"]
    for item in info:
        lines.append(f"\n{item['title']}\n{item['body']}")
    await message.answer("\n".join(lines))


@router.message(F.text == "Новини")
async def announcements(message: Message, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    rows = await db.get_announcements(message.from_user.id)
    if not rows:
        await message.answer("Актуальних оголошень поки немає.")
        return

    lines = ["Актуальні оголошення:"]
    for row in rows:
        target = row["group_code"] or "усі групи"
        lines.append(
            f"\n{row['published_at']:%Y-%m-%d} | {target}"
            f"\n{row['title']}"
            f"\n{row['body']}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == "FAQ")
async def faq_start(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    categories = await db.get_faq_categories()
    if not categories:
        await state.set_state(FaqStates.waiting_for_query)
        await message.answer("FAQ поки без категорій. Напишіть ключове слово для пошуку.")
        return
    await message.answer(
        "Оберіть категорію FAQ або запустіть пошук за ключовим словом:",
        reply_markup=faq_categories_keyboard(categories),
    )


@router.callback_query(F.data == "faq_search")
async def faq_search_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FaqStates.waiting_for_query)
    await callback.message.edit_text("Напишіть ключове слово або питання. Наприклад: стипендія, довідка, гуртожиток.")
    await callback.answer()


@router.callback_query(F.data.startswith("faq_category:"))
async def faq_category(callback: CallbackQuery, db: Database) -> None:
    category = callback.data.split(":", 1)[1]
    rows = await db.get_faq_by_category(category)
    if not rows:
        await callback.answer("У цій категорії поки немає відповідей.", show_alert=True)
        return
    lines = [title(f"FAQ: {category}")]
    for row in rows:
        lines.append(f"\n<b>{h(row['question'])}</b>\n{h(row['answer'])}")
    await callback.message.edit_text("\n".join(lines))
    await callback.answer()


@router.message(FaqStates.waiting_for_query)
async def faq_search(message: Message, state: FSMContext, db: Database) -> None:
    query_text = (message.text or "").strip()
    if len(query_text) < 2:
        await message.answer("Введіть хоча б 2 символи для пошуку.")
        return

    rows = await db.search_faq(query_text)
    await state.clear()
    if not rows:
        await message.answer(
            "Нічого не знайдено. Спробуйте інше ключове слово.",
            reply_markup=await menu_for_user(db, message.from_user.id),
        )
        return

    lines = ["Знайдені відповіді:"]
    for row in rows:
        lines.append(f"\n{row['category']}: {row['question']}\n{row['answer']}")
    await message.answer("\n".join(lines), reply_markup=await menu_for_user(db, message.from_user.id))


@router.message(F.text == "Оцінки")
async def grades(message: Message, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    rows = await db.get_grades(message.from_user.id)
    if not rows:
        await message.answer("Оцінок поки немає.")
        return

    lines = ["Ваші оцінки:"]
    for row in rows:
        comment = f"\nКоментар: {row['comment']}" if row["comment"] else ""
        lines.append(
            f"\n{row['subject_name']} | {row['graded_at']:%Y-%m-%d}"
            f"\n{row['grade']}/{row['max_grade']}{comment}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == "Завдання")
async def assignments(message: Message, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    rows = await db.get_assignments(message.from_user.id)
    if not rows:
        await message.answer("Активних завдань поки немає.")
        return

    lines = ["Ваші завдання:"]
    for row in rows:
        lines.append(
            f"\n{row['due_date']:%Y-%m-%d} | {row['subject_name']}"
            f"\n{row['title']}"
            f"\n{row['description']}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == "Матеріали")
async def resources(message: Message, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    rows = await db.get_subject_resources(message.from_user.id)
    if not rows:
        await message.answer("Навчальні матеріали для ваших предметів поки не додані.")
        return

    lines = ["Матеріали за предметами:"]
    for row in rows:
        description = f"\n{row['description']}" if row["description"] else ""
        lines.append(f"\n{row['subject_name']}\n{row['title']}\n{row['url']}{description}")
    await message.answer("\n".join(lines))


@router.message(F.text == "Нагадування")
async def reminders(message: Message, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    enabled = await db.toggle_lesson_reminders(message.from_user.id)
    if enabled:
        await message.answer("Нагадування про пари увімкнено. Бот повідомить приблизно за 30 хвилин до заняття.")
    else:
        await message.answer("Нагадування про пари вимкнено.")


@router.message(F.text == "Мої заявки")
async def my_requests(message: Message, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    consultations = await db.get_consultation_requests(message.from_user.id)
    tickets = await db.get_support_tickets(message.from_user.id)
    if not consultations and not tickets:
        await message.answer("У вас поки немає заявок.")
        return

    lines = [title("Ваші заявки")]
    if consultations:
        lines.append(section("Консультації"))
        for item in consultations:
            teacher = full_name(item)
            lines.append(
                f"\n<b>#{item['id']}</b> | {status_uk(item['status'])}"
                f" | {item['requested_date']:%Y-%m-%d}"
                f" {item['starts_at']:%H:%M}-{item['ends_at']:%H:%M}"
                f"\n{field('Викладач', teacher)}"
                f"\n{field('Тема', item['topic'])}"
            )

    if tickets:
        lines.append(section("Техпідтримка"))
        for item in tickets:
            lines.append(
                f"\n<b>#{item['id']}</b> | {status_uk(item['status'])} | {h(item['category'])}"
                f"\n{h(item['message'])}"
            )
            if item.get("resolution_comment"):
                lines.append(field("Коментар", item["resolution_comment"]))

    await message.answer(
        "\n".join(lines),
        reply_markup=requests_keyboard(consultations, tickets),
    )


@router.message(F.text == "Запис на консультацію")
async def consultation_start(message: Message, state: FSMContext, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    teachers = await db.get_student_teachers(message.from_user.id)
    if not teachers:
        await message.answer("Немає доступних викладачів для запису.")
        return

    await state.clear()
    await message.answer(
        "Оберіть викладача для консультації:",
        reply_markup=teachers_keyboard(teachers),
    )


@router.callback_query(F.data.startswith("consult_teacher:"))
async def consultation_teacher(callback: CallbackQuery, db: Database) -> None:
    if not await is_active_student(db, callback.from_user.id):
        await callback.answer("Спочатку увійдіть як студент.", show_alert=True)
        return

    teacher_id = int(callback.data.split(":")[1])
    teacher = await db.get_teacher_by_id_for_student(callback.from_user.id, teacher_id)
    if not teacher:
        await callback.answer("Цей викладач недоступний для вас.", show_alert=True)
        return

    dates = await db.get_available_consultation_dates(callback.from_user.id, teacher_id)
    if not dates:
        await callback.message.edit_text("У цього викладача поки немає вільних слотів.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"<b>Викладач:</b> {h(full_name(teacher))}\nОберіть дату консультації:",
        reply_markup=consultation_dates_keyboard(teacher_id, dates),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("consult_date:"))
async def consultation_date(callback: CallbackQuery, db: Database) -> None:
    if not await is_active_student(db, callback.from_user.id):
        await callback.answer("Спочатку увійдіть як студент.", show_alert=True)
        return

    _, teacher_id_text, date_text = callback.data.split(":")
    teacher_id = int(teacher_id_text)
    try:
        slot_date = date.fromisoformat(date_text)
    except ValueError:
        await callback.answer("Некоректна дата.", show_alert=True)
        return

    slots = await db.get_available_consultation_slots(callback.from_user.id, teacher_id, slot_date)
    if not slots:
        await callback.message.edit_text("На цю дату вільних слотів уже немає. Оберіть іншу дату.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Дата: {slot_date:%d.%m.%Y}\nОберіть вільний час:",
        reply_markup=consultation_slots_keyboard(slots),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("consult_slot:"))
async def consultation_slot(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    if not await is_active_student(db, callback.from_user.id):
        await callback.answer("Спочатку увійдіть як студент.", show_alert=True)
        return

    slot_id = int(callback.data.split(":")[1])
    slot = await db.get_consultation_slot_for_student(callback.from_user.id, slot_id)
    if not slot:
        await callback.answer("Цей слот уже зайнятий або недоступний.", show_alert=True)
        await callback.message.edit_text("Слот уже недоступний. Почніть запис на консультацію ще раз.")
        return

    await state.update_data(slot_id=slot_id)
    await state.set_state(ConsultationStates.waiting_for_topic)
    await callback.message.edit_text(
        "\n".join(
            [
                "Ви обрали слот:",
                f"Викладач: {h(full_name(slot))}",
                f"Дата: {slot['slot_date']:%d.%m.%Y}",
                f"Час: {slot['starts_at']:%H:%M}-{slot['ends_at']:%H:%M}",
                "",
                "Тепер напишіть тему консультації одним повідомленням.",
            ]
        )
    )
    await callback.answer()


@router.message(ConsultationStates.waiting_for_topic)
async def consultation_topic(message: Message, state: FSMContext, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        await state.clear()
        return

    topic = (message.text or "").strip()
    if len(topic) < 5:
        await message.answer("Опишіть тему трохи детальніше.")
        return

    data = await state.get_data()
    request_id = await db.create_consultation_request(
        telegram_user_id=message.from_user.id,
        slot_id=data["slot_id"],
        topic=topic,
    )
    if request_id is None:
        await state.clear()
        await message.answer(
            "На жаль, цей слот уже зайняв інший студент. Оберіть інший час.",
            reply_markup=MAIN_MENU,
        )
        return

    await state.clear()
    await message.answer(
        f"Запит на консультацію зареєстровано. Номер заявки: {request_id}.",
        reply_markup=MAIN_MENU,
    )


@router.message(F.text == "Технічна підтримка")
async def support_start(message: Message, state: FSMContext, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        return

    categories = await db.get_support_categories()
    if not categories:
        await message.answer("Категорії звернень поки не налаштовані.")
        return

    await state.clear()
    await message.answer(
        "Оберіть категорію звернення:",
        reply_markup=support_categories_keyboard(categories),
    )


@router.callback_query(F.data.startswith("support_category:"))
async def support_category(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    if not await is_active_student(db, callback.from_user.id):
        await callback.answer("Спочатку увійдіть як студент.", show_alert=True)
        return

    category_id = int(callback.data.split(":")[1])
    category = await db.get_support_category(category_id)
    if not category:
        await callback.answer("Категорія недоступна.", show_alert=True)
        return

    await state.update_data(category_id=category_id, category_name=category["name"])
    await state.set_state(SupportStates.waiting_for_message)
    await callback.message.edit_text(
        "\n".join(
            [
                f"<b>Категорія:</b> {h(category['name'])}",
                h(category["description"]),
                "",
                "Опишіть звернення одним повідомленням.",
                "Бажано вказати:",
                "- що саме не працює;",
                "- де виникла проблема;",
                "- який текст помилки ви бачите;",
                "- коли це сталося.",
            ]
        )
    )
    await callback.answer()


@router.message(SupportStates.waiting_for_message)
async def support_message(message: Message, state: FSMContext, db: Database) -> None:
    if not await ensure_authenticated(message, db):
        await state.clear()
        return

    text = (message.text or "").strip()
    if len(text) < 10:
        await message.answer("Опишіть проблему детальніше, будь ласка.")
        return

    data = await state.get_data()
    ticket_id = await db.create_support_ticket(
        telegram_user_id=message.from_user.id,
        category_id=data["category_id"],
        message=text,
    )
    await state.clear()
    await message.answer(
        "\n".join(
            [
                "Звернення в технічну підтримку зареєстровано.",
                f"Номер заявки: {ticket_id}",
                f"Категорія: {h(data['category_name'])}",
                "",
                "Ваш опис:",
                h(text),
            ]
        ),
        reply_markup=MAIN_MENU,
    )


def admin_consultations_text(consultations: list[dict], page: int, total_count: int, page_size: int) -> str:
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    lines = [
        title("Консультації"),
        f"Усі записи студентів до всіх викладачів. Сторінка {page + 1} з {total_pages}.",
    ]
    if consultations:
        for item in consultations:
            student = short_name(item["student_last_name"], item["student_first_name"])
            teacher = short_name(item["teacher_last_name"], item["teacher_first_name"])
            lines.append(
                f"\n<b>#{item['id']}</b> | {status_uk(item['status'])} | {item['requested_date']:%Y-%m-%d}"
                f" {item['starts_at']:%H:%M}-{item['ends_at']:%H:%M}"
                f"\n{field('Студент', student)}"
                f"\n{field('Викладач', teacher)}"
                f"\n{field('Тема', item['topic'])}"
            )
    else:
        lines.append("\nКонсультацій поки немає.")
    return "\n".join(lines)


@router.message(F.text == "Консультації")
async def admin_consultations(message: Message, state: FSMContext, db: Database) -> None:
    if not await is_active_admin(db, message.from_user.id):
        await message.answer("Консультації всіх викладачів доступні тільки після входу з роллю адміністратора.")
        return

    page = 0
    total_count = await db.count_admin_consultations()
    consultations = await db.get_admin_consultations(
        limit=ADMIN_CONSULTATIONS_PAGE_SIZE,
        offset=page * ADMIN_CONSULTATIONS_PAGE_SIZE,
    )
    await state.clear()
    await message.answer(
        admin_consultations_text(consultations, page, total_count, ADMIN_CONSULTATIONS_PAGE_SIZE),
        reply_markup=admin_consultations_keyboard(
            consultations,
            page,
            total_count,
            ADMIN_CONSULTATIONS_PAGE_SIZE,
        ),
    )


@router.message(F.text == "Адмін-панель")
async def admin_panel(message: Message, state: FSMContext, db: Database) -> None:
    if not await is_active_admin(db, message.from_user.id):
        await message.answer("Адмін-панель доступна тільки після входу з роллю адміністратора. Натисніть /logout і увійдіть як адміністратор.")
        return

    consultations = await db.get_admin_consultations(limit=ADMIN_PANEL_CONSULTATIONS_LIMIT)
    tickets = await db.get_pending_support_tickets()

    lines = ["Адмін-панель", "Оберіть дію кнопкою під повідомленням."]

    lines.append("\nОстанні консультації:")
    if consultations:
        for item in consultations:
            student = short_name(item["student_last_name"], item["student_first_name"])
            teacher = short_name(item["teacher_last_name"], item["teacher_first_name"])
            lines.append(
                f"#{item['id']} | {status_uk(item['status'])} | {item['requested_date']:%Y-%m-%d}"
                f" {item['starts_at']:%H:%M}-{item['ends_at']:%H:%M}"
                f"\nСтудент: {h(student)}"
                f"\nВикладач: {h(teacher)}"
                f"\nТема: {h(item['topic'])}"
            )
    else:
        lines.append("Консультацій поки немає.")

    lines.append("\nЗвернення в техпідтримку:")
    if tickets:
        for item in tickets:
            student = short_name(item["student_last_name"], item["student_first_name"])
            lines.append(
                f"#{item['id']} | {status_uk(item['status'])} | {h(item['category'])}"
                f"\nСтудент: {h(student)}"
                f"\n{h(item['message'])}"
            )
    else:
        lines.append("Немає відкритих звернень.")

    await state.clear()
    await message.answer(
        "\n".join(lines),
        reply_markup=admin_requests_keyboard(consultations, tickets),
    )


@router.callback_query(F.data.startswith("admin_consultation:"))
async def admin_consultation_status(callback: CallbackQuery, db: Database) -> None:
    if not await is_active_admin(db, callback.from_user.id):
        await callback.answer("Недостатньо прав.", show_alert=True)
        return

    _, item_id_text, status = callback.data.split(":")
    await callback.message.edit_text(
        f"Підтвердити зміну статусу консультації #{item_id_text} на «{status_uk(status)}»?",
        reply_markup=confirm_action_keyboard("admin_consultation", int(item_id_text), status),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_support:"))
async def admin_support_status(callback: CallbackQuery, db: Database) -> None:
    if not await is_active_admin(db, callback.from_user.id):
        await callback.answer("Недостатньо прав.", show_alert=True)
        return

    _, item_id_text, status = callback.data.split(":")
    await callback.message.edit_text(
        f"Підтвердити зміну статусу звернення #{item_id_text} на «{status_uk(status)}»?",
        reply_markup=confirm_action_keyboard("admin_support", int(item_id_text), status),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_cancel")
async def confirm_cancel(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Дію скасовано. За потреби оновіть список кнопкою меню.")
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:"))
async def confirm_action(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    _, kind, item_id_text, status = callback.data.split(":")
    item_id = int(item_id_text)

    updated = False
    target = "список"
    if kind == "cancel_consultation":
        if not await is_active_student(db, callback.from_user.id):
            await callback.answer("Спочатку увійдіть як студент.", show_alert=True)
            return
        updated = await db.cancel_consultation_request(callback.from_user.id, item_id)
        target = "Мої заявки"
    elif kind == "cancel_support":
        if not await is_active_student(db, callback.from_user.id):
            await callback.answer("Спочатку увійдіть як студент.", show_alert=True)
            return
        updated = await db.cancel_support_ticket(callback.from_user.id, item_id)
        target = "Мої заявки"
    elif kind == "teacher_consultation":
        if not await is_active_teacher(db, callback.from_user.id):
            await callback.answer("Недостатньо прав.", show_alert=True)
            return
        updated = await db.update_teacher_consultation_status(callback.from_user.id, item_id, status)
        target = "Мої консультації викладача"
    elif kind == "admin_consultation":
        if not await is_active_admin(db, callback.from_user.id):
            await callback.answer("Недостатньо прав.", show_alert=True)
            return
        updated = await db.update_consultation_status(item_id, status, callback.from_user.id)
        target = "Консультації"
    elif kind in {"support_ticket", "admin_support"}:
        if not await is_active_admin(db, callback.from_user.id):
            await callback.answer("Недостатньо прав.", show_alert=True)
            return
        if status in {"resolved", "closed"}:
            await state.update_data(resolution_kind=kind, item_id=item_id, status=status)
            await state.set_state(SupportResolutionStates.waiting_for_comment)
            await callback.message.edit_text(
                "\n".join(
                    [
                        f"Напишіть короткий коментар для звернення #{item_id}.",
                        "Наприклад: що зроблено, що перевірено або що має зробити студент.",
                        "",
                        "Якщо коментар не потрібен, напишіть: -",
                    ]
                )
            )
            await callback.answer()
            return
        if kind == "support_ticket":
            updated = await db.update_support_status(item_id, status, callback.from_user.id)
            target = "Черга підтримки"
        else:
            updated = await db.update_support_status(item_id, status, callback.from_user.id)
            target = "Адмін-панель"

    if not updated:
        await callback.answer("Не вдалося виконати дію. Можливо, статус уже змінився.", show_alert=True)
        return

    await callback.message.edit_text(
        f"Статус заявки #{item_id} змінено на: {status_uk(status)}.\nОновіть «{target}», щоб побачити актуальний список.",
        reply_markup=refresh_keyboard(
            {
                "Мої заявки": "my_requests",
                "Мої консультації викладача": "teacher_consultations",
                "Черга підтримки": "support_queue",
                "Адмін-панель": "admin",
                "Консультації": "admin_consultations:0",
            }.get(target, "my_requests")
        ),
    )
    await callback.answer("Готово.")


@router.message(SupportResolutionStates.waiting_for_comment)
async def support_resolution_comment(message: Message, state: FSMContext, db: Database) -> None:
    comment = (message.text or "").strip()
    if not comment:
        await message.answer("Напишіть коментар або «-», якщо коментар не потрібен.")
        return

    data = await state.get_data()
    kind = data["resolution_kind"]
    item_id = int(data["item_id"])
    status = data["status"]
    resolution_comment = None if comment == "-" else comment

    if kind == "support_ticket":
        if not await is_active_admin(db, message.from_user.id):
            await state.clear()
            await message.answer("Недостатньо прав.")
            return
        updated = await db.update_support_status(
            item_id,
            status,
            actor_telegram_user_id=message.from_user.id,
            resolution_comment=resolution_comment,
        )
        target_keyboard = refresh_keyboard("support_queue")
    else:
        if not await is_active_admin(db, message.from_user.id):
            await state.clear()
            await message.answer("Недостатньо прав.")
            return
        updated = await db.update_support_status(
            item_id,
            status,
            actor_telegram_user_id=message.from_user.id,
            resolution_comment=resolution_comment,
        )
        target_keyboard = refresh_keyboard("admin")

    await state.clear()
    if not updated:
        await message.answer("Не вдалося оновити звернення. Можливо, статус уже змінився.")
        return

    lines = [
        f"Статус звернення #{item_id} змінено на: {status_uk(status)}.",
    ]
    if resolution_comment:
        lines.extend(["", "Коментар:", h(resolution_comment)])
    await message.answer("\n".join(lines), reply_markup=target_keyboard)


@router.callback_query(F.data.startswith("refresh:"))
async def refresh_list(callback: CallbackQuery, db: Database) -> None:
    parts = callback.data.split(":")
    target = parts[1]

    if target == "my_requests":
        if not await is_active_student(db, callback.from_user.id):
            await callback.answer("Спочатку увійдіть як студент.", show_alert=True)
            return
        consultations = await db.get_consultation_requests(callback.from_user.id)
        tickets = await db.get_support_tickets(callback.from_user.id)
        lines = [title("Ваші заявки")]
        if consultations:
            lines.append(section("Консультації"))
            for item in consultations:
                teacher = full_name(item)
                lines.append(
                    f"\n<b>#{item['id']}</b> | {status_uk(item['status'])}"
                    f" | {item['requested_date']:%Y-%m-%d}"
                    f" {item['starts_at']:%H:%M}-{item['ends_at']:%H:%M}"
                    f"\n{field('Викладач', teacher)}"
                    f"\n{field('Тема', item['topic'])}"
                )
        if tickets:
            lines.append(section("Техпідтримка"))
            for item in tickets:
                lines.append(
                    f"\n<b>#{item['id']}</b> | {status_uk(item['status'])} | {h(item['category'])}"
                    f"\n{h(item['message'])}"
                )
                if item.get("resolution_comment"):
                    lines.append(f"{field('Коментар', item['resolution_comment'])}")
        if not consultations and not tickets:
            lines.append("\nУ вас поки немає заявок.")
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=requests_keyboard(consultations, tickets),
        )
        await callback.answer("Оновлено.")
        return

    if target == "teacher_consultations":
        if not await is_active_teacher(db, callback.from_user.id):
            await callback.answer("Недостатньо прав.", show_alert=True)
            return
        consultations = await db.get_teacher_consultations(callback.from_user.id)
        lines = [title("Ваші консультації")]
        if consultations:
            for item in consultations:
                student = short_name(item["student_last_name"], item["student_first_name"])
                student_info = f"{student}, група {item['group_code']}"
                lines.append(
                    f"\n<b>#{item['id']}</b> | {status_uk(item['status'])}"
                    f" | {item['requested_date']:%Y-%m-%d}"
                    f" {item['starts_at']:%H:%M}-{item['ends_at']:%H:%M}"
                    f"\n{field('Студент', student_info)}"
                    f"\n{field('Тема', item['topic'])}"
                )
        else:
            lines.append("\nУ вас немає активних консультацій.")
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=teacher_consultations_keyboard(consultations),
        )
        await callback.answer("Оновлено.")
        return

    if target == "support_queue":
        if not await is_active_admin(db, callback.from_user.id):
            await callback.answer("Недостатньо прав.", show_alert=True)
            return
        tickets = await db.get_support_queue()
        lines = [title("Черга технічної підтримки")]
        if tickets:
            for item in tickets:
                student = short_name(item["student_last_name"], item["student_first_name"])
                lines.append(
                    f"\n<b>#{item['id']}</b> | {status_uk(item['status'])} | {h(item['category'])}"
                    f"\n{field('Студент', student)}"
                    f"\n{h(item['message'])}"
                )
        else:
            lines.append("\nНемає відкритих звернень у техпідтримку.")
        await callback.message.edit_text("\n".join(lines), reply_markup=support_queue_keyboard(tickets))
        await callback.answer("Оновлено.")
        return

    if target == "admin_consultations":
        if not await is_active_admin(db, callback.from_user.id):
            await callback.answer("Недостатньо прав.", show_alert=True)
            return
        page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        total_count = await db.count_admin_consultations()
        max_page = max(0, (total_count - 1) // ADMIN_CONSULTATIONS_PAGE_SIZE)
        page = min(page, max_page)
        consultations = await db.get_admin_consultations(
            limit=ADMIN_CONSULTATIONS_PAGE_SIZE,
            offset=page * ADMIN_CONSULTATIONS_PAGE_SIZE,
        )
        await callback.message.edit_text(
            admin_consultations_text(consultations, page, total_count, ADMIN_CONSULTATIONS_PAGE_SIZE),
            reply_markup=admin_consultations_keyboard(
                consultations,
                page,
                total_count,
                ADMIN_CONSULTATIONS_PAGE_SIZE,
            ),
        )
        await callback.answer("Оновлено.")
        return

    if target == "admin":
        if not await is_active_admin(db, callback.from_user.id):
            await callback.answer("Недостатньо прав.", show_alert=True)
            return
        consultations = await db.get_admin_consultations(limit=ADMIN_PANEL_CONSULTATIONS_LIMIT)
        tickets = await db.get_pending_support_tickets()
        lines = [title("Адмін-панель"), "Оберіть дію кнопкою під повідомленням."]
        lines.append(section("Останні консультації"))
        if consultations:
            for item in consultations:
                student = short_name(item["student_last_name"], item["student_first_name"])
                teacher = short_name(item["teacher_last_name"], item["teacher_first_name"])
                lines.append(
                    f"\n<b>#{item['id']}</b> | {status_uk(item['status'])} | {item['requested_date']:%Y-%m-%d}"
                    f" {item['starts_at']:%H:%M}-{item['ends_at']:%H:%M}"
                    f"\n{field('Студент', student)}"
                    f"\n{field('Викладач', teacher)}"
                    f"\n{field('Тема', item['topic'])}"
                )
        else:
            lines.append("\nКонсультацій поки немає.")
        lines.append(section("Техпідтримка"))
        if tickets:
            for item in tickets:
                student = short_name(item["student_last_name"], item["student_first_name"])
                lines.append(
                    f"\n<b>#{item['id']}</b> | {status_uk(item['status'])} | {h(item['category'])}"
                    f"\n{field('Студент', student)}"
                    f"\n{h(item['message'])}"
                )
        else:
            lines.append("\nНемає відкритих звернень.")
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=admin_requests_keyboard(consultations, tickets),
        )
        await callback.answer("Оновлено.")
        return

    await callback.answer("Невідомий список.", show_alert=True)


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Оберіть дію з меню або натисніть /start. Для скасування дії є команда /cancel.")
