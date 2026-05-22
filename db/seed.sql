BEGIN;

INSERT INTO courses (id, name, year_number, group_code) VALUES
    (1, 'Компʼютерні науки', 2, 'КН-21'),
    (2, 'Інженерія програмного забезпечення', 1, 'ІПЗ-11');

INSERT INTO users (id, email, phone) VALUES
    (1, 'ivan.petrenko@student.college.local', '+380501111111'),
    (2, 'olena.koval@student.college.local', '+380502222222'),
    (3, 'andrii.shevchenko@student.college.local', '+380503333333'),
    (4, 'm.bondar@college.local', '+380671234501'),
    (5, 's.melnyk@college.local', '+380671234502'),
    (6, 'n.tkachenko@college.local', '+380671234503'),
    (7, 'test.student@college.local', '+380958961586'),
    (8, 'test.teacher@college.local', '+380667148290'),
    (9, 'test.admin@college.local', '+380635224298');

INSERT INTO roles (id, code, name) VALUES
    (1, 'student', 'Студент'),
    (2, 'teacher', 'Викладач'),
    (3, 'admin', 'Адміністратор');

INSERT INTO user_roles (user_id, role_id) VALUES
    (1, 1), (1, 3),
    (2, 1),
    (3, 1),
    (4, 2),
    (5, 2),
    (6, 2),
    (7, 1), (7, 2), (7, 3),
    (8, 1), (8, 2), (8, 3),
    (9, 1), (9, 2), (9, 3);

INSERT INTO students (id, user_id, first_name, patronymic, last_name, course_id) VALUES
    (1001, 1, 'Іван', 'Петрович', 'Петренко', 1),
    (1002, 2, 'Олена', 'Ігорівна', 'Коваль', 1),
    (1003, 3, 'Андрій', 'Миколайович', 'Шевченко', 2),
    (1004, 7, 'Test', NULL, 'User One', 1),
    (1005, 8, 'Test', NULL, 'User Two', 1),
    (1006, 9, 'Test', NULL, 'User Three', 2);

INSERT INTO teachers (id, user_id, first_name, patronymic, last_name, office, consultation_notes) VALUES
    (1, 4, 'Марія', 'Олександрівна', 'Бондар', '302', 'Консультації щовівторка 15:00-16:00'),
    (2, 5, 'Сергій', 'Вікторович', 'Мельник', '214', 'Консультації щочетверга 14:00-15:00'),
    (3, 6, 'Наталія', 'Андріївна', 'Ткаченко', '118', 'Консультації щосереди 13:00-14:00'),
    (4, 7, 'Test', NULL, 'User One', '101', 'Test consultation notes'),
    (5, 8, 'Test', NULL, 'User Two', '102', 'Test consultation notes'),
    (6, 9, 'Test', NULL, 'User Three', '103', 'Test consultation notes');

INSERT INTO subjects (id, name, description, course_id) VALUES
    (1, 'Бази даних', 'Проєктування реляційних БД, SQL, PostgreSQL.', 1),
    (2, 'Обʼєктно-орієнтоване програмування', 'Класи, обʼєкти, наслідування та патерни.', 1),
    (3, 'Компʼютерні мережі', 'Основи мереж, TCP/IP, адресація та маршрутизація.', 1),
    (4, 'Алгоритми та структури даних', 'Базові алгоритми, складність, списки, дерева, графи.', 2),
    (5, 'Вступ до програмування Python', 'Синтаксис Python, функції, модулі та робота з файлами.', 2);

INSERT INTO student_subjects (student_id, subject_id) VALUES
    (1001, 1), (1001, 2), (1001, 3),
    (1002, 1), (1002, 2), (1002, 3),
    (1003, 4), (1003, 5),
    (1004, 1), (1004, 2), (1004, 3),
    (1005, 1), (1005, 2), (1005, 3),
    (1006, 4), (1006, 5);

INSERT INTO subject_teachers (subject_id, teacher_id) VALUES
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 2),
    (5, 1),
    (1, 4),
    (2, 5),
    (5, 6);

INSERT INTO schedules (subject_id, teacher_id, course_id, weekday, starts_at, ends_at, room) VALUES
    (1, 1, 1, 1, '09:00', '10:20', '305'),
    (2, 2, 1, 2, '10:40', '12:00', '210'),
    (3, 3, 1, 4, '12:20', '13:40', '119'),
    (4, 2, 2, 1, '10:40', '12:00', '212'),
    (5, 1, 2, 3, '09:00', '10:20', '306');

INSERT INTO college_info (title, body) VALUES
    ('Адреса', 'Коледж інформаційних технологій, вул. Освітня, 10, м. Київ.'),
    ('Приймальня', 'Працює з понеділка по пʼятницю з 09:00 до 17:00. Телефон: +380441234567.'),
    ('Бібліотека', 'Бібліотека працює у будні з 08:30 до 16:30, аудиторія 101.'),
    ('Технічна підтримка', 'Звернення щодо доступу до електронних сервісів можна створити прямо в боті.');

INSERT INTO faq_questions (category, question, answer, keywords) VALUES
    ('Документи', 'Як отримати довідку про навчання?', 'Зверніться до навчальної частини або залиште запит у деканаті. Довідка готується 1-2 робочі дні.', 'довідка документи навчання'),
    ('Стипендія', 'Коли виплачують стипендію?', 'Стипендія зазвичай нараховується щомісяця після затвердження відомостей бухгалтерією.', 'стипендія виплати гроші'),
    ('Гуртожиток', 'Як подати заяву на гуртожиток?', 'Потрібно звернутися до соціального педагога з паспортом, студентським квитком і заявою.', 'гуртожиток поселення кімната'),
    ('Електронні сервіси', 'Що робити, якщо не працює пошта?', 'Створіть звернення в технічну підтримку через бот і вкажіть вашу пошту та текст помилки.', 'пошта пароль доступ техпідтримка');

INSERT INTO announcements (title, body, course_id, published_at) VALUES
    ('Зміни у розкладі', 'У четвер друга пара для групи КН-21 відбудеться в аудиторії 307.', 1, '2026-05-20 09:00:00+03'),
    ('День відкритих дверей', 'У суботу відбудеться день відкритих дверей коледжу. Запрошуються всі охочі.', NULL, '2026-05-19 10:00:00+03'),
    ('Консультація перед модулем', 'Для групи ІПЗ-11 додана консультація з Python перед модульною роботою.', 2, '2026-05-18 12:00:00+03');

INSERT INTO subject_resources (subject_id, title, url, description) VALUES
    (1, 'Документація PostgreSQL', 'https://www.postgresql.org/docs/', 'Офіційна документація PostgreSQL.'),
    (2, 'Матеріали з ООП', 'https://example.edu/oop', 'Конспекти лекцій та приклади коду.'),
    (5, 'Python Tutorial', 'https://docs.python.org/3/tutorial/', 'Офіційний посібник з Python.');

INSERT INTO assignments (subject_id, title, description, due_date) VALUES
    (1, 'ER-діаграма бази даних', 'Побудувати ER-діаграму інформаційної системи коледжу.', '2026-05-28'),
    (2, 'Класи та наслідування', 'Реалізувати приклад ієрархії класів для предметної області.', '2026-05-30'),
    (5, 'Telegram-бот на Python', 'Створити простого бота з командами /start і /help.', '2026-06-02');

INSERT INTO grades (student_id, subject_id, grade, max_grade, comment, graded_at) VALUES
    (1001, 1, 88, 100, 'Лабораторні здано вчасно', '2026-05-15'),
    (1001, 2, 92, 100, 'Добра робота з класами', '2026-05-16'),
    (1002, 1, 81, 100, 'Потрібно допрацювати нормалізацію', '2026-05-15'),
    (1003, 5, 95, 100, 'Відмінне розуміння базового синтаксису', '2026-05-17');

INSERT INTO consultation_slots (teacher_id, slot_date, starts_at, ends_at) VALUES
    (1, '2026-05-25', '14:00', '14:20'),
    (1, '2026-05-25', '14:30', '14:50'),
    (1, '2026-05-27', '15:00', '15:20'),
    (2, '2026-05-26', '13:00', '13:20'),
    (2, '2026-05-26', '13:30', '13:50'),
    (2, '2026-05-28', '14:00', '14:20'),
    (3, '2026-05-27', '12:00', '12:20'),
    (3, '2026-05-29', '12:30', '12:50');

INSERT INTO support_categories (name, description) VALUES
    ('Доступ до систем', 'Проблеми з логіном, паролем, електронним кабінетом або Moodle.'),
    ('Пошта', 'Проблеми зі студентською поштою або відновленням доступу.'),
    ('Розклад', 'Помилка або неточність у розкладі занять.'),
    ('Обладнання', 'Проблеми з компʼютером, проєктором, інтернетом або аудиторією.'),
    ('Інше', 'Питання, яке не підходить до інших категорій.');

SELECT setval('courses_id_seq', (SELECT max(id) FROM courses));
SELECT setval('users_id_seq', (SELECT max(id) FROM users));
SELECT setval('roles_id_seq', (SELECT max(id) FROM roles));
SELECT setval('teachers_id_seq', (SELECT max(id) FROM teachers));
SELECT setval('subjects_id_seq', (SELECT max(id) FROM subjects));
SELECT setval('faq_questions_id_seq', (SELECT max(id) FROM faq_questions));
SELECT setval('announcements_id_seq', (SELECT max(id) FROM announcements));
SELECT setval('subject_resources_id_seq', (SELECT max(id) FROM subject_resources));
SELECT setval('assignments_id_seq', (SELECT max(id) FROM assignments));
SELECT setval('grades_id_seq', (SELECT max(id) FROM grades));
SELECT setval('consultation_slots_id_seq', (SELECT max(id) FROM consultation_slots));
SELECT setval('support_categories_id_seq', (SELECT max(id) FROM support_categories));

COMMIT;
