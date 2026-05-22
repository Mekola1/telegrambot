from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


ROLE_SELECTION_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Студент", callback_data="auth_role:student"),
            InlineKeyboardButton(text="Викладач", callback_data="auth_role:teacher"),
        ],
        [
            InlineKeyboardButton(text="Адміністратор", callback_data="auth_role:admin"),
        ],
    ]
)


STAFF_ROLE_SELECTION_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Викладач", callback_data="auth_role:teacher"),
            InlineKeyboardButton(text="Адміністратор", callback_data="auth_role:admin"),
        ],
    ]
)


CONTACT_REQUEST_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Поділитися телефоном", request_contact=True)],
        [KeyboardButton(text="Вийти")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Натисніть кнопку для безпечного входу",
)


MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Мій профіль"),
            KeyboardButton(text="Новини"),
        ],
        [
            KeyboardButton(text="Мої предмети"),
            KeyboardButton(text="Мої викладачі"),
        ],
        [
            KeyboardButton(text="Розклад"),
            KeyboardButton(text="Інформація про коледж"),
        ],
        [
            KeyboardButton(text="Запис на консультацію"),
            KeyboardButton(text="Технічна підтримка"),
        ],
        [
            KeyboardButton(text="Мої заявки"),
            KeyboardButton(text="FAQ"),
        ],
        [
            KeyboardButton(text="Оцінки"),
            KeyboardButton(text="Завдання"),
        ],
        [
            KeyboardButton(text="Матеріали"),
            KeyboardButton(text="Нагадування"),
        ],
        [
            KeyboardButton(text="Вийти"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Оберіть дію з меню",
    is_persistent=True,
)


STAFF_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Профіль працівника"),
            KeyboardButton(text="Мої консультації викладача"),
        ],
        [
            KeyboardButton(text="Додати слот консультації"),
        ],
        [
            KeyboardButton(text="Інформація про коледж"),
            KeyboardButton(text="FAQ"),
        ],
        [
            KeyboardButton(text="Вийти"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Оберіть дію працівника",
    is_persistent=True,
)


ADMIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Профіль працівника"),
            KeyboardButton(text="Адмін-панель"),
        ],
        [
            KeyboardButton(text="Додати акаунт"),
            KeyboardButton(text="Додати студента"),
        ],
        [
            KeyboardButton(text="Додати викладача"),
            KeyboardButton(text="Черга підтримки"),
        ],
        [
            KeyboardButton(text="Консультації"),
        ],
        [
            KeyboardButton(text="Інформація про коледж"),
            KeyboardButton(text="FAQ"),
        ],
        [
            KeyboardButton(text="Вийти"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Оберіть дію адміністратора",
    is_persistent=True,
)


def admin_account_role_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Адміністратор", callback_data="admin_new_account_role:admin"),
            ],
        ]
    )


def courses_keyboard(courses: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{course['group_code']} - {course['name']}",
                    callback_data=f"admin_student_course:{course['id']}",
                )
            ]
            for course in courses
        ]
    )


def teachers_keyboard(teachers: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for teacher in teachers:
        name = " ".join(
            part
            for part in [teacher.get("last_name"), teacher.get("first_name"), teacher.get("patronymic")]
            if part
        )
        buttons.append(
            [InlineKeyboardButton(text=name, callback_data=f"consult_teacher:{teacher['id']}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def consultation_dates_keyboard(teacher_id: int, dates: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for item in dates:
        slot_date: date = item["slot_date"]
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{slot_date:%d.%m.%Y} ({item['slots_count']} слот.)",
                    callback_data=f"consult_date:{teacher_id}:{slot_date:%Y-%m-%d}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def consultation_slots_keyboard(slots: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for slot in slots:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{slot['starts_at']:%H:%M}-{slot['ends_at']:%H:%M}",
                    callback_data=f"consult_slot:{slot['id']}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def support_categories_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=category["name"], callback_data=f"support_category:{category['id']}")]
            for category in categories
        ]
    )


def faq_categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=category, callback_data=f"faq_category:{category}")]
        for category in categories
    ]
    buttons.append([InlineKeyboardButton(text="Пошук за словом", callback_data="faq_search")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_action_keyboard(kind: str, item_id: int, status: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Так, підтвердити",
                    callback_data=f"confirm:{kind}:{item_id}:{status}",
                )
            ],
            [InlineKeyboardButton(text="Ні, скасувати", callback_data="confirm_cancel")],
        ]
    )


def refresh_keyboard(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оновити список", callback_data=f"refresh:{target}")]
        ]
    )


def requests_keyboard(consultations: list[dict], tickets: list[dict]) -> InlineKeyboardMarkup | None:
    buttons = [[InlineKeyboardButton(text="Оновити список", callback_data="refresh:my_requests")]]
    for item in consultations:
        if item["status"] in {"new", "approved"}:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"Скасувати консультацію #{item['id']}",
                        callback_data=f"cancel_consultation:{item['id']}",
                    )
                ]
            )

    for item in tickets:
        if item["status"] in {"new", "in_progress"}:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"Скасувати звернення #{item['id']}",
                        callback_data=f"cancel_support:{item['id']}",
                    )
                ]
            )

    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=buttons)


ADMIN_CONSULTATION_ACTIONS = [
    ("new", "Повернути в нові"),
    ("approved", "Підтвердити"),
    ("rejected", "Відхилити"),
    ("done", "Виконано"),
    ("cancelled", "Скасувати"),
]


def add_admin_consultation_buttons(buttons: list[list[InlineKeyboardButton]], consultations: list[dict]) -> None:
    for item in consultations:
        item_buttons = [
            InlineKeyboardButton(
                text=f"{label} #{item['id']}",
                callback_data=f"admin_consultation:{item['id']}:{status}",
            )
            for status, label in ADMIN_CONSULTATION_ACTIONS
            if status != item["status"]
        ]
        for index in range(0, len(item_buttons), 2):
            buttons.append(item_buttons[index : index + 2])


def admin_consultations_keyboard(
    consultations: list[dict],
    page: int,
    total_count: int,
    page_size: int,
) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="Оновити список", callback_data=f"refresh:admin_consultations:{page}")]]
    add_admin_consultation_buttons(buttons, consultations)
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="Назад", callback_data=f"refresh:admin_consultations:{page - 1}"))
    if (page + 1) * page_size < total_count:
        nav_buttons.append(InlineKeyboardButton(text="Далі", callback_data=f"refresh:admin_consultations:{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_requests_keyboard(consultations: list[dict], tickets: list[dict]) -> InlineKeyboardMarkup | None:
    buttons = [[InlineKeyboardButton(text="Оновити список", callback_data="refresh:admin")]]
    add_admin_consultation_buttons(buttons, consultations)

    for item in tickets:
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text=f"Взяти в роботу звернення #{item['id']}",
                        callback_data=f"admin_support:{item['id']}:in_progress",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"Вирішено #{item['id']}",
                        callback_data=f"admin_support:{item['id']}:resolved",
                    ),
                    InlineKeyboardButton(
                        text=f"Закрити #{item['id']}",
                        callback_data=f"admin_support:{item['id']}:closed",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=f"Скасувати звернення #{item['id']}",
                        callback_data=f"admin_support:{item['id']}:cancelled",
                    )
                ],
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def teacher_consultations_keyboard(consultations: list[dict]) -> InlineKeyboardMarkup | None:
    buttons = [[InlineKeyboardButton(text="Оновити список", callback_data="refresh:teacher_consultations")]]
    for item in consultations:
        if item["status"] in {"new", "approved"}:
            buttons.extend(
                [
                    [
                        InlineKeyboardButton(
                            text=f"Підтвердити #{item['id']}",
                            callback_data=f"teacher_consultation:{item['id']}:approved",
                        ),
                        InlineKeyboardButton(
                            text=f"Виконано #{item['id']}",
                            callback_data=f"teacher_consultation:{item['id']}:done",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"Відхилити #{item['id']}",
                            callback_data=f"teacher_consultation:{item['id']}:rejected",
                        ),
                    ],
                ]
            )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def support_queue_keyboard(tickets: list[dict]) -> InlineKeyboardMarkup | None:
    buttons = [[InlineKeyboardButton(text="Оновити список", callback_data="refresh:support_queue")]]
    for item in tickets:
        if item["status"] in {"new", "in_progress"}:
            buttons.extend(
                [
                    [
                        InlineKeyboardButton(
                            text=f"Взяти в роботу #{item['id']}",
                            callback_data=f"support_ticket:{item['id']}:in_progress",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"Вирішено #{item['id']}",
                            callback_data=f"support_ticket:{item['id']}:resolved",
                        ),
                        InlineKeyboardButton(
                            text=f"Закрити #{item['id']}",
                            callback_data=f"support_ticket:{item['id']}:closed",
                        ),
                    ],
                ]
            )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
