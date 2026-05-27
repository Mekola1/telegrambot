# Telegram-бот коледжу

Telegram-бот для коледжу на Python 3.11, aiogram 3 і PostgreSQL. Бот дає студентам доступ до навчальної інформації, консультацій, технічної підтримки, FAQ, новин, оцінок і матеріалів. Для працівників є окремі інтерфейси викладача та адміністратора.

Проєкт побудований навколо трьох ролей:

- `student` - студентський кабінет;
- `teacher` - кабінет викладача;
- `admin` - адміністративна панель.

Один користувач може мати кілька ролей одночасно. Під час входу він обирає активну роль, а бот показує відповідне меню.

## Зміст

- [Можливості](#можливості)
- [Швидкий старт](#швидкий-старт)
- [Структура проєкту](#структура-проєкту)
- [Змінні середовища](#змінні-середовища)
- [Запуск і робота з базою](#запуск-і-робота-з-базою)
- [Команди бота](#команди-бота)
- [Загальна логіка роботи](#загальна-логіка-роботи)
- [Ролі та функціонал](#ролі-та-функціонал)
- [Авторизація](#авторизація)
- [Тестові користувачі](#тестові-користувачі)
- [Структура бази даних](#структура-бази-даних)
- [Зв'язки між таблицями](#звязки-між-таблицями)
- [UML / ER-діаграма](#uml--er-діаграма)
- [Основні бізнес-сценарії](#основні-бізнес-сценарії)
- [Міграції](#міграції)
- [Деплой як сервіс](#деплой-як-сервіс)
- [Корисні SQL-запити](#корисні-sql-запити)

## Можливості

Бот підтримує:

- вибір ролі при старті;
- авторизацію через безпечну кнопку Telegram `Поділитися телефоном`;
- прив'язку Telegram-акаунта до запису в `users`;
- відв'язку акаунта через `/logout` або кнопку `Вийти`;
- окремі меню для студента, викладача та адміністратора;
- перегляд студентського профілю;
- перегляд предметів студента;
- перегляд викладачів студента;
- перегляд розкладу;
- перегляд новин і оголошень;
- перегляд матеріалів, завдань і оцінок;
- FAQ за категоріями та пошук по ключових словах;
- запис студента на консультацію до доступного викладача;
- вибір вільної дати та тайм-слота консультації;
- захист консультаційного слота від подвійного бронювання;
- скасування студентом власних активних консультацій;
- створення звернення в технічну підтримку;
- скасування студентом власних активних звернень;
- перегляд власних заявок;
- перегляд викладачем власних консультацій;
- створення викладачем консультаційних слотів з Telegram;
- підтвердження, відхилення та завершення консультацій викладачем;
- адмін-панель з консультаціями та зверненнями;
- додавання акаунтів, студентів і викладачів адміністратором;
- зміна статусів заявок через inline-кнопки з підтвердженням;
- коментар адміністратора при закритті або вирішенні звернення;
- журнал зміни статусів;
- нагадування про заняття приблизно за 30 хвилин;
- нагадування про підтверджені консультації приблизно за 30 хвилин.

## Швидкий старт

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
cp .env.example .env
```

Заповніть `.env`, створіть PostgreSQL-базу і завантажте схему з тестовими даними:

```bash
python scripts/reset_db.py
```

Запуск бота:

```bash
python -m college_bot.main
```

На Windows команди активації venv можуть відрізнятися:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
python scripts\reset_db.py
python -m college_bot.main
```

## Структура проєкту

```text
.
├── db/
│   ├── init.sql
│   ├── seed.sql
│   └── migrations/
│       └── 20260521_interactive_workflows.sql
├── deploy/
│   └── college-bot.service.example
├── scripts/
│   └── reset_db.py
├── src/
│   └── college_bot/
│       ├── __init__.py
│       ├── config.py
│       ├── db.py
│       ├── handlers.py
│       ├── keyboards.py
│       ├── main.py
│       └── ui.py
├── README.md
└── pyproject.toml
```

Основні файли:

| Файл | Призначення |
| --- | --- |
| `src/college_bot/main.py` | Точка входу, створення `Bot`, `Dispatcher`, запуск polling і фонового циклу нагадувань. |
| `src/college_bot/handlers.py` | Всі Telegram-хендлери: авторизація, меню, студентські сценарії, викладач, адмін. |
| `src/college_bot/db.py` | Шар доступу до PostgreSQL: запити, створення сутностей, перевірка ролей, статуси. |
| `src/college_bot/keyboards.py` | Reply та inline-клавіатури. |
| `src/college_bot/ui.py` | Допоміжні функції для форматування повідомлень. |
| `src/college_bot/config.py` | Читання `BOT_TOKEN` і `DATABASE_URL`. |
| `db/init.sql` | Повна актуальна схема бази. |
| `db/seed.sql` | Тестові дані. |
| `scripts/reset_db.py` | Повністю перестворює базу: запускає `init.sql`, потім `seed.sql`. |
| `db/migrations/...sql` | Міграція для вже існуючої бази без повного reset. |

## Змінні середовища

Проєкт очікує `.env` або змінні середовища:

```env
BOT_TOKEN=123456:telegram-token
DATABASE_URL=postgresql://college_bot:college_bot_password@localhost:5432/college_bot
```

`BOT_TOKEN` - токен Telegram-бота з BotFather.

`DATABASE_URL` - повний рядок підключення до PostgreSQL.

Приклад для зовнішньої бази:

```env
DATABASE_URL=postgresql://user:password@host:5432/database_name
```

Для `scripts/reset_db.py` користувач бази повинен мати права на `DROP TABLE`, `CREATE TABLE`, `CREATE INDEX`, `INSERT`.

## Запуск і робота з базою

### Повне перестворення бази

```bash
python scripts/reset_db.py
```

Скрипт:

1. Читає `DATABASE_URL`.
2. Підключається через `asyncpg`.
3. Виконує `db/init.sql`.
4. Виконує `db/seed.sql`.
5. Закриває підключення.

Це зручний варіант для локальної розробки та навчального тестування.

### Оновлення існуючої бази без reset

Якщо база вже містить дані, не запускайте `reset_db.py`, бо він видаляє таблиці. Для оновлення структури використовуйте міграції:

```bash
psql "$DATABASE_URL" -f db/migrations/20260521_interactive_workflows.sql
```

На Windows можна виконати через pgAdmin Query Tool або через `psql`, якщо він є в PATH.

## Команди бота

| Команда | Що робить |
| --- | --- |
| `/start` | Початок роботи, показ поточного входу або вибір ролі. |
| `/login` | Повторно відкриває вибір ролі. |
| `/staff` | Вхід для викладача або адміністратора. |
| `/whoami` | Показує поточного користувача, активну роль і профілі. |
| `/logout` | Відв'язує Telegram ID від користувача і очищає активну роль. |
| `/help` | Показує можливості бота. |
| `/cancel` | Скасовує поточний FSM-сценарій. |

Кнопка `Вийти` працює як `/logout`.

## Загальна логіка роботи

У системі є один базовий акаунт людини в таблиці `users`. Цей акаунт містить:

- email;
- телефон;
- Telegram ID після входу;
- активну роль.

Ролі зберігаються окремо:

```text
users -> user_roles -> roles
```

Профілі теж зберігаються окремо:

```text
users -> students
users -> teachers
```

Це означає:

- один користувач може бути тільки студентом;
- може бути тільки викладачем;
- може бути тільки адміністратором;
- може мати кілька ролей одночасно;
- може мати студентський і викладацький профіль одночасно, якщо це потрібно для тестів.

Після входу бот записує в `users`:

- `telegram_user_id` - ID Telegram-акаунта;
- `active_role` - роль, яку користувач обрав на вході.

Саме `active_role` визначає, яке меню буде показано.

## Ролі та функціонал

### Студент

Активна роль: `student`.

Студентське меню містить:

- `Мій профіль`;
- `Новини`;
- `Мої предмети`;
- `Мої викладачі`;
- `Розклад`;
- `Інформація про коледж`;
- `Запис на консультацію`;
- `Технічна підтримка`;
- `Мої заявки`;
- `FAQ`;
- `Оцінки`;
- `Завдання`;
- `Матеріали`;
- `Нагадування`;
- `Вийти`.

Студент може бачити тільки власні дані. Всі студентські запити прив'язані до Telegram ID, а далі через `users` до `students`.

### Викладач

Активна роль: `teacher`.

Меню викладача містить:

- `Профіль працівника`;
- `Мої консультації викладача`;
- `Додати слот консультації`;
- `Інформація про коледж`;
- `FAQ`;
- `Вийти`.

Викладач може:

- переглядати консультації, записані саме до нього;
- підтверджувати консультацію;
- відхиляти консультацію;
- позначати консультацію виконаною;
- створювати нові слоти консультацій.

Для входу як викладач потрібні дві умови:

- користувач має роль `teacher` у `user_roles`;
- користувач має профіль у `teachers`.

### Адміністратор

Активна роль: `admin`.

Адмін-меню містить:

- `Профіль працівника`;
- `Адмін-панель`;
- `Додати акаунт`;
- `Додати студента`;
- `Додати викладача`;
- `Черга підтримки`;
- `Консультації`;
- `Інформація про коледж`;
- `FAQ`;
- `Вийти`.

Адміністратор може:

- переглядати останні консультації та звернення;
- переглядати всі консультації з пагінацією;
- змінювати статуси консультацій;
- обробляти чергу техпідтримки;
- додавати базові адмін-акаунти;
- додавати студентів;
- додавати викладачів.

Критичні дії виконуються через підтвердження inline-кнопками.

## Авторизація

Бот не приймає номер телефону текстом. Користувач має натиснути кнопку Telegram `Поділитися телефоном`. Так Telegram передає контакт саме поточного користувача.

Студентський вхід:

```text
/start -> Студент -> Поділитися телефоном
```

Вхід викладача:

```text
/start -> Викладач -> Поділитися телефоном
```

Або:

```text
/staff -> Викладач -> Поділитися телефоном
```

Вхід адміністратора:

```text
/start -> Адміністратор -> Поділитися телефоном
```

Після успішного входу:

```sql
UPDATE users
SET telegram_user_id = <telegram id>,
    active_role = <selected role>
WHERE phone = <shared phone>;
```

Фактично код нормалізує телефон через `regexp_replace(..., '[^0-9]', '', 'g')`, тому `+380...` і `380...` порівнюються як цифри.

Щоб зайти під іншою роллю або іншим тестовим користувачем, треба натиснути `/logout` або кнопку `Вийти`.

## Тестові користувачі

У `seed.sql` є звичайні тестові студенти та викладачі, а також три мульти-рольові користувачі для перевірки всіх ролей.

### Мульти-рольові користувачі

Кожен із цих номерів має ролі `student`, `teacher`, `admin`, а також записи в `students` і `teachers`.

| Телефон | Email | Ролі | Що можна тестувати |
| --- | --- | --- | --- |
| `+380958961586` | `test.student@college.local` | `student`, `teacher`, `admin` | всі меню й переходи між ролями |
| `+380667148290` | `test.teacher@college.local` | `student`, `teacher`, `admin` | всі меню й переходи між ролями |
| `+380635224298` | `test.admin@college.local` | `student`, `teacher`, `admin` | всі меню й переходи між ролями |

Для перемикання ролі:

```text
/logout -> /start -> обрати іншу роль -> Поділитися телефоном
```

### Студенти з seed

| Student ID | ПІБ | Телефон | Email |
| --- | --- | --- | --- |
| `1001` | Іван Петренко | `+380501111111` | `ivan.petrenko@student.college.local` |
| `1002` | Олена Коваль | `+380502222222` | `olena.koval@student.college.local` |
| `1003` | Андрій Шевченко | `+380503333333` | `andrii.shevchenko@student.college.local` |

### Викладачі з seed

| Teacher ID | ПІБ | Телефон | Email |
| --- | --- | --- | --- |
| `1` | Марія Бондар | `+380671234501` | `m.bondar@college.local` |
| `2` | Сергій Мельник | `+380671234502` | `s.melnyk@college.local` |
| `3` | Наталія Ткаченко | `+380671234503` | `n.tkachenko@college.local` |

## Структура бази даних

### Група користувачів і ролей

#### `users`

Базова таблиця акаунтів.

| Поле | Тип | Опис |
| --- | --- | --- |
| `id` | `BIGSERIAL PRIMARY KEY` | Внутрішній ID користувача. |
| `email` | `TEXT UNIQUE NOT NULL` | Email акаунта. |
| `phone` | `TEXT` | Телефон для авторизації через Telegram contact. |
| `telegram_user_id` | `BIGINT UNIQUE` | Telegram ID після входу. |
| `active_role` | `TEXT` | Поточна активна роль: `student`, `teacher`, `admin`. |
| `created_at` | `TIMESTAMPTZ` | Дата створення. |

Додатково є унікальний індекс `uq_users_normalized_phone`, який забороняє дублювати один номер у різних форматах.

#### `roles`

Довідник ролей.

| Поле | Опис |
| --- | --- |
| `id` | ID ролі. |
| `code` | Системний код: `student`, `teacher`, `admin`. |
| `name` | Людська назва ролі. |

#### `user_roles`

Зв'язок багато-до-багатьох між користувачами та ролями.

| Поле | Опис |
| --- | --- |
| `user_id` | Посилання на `users.id`. |
| `role_id` | Посилання на `roles.id`. |

Первинний ключ: `(user_id, role_id)`.

### Навчальна структура

#### `courses`

Курси та групи.

| Поле | Опис |
| --- | --- |
| `id` | ID курсу/групи. |
| `name` | Назва спеціальності або курсу. |
| `year_number` | Рік навчання. |
| `group_code` | Код групи, наприклад `КН-21`. |

#### `students`

Студентський профіль.

| Поле | Опис |
| --- | --- |
| `id` | Student ID. |
| `user_id` | Посилання на `users.id`, унікальне. |
| `first_name` | Ім'я. |
| `patronymic` | По батькові. |
| `last_name` | Прізвище. |
| `course_id` | Посилання на `courses.id`. |
| `lesson_reminders_enabled` | Чи увімкнені нагадування про заняття. |
| `created_at` | Дата створення профілю. |

#### `teachers`

Профіль викладача.

| Поле | Опис |
| --- | --- |
| `id` | Teacher ID. |
| `user_id` | Посилання на `users.id`, може бути `NULL`. |
| `first_name` | Ім'я. |
| `patronymic` | По батькові. |
| `last_name` | Прізвище. |
| `office` | Кабінет. |
| `consultation_notes` | Примітки щодо консультацій. |

#### `subjects`

Предмети.

| Поле | Опис |
| --- | --- |
| `id` | ID предмета. |
| `name` | Назва. |
| `description` | Опис. |
| `course_id` | Група/курс, до якого належить предмет. |

#### `student_subjects`

Які предмети доступні студенту.

| Поле | Опис |
| --- | --- |
| `student_id` | Посилання на `students.id`. |
| `subject_id` | Посилання на `subjects.id`. |

#### `subject_teachers`

Які викладачі ведуть предмети.

| Поле | Опис |
| --- | --- |
| `subject_id` | Посилання на `subjects.id`. |
| `teacher_id` | Посилання на `teachers.id`. |

#### `schedules`

Розклад занять.

| Поле | Опис |
| --- | --- |
| `subject_id` | Предмет. |
| `teacher_id` | Викладач. |
| `course_id` | Група/курс. |
| `weekday` | День тижня від 1 до 7. |
| `starts_at` | Початок пари. |
| `ends_at` | Кінець пари. |
| `room` | Аудиторія. |

### Контент і навчальні матеріали

#### `announcements`

Новини та оголошення.

`course_id` може бути `NULL`. Якщо `NULL`, оголошення бачать усі студенти. Якщо заданий конкретний курс, оголошення бачать тільки студенти цієї групи.

#### `faq_questions`

FAQ.

Містить категорію, питання, відповідь і ключові слова. Для пошуку використовується PostgreSQL full-text search через `to_tsvector('simple', ...)`.

#### `subject_resources`

Посилання та матеріали за предметами.

#### `assignments`

Завдання та дедлайни за предметами.

#### `grades`

Оцінки студентів за предметами.

### Консультації

#### `consultation_slots`

Вільні слоти консультацій, які створює викладач.

| Поле | Опис |
| --- | --- |
| `teacher_id` | Викладач. |
| `slot_date` | Дата консультації. |
| `starts_at` | Початок. |
| `ends_at` | Кінець. |
| `is_active` | Чи активний слот. |

Унікальність: один викладач не може мати два слоти з однаковими `teacher_id`, `slot_date`, `starts_at`.

#### `consultation_requests`

Заявки студентів на консультації.

| Поле | Опис |
| --- | --- |
| `student_id` | Студент. |
| `teacher_id` | Викладач. |
| `consultation_slot_id` | Обраний слот. |
| `requested_date` | Дата консультації, дублюється зі слота для історії. |
| `starts_at` | Початок, дублюється зі слота для історії. |
| `ends_at` | Кінець, дублюється зі слота для історії. |
| `topic` | Тема консультації. |
| `status` | `new`, `approved`, `rejected`, `done`, `cancelled`. |

Активно зайнятий слот - це заявка зі статусом `new` або `approved`. Це захищає partial unique index:

```sql
CREATE UNIQUE INDEX uq_active_consultation_slot
ON consultation_requests(consultation_slot_id)
WHERE status IN ('new', 'approved');
```

Якщо заявка `cancelled`, `rejected` або `done`, слот більше не блокується.

#### `consultation_reminder_logs`

Журнал уже надісланих нагадувань про консультації. Захищає від повторної відправки одного й того самого нагадування.

### Технічна підтримка

#### `support_categories`

Категорії звернень: доступ до систем, пошта, розклад, обладнання тощо.

#### `support_tickets`

Звернення студентів.

| Поле | Опис |
| --- | --- |
| `student_id` | Автор звернення. |
| `category_id` | Категорія. |
| `message` | Текст проблеми. |
| `status` | `new`, `in_progress`, `resolved`, `closed`, `cancelled`. |
| `resolution_comment` | Коментар адміністратора при вирішенні або закритті. |

### Журнали

#### `request_status_history`

Журнал зміни статусів консультацій і звернень.

| Поле | Опис |
| --- | --- |
| `entity_type` | `consultation` або `support`. |
| `entity_id` | ID заявки. |
| `old_status` | Попередній статус. |
| `new_status` | Новий статус. |
| `changed_by_user_id` | Користувач, який змінив статус. |
| `comment` | Коментар, якщо є. |

#### `lesson_reminder_logs`

Журнал надісланих нагадувань про заняття. Унікальність `(student_id, schedule_id, lesson_date)` не дає відправити одне нагадування двічі.

## Зв'язки між таблицями

Ключові зв'язки:

| Звідки | Куди | Тип | Значення |
| --- | --- | --- | --- |
| `users.id` | `students.user_id` | 1 до 0..1 | Користувач може мати студентський профіль. |
| `users.id` | `teachers.user_id` | 1 до 0..1 | Користувач може мати викладацький профіль. |
| `users.id` | `user_roles.user_id` | 1 до N | Користувач може мати багато ролей. |
| `roles.id` | `user_roles.role_id` | 1 до N | Роль може бути призначена багатьом користувачам. |
| `courses.id` | `students.course_id` | 1 до N | У групі багато студентів. |
| `courses.id` | `subjects.course_id` | 1 до N | Предмет належить курсу/групі. |
| `students.id` | `student_subjects.student_id` | 1 до N | Студент має багато предметів. |
| `subjects.id` | `student_subjects.subject_id` | 1 до N | Предмет доступний багатьом студентам. |
| `subjects.id` | `subject_teachers.subject_id` | 1 до N | Предмет можуть вести кілька викладачів. |
| `teachers.id` | `subject_teachers.teacher_id` | 1 до N | Викладач може вести кілька предметів. |
| `courses.id` | `schedules.course_id` | 1 до N | Розклад прив'язаний до групи. |
| `students.id` | `consultation_requests.student_id` | 1 до N | Студент може мати багато консультацій. |
| `teachers.id` | `consultation_slots.teacher_id` | 1 до N | Викладач створює багато слотів. |
| `consultation_slots.id` | `consultation_requests.consultation_slot_id` | 1 до N історично, 1 активна | Слот може мати багато історичних заявок, але тільки одну активну. |
| `students.id` | `support_tickets.student_id` | 1 до N | Студент може створити багато звернень. |
| `support_categories.id` | `support_tickets.category_id` | 1 до N | Категорія має багато звернень. |

## UML / ER-діаграма
```
erDiagram
    USERS {
        bigint id PK
        text email UK
        text phone
        bigint telegram_user_id UK
        text active_role
        timestamptz created_at
    }

    ROLES {
        bigint id PK
        text code UK
        text name
    }

    USER_ROLES {
        bigint user_id PK, FK
        bigint role_id PK, FK
    }

    COURSES {
        bigint id PK
        text name
        int year_number
        text group_code UK
    }

    STUDENTS {
        bigint id PK
        bigint user_id UK, FK
        text first_name
        text patronymic
        text last_name
        bigint course_id FK
        boolean lesson_reminders_enabled
        timestamptz created_at
    }

    TEACHERS {
        bigint id PK
        bigint user_id UK, FK
        text first_name
        text patronymic
        text last_name
        text office
        text consultation_notes
    }

    SUBJECTS {
        bigint id PK
        text name
        text description
        bigint course_id FK
    }

    STUDENT_SUBJECTS {
        bigint student_id PK, FK
        bigint subject_id PK, FK
    }

    SUBJECT_TEACHERS {
        bigint subject_id PK, FK
        bigint teacher_id PK, FK
    }

    SCHEDULES {
        bigint id PK
        bigint subject_id FK
        bigint teacher_id FK
        bigint course_id FK
        int weekday
        time starts_at
        time ends_at
        text room
    }

    FAQ_QUESTIONS {
        bigint id PK
        text category
        text question
        text answer
        text keywords
    }

    ANNOUNCEMENTS {
        bigint id PK
        text title
        text body
        bigint course_id FK
        timestamptz published_at
        boolean is_active
    }

    SUBJECT_RESOURCES {
        bigint id PK
        bigint subject_id FK
        text title
        text url
        text description
    }

    ASSIGNMENTS {
        bigint id PK
        bigint subject_id FK
        text title
        text description
        date due_date
    }

    GRADES {
        bigint id PK
        bigint student_id FK
        bigint subject_id FK
        numeric grade
        numeric max_grade
        text comment
        date graded_at
    }

    LESSON_REMINDER_LOGS {
        bigint id PK
        bigint student_id FK
        bigint schedule_id FK
        date lesson_date
        timestamptz sent_at
    }

    CONSULTATION_SLOTS {
        bigint id PK
        bigint teacher_id FK
        date slot_date
        time starts_at
        time ends_at
        boolean is_active
    }

    CONSULTATION_REQUESTS {
        bigint id PK
        bigint student_id FK
        bigint teacher_id FK
        bigint consultation_slot_id FK
        date requested_date
        time starts_at
        time ends_at
        text topic
        text status
        timestamptz created_at
    }

    CONSULTATION_REMINDER_LOGS {
        bigint id PK
        bigint request_id UK, FK
        timestamptz sent_at
    }

    SUPPORT_CATEGORIES {
        bigint id PK
        text name UK
        text description
        boolean is_active
    }

    SUPPORT_TICKETS {
        bigint id PK
        bigint student_id FK
        bigint category_id FK
        text message
        text status
        text resolution_comment
        timestamptz created_at
    }

    REQUEST_STATUS_HISTORY {
        bigint id PK
        text entity_type
        bigint entity_id
        text old_status
        text new_status
        bigint changed_by_user_id FK
        text comment
        timestamptz created_at
    }

    COLLEGE_INFO {
        bigint id PK
        text title
        text body
    }

    USERS ||--o{ USER_ROLES : has
    ROLES ||--o{ USER_ROLES : assigned
    USERS ||--o| STUDENTS : student_profile
    USERS ||--o| TEACHERS : teacher_profile
    COURSES ||--o{ STUDENTS : contains
    COURSES ||--o{ SUBJECTS : includes
    COURSES ||--o{ SCHEDULES : schedule_for
    COURSES ||--o{ ANNOUNCEMENTS : targeted_to
    STUDENTS ||--o{ STUDENT_SUBJECTS : studies
    SUBJECTS ||--o{ STUDENT_SUBJECTS : studied_by
    SUBJECTS ||--o{ SUBJECT_TEACHERS : taught_as
    TEACHERS ||--o{ SUBJECT_TEACHERS : teaches
    SUBJECTS ||--o{ SCHEDULES : scheduled
    TEACHERS ||--o{ SCHEDULES : teaches_in
    SUBJECTS ||--o{ SUBJECT_RESOURCES : has
    SUBJECTS ||--o{ ASSIGNMENTS : has
    SUBJECTS ||--o{ GRADES : graded_for
    STUDENTS ||--o{ GRADES : receives
    STUDENTS ||--o{ LESSON_REMINDER_LOGS : reminder_sent
    SCHEDULES ||--o{ LESSON_REMINDER_LOGS : reminder_for
    TEACHERS ||--o{ CONSULTATION_SLOTS : owns
    STUDENTS ||--o{ CONSULTATION_REQUESTS : creates
    TEACHERS ||--o{ CONSULTATION_REQUESTS : receives
    CONSULTATION_SLOTS ||--o{ CONSULTATION_REQUESTS : selected
    CONSULTATION_REQUESTS ||--o| CONSULTATION_REMINDER_LOGS : reminder
    SUPPORT_CATEGORIES ||--o{ SUPPORT_TICKETS : categorizes
    STUDENTS ||--o{ SUPPORT_TICKETS : opens
    USERS ||--o{ REQUEST_STATUS_HISTORY : changes
```


Діаграма логіки авторизації та вибору ролі:

```mermaid
flowchart TD
    A["/start або /login"] --> B["Показати вибір ролі"]
    B --> C{"Обрана роль"}
    C -->|student| D["Запросити Telegram contact"]
    C -->|teacher або admin| E["Запросити Telegram contact"]
    D --> F["Нормалізувати телефон"]
    E --> F
    F --> G["Знайти users.phone"]
    G --> H{"Користувач знайдений?"}
    H -->|ні| I["Показати помилку входу"]
    H -->|так| J{"Є потрібна роль?"}
    J -->|ні| I
    J -->|так| K{"Для student є students? Для teacher є teachers?"}
    K -->|ні| I
    K -->|так| L["Записати telegram_user_id і active_role"]
    L --> M{"active_role"}
    M -->|student| N["Показати студентське меню"]
    M -->|teacher| O["Показати меню викладача"]
    M -->|admin| P["Показати адмін-меню"]
```

## Основні бізнес-сценарії

### Перегляд студентських даних

1. Студент входить як `student`.
2. Бот знаходить `users` за Telegram ID.
3. Через `students.user_id` знаходить студентський профіль.
4. Через `course_id`, `student_subjects`, `subjects`, `schedules`, `grades` та інші таблиці показує потрібні дані.

### Запис на консультацію

```text
Запис на консультацію
-> вибір викладача
-> вибір дати
-> вибір вільного слота
-> введення теми
-> створення consultation_requests
```

Бот показує студенту тільки тих викладачів, які пов'язані з його предметами:

```text
students -> student_subjects -> subjects -> subject_teachers -> teachers
```

Вільні слоти беруться з `consultation_slots`, але відфільтровуються від уже зайнятих активними заявками.

### Обробка консультації викладачем

1. Викладач входить як `teacher`.
2. Бот знаходить `teachers` через `users.telegram_user_id`.
3. Показує консультації зі статусом `new` або `approved`.
4. Викладач може змінити статус на `approved`, `rejected` або `done`.
5. Зміна записується в `request_status_history`.

### Технічна підтримка

Студент:

```text
Технічна підтримка
-> вибір категорії
-> опис проблеми
-> створення support_tickets
```

Адміністратор:

```text
Черга підтримки
-> взяти в роботу / вирішено / закрити / скасувати
-> за потреби додати коментар
-> оновити support_tickets
-> записати request_status_history
```

### Нагадування

У `main.py` запускається фоновий цикл `send_lesson_reminders`.

Кожну хвилину він:

1. Шукає заняття, які почнуться приблизно через 30 хвилин.
2. Відправляє студентам нагадування.
3. Записує факт відправки в `lesson_reminder_logs`.
4. Шукає підтверджені консультації приблизно через 30 хвилин.
5. Відправляє нагадування студенту і викладачу.
6. Записує факт відправки в `consultation_reminder_logs`.

## Міграції

Актуальна міграція:

```text
db/migrations/20260521_interactive_workflows.sql
```

Вона:

- додає `support_tickets.resolution_comment`;
- створює `request_status_history`;
- створює `consultation_reminder_logs`;
- прибирає старий звичайний unique constraint на `consultation_slot_id`, якщо він існує;
- створює partial unique index `uq_active_consultation_slot`;
- створює unique index `uq_users_normalized_phone`;
- створює індекс для історії статусів.

Запуск:

```bash
psql "$DATABASE_URL" -f db/migrations/20260521_interactive_workflows.sql
```

Важливо: якщо у live-БД уже є дублікати телефонів, створення `uq_users_normalized_phone` впаде. Спочатку треба знайти дублікати:

```sql
SELECT
    regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g') AS normalized_phone,
    count(*) AS users_count,
    string_agg(email, ', ' ORDER BY email) AS emails
FROM users
WHERE phone IS NOT NULL
GROUP BY normalized_phone
HAVING count(*) > 1;
```

## Деплой як сервіс

У репозиторії є шаблон:

```text
deploy/college-bot.service.example
```

Приклад встановлення на Linux:

```bash
sudo cp deploy/college-bot.service.example /etc/systemd/system/college-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now college-bot
sudo systemctl status college-bot
```

Перед цим у service-файлі треба перевірити:

- шлях до проєкту;
- користувача Linux;
- шлях до Python/venv;
- наявність `.env` або environment-змінних.

## Корисні SQL-запити

### Подивитися користувачів і ролі

```sql
SELECT
    u.id AS user_id,
    u.email,
    u.phone,
    u.telegram_user_id,
    u.active_role,
    string_agg(r.code, ', ' ORDER BY r.code) AS roles
FROM users u
LEFT JOIN user_roles ur ON ur.user_id = u.id
LEFT JOIN roles r ON r.id = ur.role_id
GROUP BY u.id, u.email, u.phone, u.telegram_user_id, u.active_role
ORDER BY u.id;
```

### Відв'язати Telegram від користувача

```sql
UPDATE users
SET telegram_user_id = NULL,
    active_role = NULL
WHERE phone = '+380958961586';
```

### Додати роль користувачу

```sql
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
CROSS JOIN roles r
WHERE u.email = 'test.student@college.local'
  AND r.code = 'admin'
ON CONFLICT DO NOTHING;
```

### Видалити роль користувача

```sql
DELETE FROM user_roles
WHERE user_id = (SELECT id FROM users WHERE email = 'test.student@college.local')
  AND role_id = (SELECT id FROM roles WHERE code = 'admin');
```

### Перевірити активні консультації

```sql
SELECT
    cr.id,
    cr.status,
    cr.requested_date,
    cr.starts_at,
    cr.ends_at,
    s.last_name AS student_last_name,
    t.last_name AS teacher_last_name,
    cr.topic
FROM consultation_requests cr
JOIN students s ON s.id = cr.student_id
JOIN teachers t ON t.id = cr.teacher_id
ORDER BY cr.requested_date DESC, cr.starts_at DESC;
```

### Перевірити звернення в підтримку

```sql
SELECT
    st.id,
    st.status,
    sc.name AS category,
    s.last_name AS student_last_name,
    st.message,
    st.resolution_comment,
    st.created_at
FROM support_tickets st
JOIN support_categories sc ON sc.id = st.category_id
JOIN students s ON s.id = st.student_id
ORDER BY st.created_at DESC;
```

### Подивитися історію статусів

```sql
SELECT
    rsh.entity_type,
    rsh.entity_id,
    rsh.old_status,
    rsh.new_status,
    u.email AS changed_by,
    rsh.comment,
    rsh.created_at
FROM request_status_history rsh
LEFT JOIN users u ON u.id = rsh.changed_by_user_id
ORDER BY rsh.created_at DESC;
```

## Обмеження та важливі правила

- Один номер телефону може належати тільки одному запису `users`.
- Один Telegram ID може бути прив'язаний тільки до одного запису `users`.
- Для входу студентом потрібен запис у `students`.
- Для входу викладачем потрібен запис у `teachers`.
- Для входу адміністратором достатньо ролі `admin`.
- Активна роль зберігається в `users.active_role`.
- Щоб змінити роль, потрібно вийти через `/logout` або `Вийти` і зайти знову.
- Студент бачить тільки свої дані.
- Викладач бачить тільки свої консультації.
- Адміністратор бачить загальні черги та може змінювати статуси.
