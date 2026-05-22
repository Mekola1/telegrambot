from __future__ import annotations

from datetime import date, time
from typing import Any

import asyncpg


WEEKDAYS = {
    1: "Понеділок",
    2: "Вівторок",
    3: "Середа",
    4: "Четвер",
    5: "Пʼятниця",
    6: "Субота",
    7: "Неділя",
}


class Database:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(dsn=self._database_url, min_size=1, max_size=10)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    @property
    def pool(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("Database pool is not initialized")
        return self._pool

    async def verify_student_phone_login(
        self,
        phone: str,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        query = """
            UPDATE users u
            SET telegram_user_id = $2,
                active_role = 'student'
            FROM students s
            WHERE s.user_id = u.id
              AND regexp_replace(COALESCE(u.phone, ''), '[^0-9]', '', 'g')
                  = regexp_replace($1, '[^0-9]', '', 'g')
              AND (u.telegram_user_id IS NULL OR u.telegram_user_id = $2)
            RETURNING s.id, s.first_name, s.patronymic, s.last_name, u.email
        """
        try:
            row = await self.pool.fetchrow(query, phone.strip(), telegram_user_id)
        except asyncpg.UniqueViolationError:
            return None
        return dict(row) if row else None

    async def get_student_by_telegram(self, telegram_user_id: int) -> dict[str, Any] | None:
        query = """
            SELECT
                s.id,
                s.first_name,
                s.patronymic,
                s.last_name,
                u.email,
                u.phone,
                COALESCE(string_agg(r.code, ', ' ORDER BY r.code), '') AS roles,
                c.name AS course_name,
                c.year_number,
                c.group_code
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN courses c ON c.id = s.course_id
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON r.id = ur.role_id
            WHERE u.telegram_user_id = $1
            GROUP BY s.id, s.first_name, s.patronymic, s.last_name,
                     u.email, u.phone, c.name, c.year_number, c.group_code
        """
        row = await self.pool.fetchrow(query, telegram_user_id)
        return dict(row) if row else None

    async def verify_staff_phone_login(
        self,
        phone: str,
        telegram_user_id: int,
        role: str,
    ) -> dict[str, Any] | None:
        query = """
            UPDATE users u
            SET telegram_user_id = $2,
                active_role = $3
            WHERE regexp_replace(COALESCE(u.phone, ''), '[^0-9]', '', 'g')
                  = regexp_replace($1, '[^0-9]', '', 'g')
              AND (u.telegram_user_id IS NULL OR u.telegram_user_id = $2)
              AND EXISTS (
                  SELECT 1
                  FROM user_roles ur
                  JOIN roles r ON r.id = ur.role_id
                  WHERE ur.user_id = u.id AND r.code = $3
              )
              AND (
                  $3 <> 'teacher'
                  OR EXISTS (
                      SELECT 1
                      FROM teachers t
                      WHERE t.user_id = u.id
                  )
              )
            RETURNING u.id, u.email, u.phone
        """
        try:
            row = await self.pool.fetchrow(query, phone.strip(), telegram_user_id, role)
        except asyncpg.UniqueViolationError:
            return None
        if not row:
            return None
        return await self.get_user_by_telegram(telegram_user_id)

    async def get_user_by_telegram(self, telegram_user_id: int) -> dict[str, Any] | None:
        query = """
            SELECT
                u.id,
                u.email,
                u.phone,
                u.active_role,
                COALESCE(string_agg(r.code, ', ' ORDER BY r.code), '') AS roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON r.id = ur.role_id
            WHERE u.telegram_user_id = $1
            GROUP BY u.id, u.email, u.phone, u.active_role
        """
        row = await self.pool.fetchrow(query, telegram_user_id)
        return dict(row) if row else None

    async def has_role(self, telegram_user_id: int, role: str) -> bool:
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM users u
                JOIN user_roles ur ON ur.user_id = u.id
                JOIN roles r ON r.id = ur.role_id
                WHERE u.telegram_user_id = $1 AND r.code = $2
            )
        """
        return await self.pool.fetchval(query, telegram_user_id, role)

    async def get_active_role(self, telegram_user_id: int) -> str | None:
        return await self.pool.fetchval(
            "SELECT active_role FROM users WHERE telegram_user_id = $1",
            telegram_user_id,
        )

    async def is_active_role(self, telegram_user_id: int, role: str) -> bool:
        active_role = await self.get_active_role(telegram_user_id)
        return active_role == role

    async def logout_user(self, telegram_user_id: int) -> bool:
        query = """
            UPDATE users
            SET telegram_user_id = NULL,
                active_role = NULL
            WHERE telegram_user_id = $1
        """
        result = await self.pool.execute(query, telegram_user_id)
        return result == "UPDATE 1"

    async def get_user_id_by_telegram(self, telegram_user_id: int) -> int | None:
        return await self.pool.fetchval(
            "SELECT id FROM users WHERE telegram_user_id = $1",
            telegram_user_id,
        )

    async def get_teacher_profile_by_telegram(self, telegram_user_id: int) -> dict[str, Any] | None:
        query = """
            SELECT
                t.id,
                t.first_name,
                t.patronymic,
                t.last_name,
                t.office,
                t.consultation_notes
            FROM teachers t
            JOIN users u ON u.id = t.user_id
            WHERE u.telegram_user_id = $1
        """
        row = await self.pool.fetchrow(query, telegram_user_id)
        return dict(row) if row else None

    async def get_courses(self) -> list[dict[str, Any]]:
        query = """
            SELECT id, name, year_number, group_code
            FROM courses
            ORDER BY year_number, group_code
        """
        return [dict(row) for row in await self.pool.fetch(query)]

    async def create_user_account(
        self,
        email: str,
        phone: str,
        role: str,
    ) -> int | None:
        if role != "admin":
            return None
        try:
            async with self.pool.acquire() as connection:
                async with connection.transaction():
                    user_id = await connection.fetchval(
                        """
                        INSERT INTO users (email, phone)
                        VALUES ($1, $2)
                        ON CONFLICT (email) DO UPDATE
                        SET phone = EXCLUDED.phone
                        RETURNING id
                        """,
                        email.strip(),
                        phone.strip(),
                    )
                    role_id = await connection.fetchval("SELECT id FROM roles WHERE code = $1", role)
                    if not role_id:
                        return None
                    await connection.execute(
                        """
                        INSERT INTO user_roles (user_id, role_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                        """,
                        user_id,
                        role_id,
                    )
                    return user_id
        except asyncpg.UniqueViolationError:
            return None

    async def create_student_account(
        self,
        student_id: int,
        email: str,
        phone: str,
        first_name: str,
        patronymic: str | None,
        last_name: str,
        course_id: int,
    ) -> int | None:
        try:
            async with self.pool.acquire() as connection:
                async with connection.transaction():
                    user_id = await connection.fetchval(
                        """
                        INSERT INTO users (email, phone)
                        VALUES ($1, $2)
                        ON CONFLICT (email) DO UPDATE
                        SET phone = EXCLUDED.phone
                        RETURNING id
                        """,
                        email.strip(),
                        phone.strip(),
                    )
                    role_id = await connection.fetchval("SELECT id FROM roles WHERE code = 'student'")
                    await connection.execute(
                        """
                        INSERT INTO user_roles (user_id, role_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                        """,
                        user_id,
                        role_id,
                    )
                    await connection.execute(
                        """
                        INSERT INTO students (
                            id,
                            user_id,
                            first_name,
                            patronymic,
                            last_name,
                            course_id
                        )
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        student_id,
                        user_id,
                        first_name.strip(),
                        patronymic.strip() if patronymic else None,
                        last_name.strip(),
                        course_id,
                    )
                    return user_id
        except asyncpg.UniqueViolationError:
            return None

    async def create_teacher_account(
        self,
        email: str,
        phone: str,
        first_name: str,
        patronymic: str | None,
        last_name: str,
        office: str | None,
        consultation_notes: str | None,
    ) -> int | None:
        try:
            async with self.pool.acquire() as connection:
                async with connection.transaction():
                    user_id = await connection.fetchval(
                        """
                        INSERT INTO users (email, phone)
                        VALUES ($1, $2)
                        ON CONFLICT (email) DO UPDATE
                        SET phone = EXCLUDED.phone
                        RETURNING id
                        """,
                        email.strip(),
                        phone.strip(),
                    )
                    role_id = await connection.fetchval("SELECT id FROM roles WHERE code = 'teacher'")
                    await connection.execute(
                        """
                        INSERT INTO user_roles (user_id, role_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                        """,
                        user_id,
                        role_id,
                    )
                    await connection.execute(
                        """
                        INSERT INTO teachers (
                            user_id,
                            first_name,
                            patronymic,
                            last_name,
                            office,
                            consultation_notes
                        )
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        user_id,
                        first_name.strip(),
                        patronymic.strip() if patronymic else None,
                        last_name.strip(),
                        office.strip() if office else None,
                        consultation_notes.strip() if consultation_notes else None,
                    )
                    return user_id
        except asyncpg.UniqueViolationError:
            return None

    async def get_student_subjects(self, telegram_user_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT subj.id, subj.name, subj.description
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN student_subjects ss ON ss.student_id = s.id
            JOIN subjects subj ON subj.id = ss.subject_id
            WHERE u.telegram_user_id = $1
            ORDER BY subj.name
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id)]

    async def get_student_teachers(self, telegram_user_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT DISTINCT
                t.id,
                t.first_name,
                t.patronymic,
                t.last_name,
                u_teacher.email,
                u_teacher.phone,
                t.office,
                t.consultation_notes
            FROM students s
            JOIN users u_student ON u_student.id = s.user_id
            JOIN student_subjects ss ON ss.student_id = s.id
            JOIN subject_teachers st ON st.subject_id = ss.subject_id
            JOIN teachers t ON t.id = st.teacher_id
            LEFT JOIN users u_teacher ON u_teacher.id = t.user_id
            WHERE u_student.telegram_user_id = $1
            ORDER BY t.last_name, t.first_name
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id)]

    async def get_schedule(self, telegram_user_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT
                sch.weekday,
                sch.starts_at,
                sch.ends_at,
                sch.room,
                subj.name AS subject_name,
                t.last_name AS teacher_last_name,
                t.first_name AS teacher_first_name,
                t.patronymic AS teacher_patronymic
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN schedules sch ON sch.course_id = s.course_id
            JOIN subjects subj ON subj.id = sch.subject_id
            JOIN teachers t ON t.id = sch.teacher_id
            WHERE u.telegram_user_id = $1
            ORDER BY sch.weekday, sch.starts_at
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id)]

    async def get_college_info(self) -> list[dict[str, Any]]:
        rows = await self.pool.fetch("SELECT title, body FROM college_info ORDER BY id")
        return [dict(row) for row in rows]

    async def search_faq(self, query_text: str) -> list[dict[str, Any]]:
        query = """
            SELECT category, question, answer
            FROM faq_questions
            WHERE to_tsvector('simple', question || ' ' || answer || ' ' || keywords)
                @@ plainto_tsquery('simple', $1)
               OR question ILIKE '%' || $1 || '%'
               OR answer ILIKE '%' || $1 || '%'
               OR keywords ILIKE '%' || $1 || '%'
            ORDER BY category, question
            LIMIT 5
        """
        return [dict(row) for row in await self.pool.fetch(query, query_text.strip())]

    async def get_faq_categories(self) -> list[str]:
        rows = await self.pool.fetch("SELECT DISTINCT category FROM faq_questions ORDER BY category")
        return [row["category"] for row in rows]

    async def get_faq_by_category(self, category: str) -> list[dict[str, Any]]:
        query = """
            SELECT category, question, answer
            FROM faq_questions
            WHERE category = $1
            ORDER BY question
        """
        return [dict(row) for row in await self.pool.fetch(query, category)]

    async def get_announcements(self, telegram_user_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT a.title, a.body, a.published_at, c.group_code
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN announcements a ON a.course_id IS NULL OR a.course_id = s.course_id
            LEFT JOIN courses c ON c.id = a.course_id
            WHERE u.telegram_user_id = $1 AND a.is_active = true
            ORDER BY a.published_at DESC
            LIMIT 10
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id)]

    async def get_subject_resources(self, telegram_user_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT subj.name AS subject_name, r.title, r.url, r.description
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN student_subjects ss ON ss.student_id = s.id
            JOIN subjects subj ON subj.id = ss.subject_id
            JOIN subject_resources r ON r.subject_id = subj.id
            WHERE u.telegram_user_id = $1
            ORDER BY subj.name, r.title
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id)]

    async def get_assignments(self, telegram_user_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT subj.name AS subject_name, a.title, a.description, a.due_date
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN student_subjects ss ON ss.student_id = s.id
            JOIN subjects subj ON subj.id = ss.subject_id
            JOIN assignments a ON a.subject_id = subj.id
            WHERE u.telegram_user_id = $1
            ORDER BY a.due_date, subj.name
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id)]

    async def get_grades(self, telegram_user_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT subj.name AS subject_name, g.grade, g.max_grade, g.comment, g.graded_at
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN grades g ON g.student_id = s.id
            JOIN subjects subj ON subj.id = g.subject_id
            WHERE u.telegram_user_id = $1
            ORDER BY g.graded_at DESC, subj.name
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id)]

    async def toggle_lesson_reminders(self, telegram_user_id: int) -> bool:
        query = """
            UPDATE students s
            SET lesson_reminders_enabled = NOT lesson_reminders_enabled
            FROM users u
            WHERE u.id = s.user_id AND u.telegram_user_id = $1
            RETURNING s.lesson_reminders_enabled
        """
        return await self.pool.fetchval(query, telegram_user_id)

    async def get_due_lesson_reminders(self) -> list[dict[str, Any]]:
        query = """
            SELECT
                s.id AS student_id,
                u.telegram_user_id,
                sch.id AS schedule_id,
                CURRENT_DATE AS lesson_date,
                sch.starts_at,
                sch.room,
                subj.name AS subject_name,
                t.last_name AS teacher_last_name,
                t.first_name AS teacher_first_name,
                t.patronymic AS teacher_patronymic
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN schedules sch ON sch.course_id = s.course_id
            JOIN subjects subj ON subj.id = sch.subject_id
            JOIN teachers t ON t.id = sch.teacher_id
            LEFT JOIN lesson_reminder_logs lrl
                ON lrl.student_id = s.id
               AND lrl.schedule_id = sch.id
               AND lrl.lesson_date = CURRENT_DATE
            WHERE u.telegram_user_id IS NOT NULL
              AND s.lesson_reminders_enabled = true
              AND sch.weekday = EXTRACT(ISODOW FROM CURRENT_DATE)
              AND sch.starts_at BETWEEN (LOCALTIME + INTERVAL '25 minutes')
                                  AND (LOCALTIME + INTERVAL '35 minutes')
              AND lrl.id IS NULL
        """
        return [dict(row) for row in await self.pool.fetch(query)]

    async def mark_lesson_reminder_sent(
        self,
        student_id: int,
        schedule_id: int,
        lesson_date: date,
    ) -> None:
        query = """
            INSERT INTO lesson_reminder_logs (student_id, schedule_id, lesson_date)
            VALUES ($1, $2, $3)
            ON CONFLICT (student_id, schedule_id, lesson_date) DO NOTHING
        """
        await self.pool.execute(query, student_id, schedule_id, lesson_date)

    async def get_consultation_requests(self, telegram_user_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT cr.id, cr.requested_date, cr.starts_at, cr.ends_at, cr.topic, cr.status, cr.created_at,
                   t.last_name, t.first_name, t.patronymic
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN consultation_requests cr ON cr.student_id = s.id
            JOIN teachers t ON t.id = cr.teacher_id
            WHERE u.telegram_user_id = $1
            ORDER BY cr.created_at DESC
            LIMIT 10
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id)]

    async def get_support_tickets(self, telegram_user_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT st.id, sc.name AS category, st.message, st.status, st.resolution_comment, st.created_at
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN support_tickets st ON st.student_id = s.id
            JOIN support_categories sc ON sc.id = st.category_id
            WHERE u.telegram_user_id = $1
            ORDER BY st.created_at DESC
            LIMIT 10
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id)]

    async def count_admin_consultations(self) -> int:
        return await self.pool.fetchval("SELECT count(*) FROM consultation_requests")

    async def get_admin_consultations(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        query = """
            SELECT cr.id, cr.requested_date, cr.topic, cr.status,
                   cr.starts_at, cr.ends_at, cr.created_at,
                   s.last_name AS student_last_name, s.first_name AS student_first_name,
                   t.last_name AS teacher_last_name, t.first_name AS teacher_first_name
            FROM consultation_requests cr
            JOIN students s ON s.id = cr.student_id
            JOIN teachers t ON t.id = cr.teacher_id
            ORDER BY cr.requested_date DESC, cr.starts_at DESC, cr.id DESC
            LIMIT $1 OFFSET $2
        """
        return [dict(row) for row in await self.pool.fetch(query, limit, offset)]

    async def get_pending_support_tickets(self) -> list[dict[str, Any]]:
        query = """
            SELECT st.id, sc.name AS category, st.message, st.status, st.resolution_comment,
                   s.last_name AS student_last_name, s.first_name AS student_first_name
            FROM support_tickets st
            JOIN students s ON s.id = st.student_id
            JOIN support_categories sc ON sc.id = st.category_id
            WHERE st.status IN ('new', 'in_progress')
            ORDER BY st.created_at
            LIMIT 20
        """
        return [dict(row) for row in await self.pool.fetch(query)]

    async def log_status_change(
        self,
        entity_type: str,
        entity_id: int,
        old_status: str | None,
        new_status: str,
        actor_telegram_user_id: int | None = None,
        comment: str | None = None,
    ) -> None:
        actor_user_id = None
        if actor_telegram_user_id is not None:
            actor_user_id = await self.get_user_id_by_telegram(actor_telegram_user_id)
        query = """
            INSERT INTO request_status_history (
                entity_type,
                entity_id,
                old_status,
                new_status,
                changed_by_user_id,
                comment
            )
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        await self.pool.execute(query, entity_type, entity_id, old_status, new_status, actor_user_id, comment)

    async def update_consultation_status(
        self,
        request_id: int,
        status: str,
        actor_telegram_user_id: int | None = None,
    ) -> bool:
        query = """
            WITH old_row AS (
                SELECT id, status
                FROM consultation_requests
                WHERE id = $1
            )
            UPDATE consultation_requests cr
            SET status = $2
            FROM old_row
            WHERE cr.id = old_row.id
              AND old_row.status IN ('new', 'approved')
              AND old_row.status <> $2
              AND $2 = ANY(ARRAY['new', 'approved', 'rejected', 'done', 'cancelled']::text[])
            RETURNING old_row.status AS old_status
        """
        old_status = await self.pool.fetchval(query, request_id, status)
        if old_status is None:
            return False
        await self.log_status_change("consultation", request_id, old_status, status, actor_telegram_user_id)
        return True

    async def update_support_status(
        self,
        ticket_id: int,
        status: str,
        actor_telegram_user_id: int | None = None,
        resolution_comment: str | None = None,
    ) -> bool:
        query = """
            WITH old_row AS (
                SELECT id, status
                FROM support_tickets
                WHERE id = $1
            )
            UPDATE support_tickets st
            SET status = $2,
                resolution_comment = COALESCE($3, st.resolution_comment)
            FROM old_row
            WHERE st.id = old_row.id
              AND old_row.status IN ('new', 'in_progress')
              AND old_row.status <> $2
              AND $2 = ANY(ARRAY['new', 'in_progress', 'resolved', 'closed', 'cancelled']::text[])
            RETURNING old_row.status AS old_status
        """
        old_status = await self.pool.fetchval(query, ticket_id, status, resolution_comment)
        if old_status is None:
            return False
        await self.log_status_change("support", ticket_id, old_status, status, actor_telegram_user_id, resolution_comment)
        return True

    async def get_teacher_consultations(self, telegram_user_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT cr.id, cr.requested_date, cr.starts_at, cr.ends_at, cr.topic, cr.status,
                   s.last_name AS student_last_name, s.first_name AS student_first_name,
                   c.group_code
            FROM users u
            JOIN teachers t ON t.user_id = u.id
            JOIN consultation_requests cr ON cr.teacher_id = t.id
            JOIN students s ON s.id = cr.student_id
            JOIN courses c ON c.id = s.course_id
            WHERE u.telegram_user_id = $1
              AND cr.status IN ('new', 'approved')
            ORDER BY cr.requested_date, cr.starts_at
            LIMIT 20
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id)]

    async def update_teacher_consultation_status(
        self,
        telegram_user_id: int,
        request_id: int,
        status: str,
    ) -> bool:
        query = """
            WITH old_row AS (
                SELECT cr.id, cr.status
                FROM consultation_requests cr
                JOIN teachers t ON t.id = cr.teacher_id
                JOIN users u ON u.id = t.user_id
                WHERE u.telegram_user_id = $1
                  AND cr.id = $2
            )
            UPDATE consultation_requests cr
            SET status = $3
            FROM old_row
            WHERE cr.id = old_row.id
              AND old_row.status IN ('new', 'approved')
              AND old_row.status <> $3
              AND $3 = ANY(ARRAY['approved', 'rejected', 'done']::text[])
            RETURNING old_row.status AS old_status
        """
        old_status = await self.pool.fetchval(query, telegram_user_id, request_id, status)
        if old_status is None:
            return False
        await self.log_status_change("consultation", request_id, old_status, status, telegram_user_id)
        return True

    async def get_support_queue(self) -> list[dict[str, Any]]:
        return await self.get_pending_support_tickets()

    async def cancel_consultation_request(self, telegram_user_id: int, request_id: int) -> bool:
        query = """
            WITH old_row AS (
                SELECT cr.id, cr.status
                FROM consultation_requests cr
                JOIN students s ON s.id = cr.student_id
                JOIN users u ON u.id = s.user_id
                WHERE u.telegram_user_id = $1
                  AND cr.id = $2
                  AND cr.status IN ('new', 'approved')
            )
            UPDATE consultation_requests cr
            SET status = 'cancelled'
            FROM old_row
            WHERE cr.id = old_row.id
            RETURNING old_row.status AS old_status
        """
        old_status = await self.pool.fetchval(query, telegram_user_id, request_id)
        if old_status is None:
            return False
        await self.log_status_change("consultation", request_id, old_status, "cancelled", telegram_user_id)
        return True

    async def cancel_support_ticket(self, telegram_user_id: int, ticket_id: int) -> bool:
        query = """
            WITH old_row AS (
                SELECT st.id, st.status
                FROM support_tickets st
                JOIN students s ON s.id = st.student_id
                JOIN users u ON u.id = s.user_id
                WHERE u.telegram_user_id = $1
                  AND st.id = $2
                  AND st.status IN ('new', 'in_progress')
            )
            UPDATE support_tickets st
            SET status = 'cancelled'
            FROM old_row
            WHERE st.id = old_row.id
            RETURNING old_row.status AS old_status
        """
        old_status = await self.pool.fetchval(query, telegram_user_id, ticket_id)
        if old_status is None:
            return False
        await self.log_status_change("support", ticket_id, old_status, "cancelled", telegram_user_id)
        return True

    async def get_teacher_by_id_for_student(
        self,
        telegram_user_id: int,
        teacher_id: int,
    ) -> dict[str, Any] | None:
        query = """
            SELECT DISTINCT t.id, t.first_name, t.patronymic, t.last_name
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN student_subjects ss ON ss.student_id = s.id
            JOIN subject_teachers st ON st.subject_id = ss.subject_id
            JOIN teachers t ON t.id = st.teacher_id
            WHERE u.telegram_user_id = $1 AND t.id = $2
        """
        row = await self.pool.fetchrow(query, telegram_user_id, teacher_id)
        return dict(row) if row else None

    async def get_available_consultation_dates(
        self,
        telegram_user_id: int,
        teacher_id: int,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT cs.slot_date, count(DISTINCT cs.id) AS slots_count
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN student_subjects ss ON ss.student_id = s.id
            JOIN subject_teachers st ON st.subject_id = ss.subject_id
            JOIN consultation_slots cs ON cs.teacher_id = st.teacher_id
            LEFT JOIN consultation_requests cr
                ON cr.consultation_slot_id = cs.id
               AND cr.status IN ('new', 'approved')
            WHERE u.telegram_user_id = $1
              AND st.teacher_id = $2
              AND cs.is_active = true
              AND cs.slot_date >= CURRENT_DATE
              AND cr.id IS NULL
            GROUP BY cs.slot_date
            ORDER BY cs.slot_date
            LIMIT 14
        """
        return [dict(row) for row in await self.pool.fetch(query, telegram_user_id, teacher_id)]

    async def get_available_consultation_slots(
        self,
        telegram_user_id: int,
        teacher_id: int,
        slot_date: date,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT DISTINCT cs.id, cs.slot_date, cs.starts_at, cs.ends_at
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN student_subjects ss ON ss.student_id = s.id
            JOIN subject_teachers st ON st.subject_id = ss.subject_id
            JOIN consultation_slots cs ON cs.teacher_id = st.teacher_id
            LEFT JOIN consultation_requests cr
                ON cr.consultation_slot_id = cs.id
               AND cr.status IN ('new', 'approved')
            WHERE u.telegram_user_id = $1
              AND st.teacher_id = $2
              AND cs.slot_date = $3
              AND cs.is_active = true
              AND cr.id IS NULL
            ORDER BY cs.starts_at
        """
        return [
            dict(row)
            for row in await self.pool.fetch(query, telegram_user_id, teacher_id, slot_date)
        ]

    async def get_consultation_slot_for_student(
        self,
        telegram_user_id: int,
        slot_id: int,
    ) -> dict[str, Any] | None:
        query = """
            SELECT DISTINCT
                cs.id,
                cs.teacher_id,
                cs.slot_date,
                cs.starts_at,
                cs.ends_at,
                t.first_name,
                t.patronymic,
                t.last_name
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN student_subjects ss ON ss.student_id = s.id
            JOIN subject_teachers st ON st.subject_id = ss.subject_id
            JOIN consultation_slots cs ON cs.teacher_id = st.teacher_id
            JOIN teachers t ON t.id = cs.teacher_id
            LEFT JOIN consultation_requests cr
                ON cr.consultation_slot_id = cs.id
               AND cr.status IN ('new', 'approved')
            WHERE u.telegram_user_id = $1
              AND cs.id = $2
              AND cs.is_active = true
              AND cs.slot_date >= CURRENT_DATE
              AND cr.id IS NULL
        """
        row = await self.pool.fetchrow(query, telegram_user_id, slot_id)
        return dict(row) if row else None

    async def create_consultation_request(
        self,
        telegram_user_id: int,
        slot_id: int,
        topic: str,
    ) -> int | None:
        query = """
            INSERT INTO consultation_requests (
                student_id,
                teacher_id,
                consultation_slot_id,
                requested_date,
                starts_at,
                ends_at,
                topic
            )
            SELECT DISTINCT s.id, cs.teacher_id, cs.id, cs.slot_date, cs.starts_at, cs.ends_at, $3
            FROM students s
            JOIN users u ON u.id = s.user_id
            JOIN consultation_slots cs ON cs.id = $2
            JOIN student_subjects ss ON ss.student_id = s.id
            JOIN subject_teachers st ON st.subject_id = ss.subject_id AND st.teacher_id = cs.teacher_id
            LEFT JOIN consultation_requests cr
                ON cr.consultation_slot_id = cs.id
               AND cr.status IN ('new', 'approved')
            WHERE u.telegram_user_id = $1
              AND cs.is_active = true
              AND cs.slot_date >= CURRENT_DATE
              AND cr.id IS NULL
            RETURNING id
        """
        try:
            return await self.pool.fetchval(query, telegram_user_id, slot_id, topic)
        except asyncpg.UniqueViolationError:
            return None

    async def create_teacher_consultation_slot(
        self,
        telegram_user_id: int,
        slot_date: date,
        starts_at: time,
        ends_at: time,
    ) -> int | None:
        if starts_at >= ends_at:
            return None
        query = """
            INSERT INTO consultation_slots (teacher_id, slot_date, starts_at, ends_at)
            SELECT t.id, $2, $3, $4
            FROM teachers t
            JOIN users u ON u.id = t.user_id
            WHERE u.telegram_user_id = $1
              AND $2 >= CURRENT_DATE
            ON CONFLICT (teacher_id, slot_date, starts_at) DO NOTHING
            RETURNING id
        """
        return await self.pool.fetchval(query, telegram_user_id, slot_date, starts_at, ends_at)

    async def get_support_categories(self) -> list[dict[str, Any]]:
        query = """
            SELECT id, name, description
            FROM support_categories
            WHERE is_active = true
            ORDER BY name
        """
        return [dict(row) for row in await self.pool.fetch(query)]

    async def get_support_category(self, category_id: int) -> dict[str, Any] | None:
        query = """
            SELECT id, name, description
            FROM support_categories
            WHERE id = $1 AND is_active = true
        """
        row = await self.pool.fetchrow(query, category_id)
        return dict(row) if row else None

    async def create_support_ticket(
        self,
        telegram_user_id: int,
        category_id: int,
        message: str,
    ) -> int:
        query = """
            INSERT INTO support_tickets (student_id, category_id, message)
            SELECT s.id, $2, $3
            FROM students s
            JOIN users u ON u.id = s.user_id
            WHERE u.telegram_user_id = $1
            RETURNING id
        """
        return await self.pool.fetchval(query, telegram_user_id, category_id, message)

    async def get_due_consultation_reminders(self) -> list[dict[str, Any]]:
        query = """
            SELECT
                cr.id AS request_id,
                u_student.telegram_user_id AS student_telegram_user_id,
                u_teacher.telegram_user_id AS teacher_telegram_user_id,
                cr.requested_date,
                cr.starts_at,
                cr.ends_at,
                cr.topic,
                s.last_name AS student_last_name,
                s.first_name AS student_first_name,
                t.last_name AS teacher_last_name,
                t.first_name AS teacher_first_name,
                t.patronymic AS teacher_patronymic
            FROM consultation_requests cr
            JOIN students s ON s.id = cr.student_id
            JOIN users u_student ON u_student.id = s.user_id
            JOIN teachers t ON t.id = cr.teacher_id
            LEFT JOIN users u_teacher ON u_teacher.id = t.user_id
            LEFT JOIN consultation_reminder_logs crl ON crl.request_id = cr.id
            WHERE cr.status = 'approved'
              AND cr.requested_date = CURRENT_DATE
              AND cr.starts_at BETWEEN (LOCALTIME + INTERVAL '25 minutes')
                                  AND (LOCALTIME + INTERVAL '35 minutes')
              AND crl.id IS NULL
        """
        return [dict(row) for row in await self.pool.fetch(query)]

    async def mark_consultation_reminder_sent(self, request_id: int) -> None:
        query = """
            INSERT INTO consultation_reminder_logs (request_id)
            VALUES ($1)
            ON CONFLICT (request_id) DO NOTHING
        """
        await self.pool.execute(query, request_id)
