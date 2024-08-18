"""
That's the part to interact bot and func of graphics
with postgresql database using psycopg3 with async.

tables:
    users - id(auto, pk), tg_id(uq)\n
    purchases - id(auto, pk), user_id(fk), date, product, summ\n
    income - id(auto, pk), user_id(fk), date, summ\n
    save - id(auto, pk), user_id(fk), date, summ\n
    take - id(auto, pk), user_id(fk), date, summ\n
    balance - user_id(fk), date(pk), summ\n
    savings - user_id(fk), date(pk), summ
"""

import os
import dotenv

from psycopg import AsyncConnection as AsCon
from psycopg import sql


dotenv.load_dotenv()
database = os.getenv('DB')


async def user_check(user: str) -> int:
    """check if user already exists.\n
    yes: return his id in db.\n
    no: create record in 'users' table and return created id."""

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query = '''SELECT id FROM users
            WHERE tg_id = (%s);'''
            await curs.execute(query, (user,))

            user_id = await curs.fetchone()

    if user_id:
        return user_id[0]  # in this tuple first elem is user_id


async def create_user(user: str) -> None:
    """create user in db and 0 in balance, savings tables"""

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query = '''INSERT INTO users (tg_id)
            VALUES (%s);'''
            await curs.execute(query, (user,))

            query = '''SELECT id FROM users
            WHERE tg_id = (%s);'''
            await curs.execute(query, (user,))

            user_id = await curs.fetchone()

    await insert_into_bs(user_id[0], 'balance', 0)
    await insert_into_bs(user_id[0], 'savings', 0)


async def get_balance_savings(user: int, table: str) -> float:
    """resulting last date record of user.\n
     prefer 'savings' or 'balance'"""

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query = sql.SQL('''SELECT summ FROM {table}
                WHERE date = (SELECT max(date) FROM {table})
                AND user_id = (%s);''').format(table=sql.Identifier(table.lower()))
            await curs.execute(query, (user,))
            result = await curs.fetchone()

    if result:
        return result[0]  # in this tuple only the first elem is balance


async def insert_into_bs(user: int, table: str, summ: float) -> None:
    """insert changes to table deleting today's record if exists.\n
    prefer 'balance' or 'savings' """

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query = sql.SQL('''DELETE FROM {table}
            WHERE user_id = (%s) AND
            date = CURRENT_DATE;''').format(table=sql.Identifier(table.lower()))
            await curs.execute(query, (user,))

            query = sql.SQL('''INSERT INTO {table} (user_id, date, summ)
            VALUES ((%s), CURRENT_DATE, (%s));''').format(table=sql.Identifier(table.lower()))
            await curs.execute(query, (user, summ))


async def insert_into_pcs(user: int, prod: str, summ: float) -> None:
    """just insert into table 'purchases', oh no, some purchase\n"""

    prod = prod.lower().capitalize().strip().replace(' ', '_')

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query = '''INSERT INTO purchases (user_id, date, product, summ)
            VALUES ((%s), CURRENT_DATE, (%s), (%s))'''
            await curs.execute(query, (user, prod, summ))


async def insert_into_sti(user: int, table: str, summ: float) -> None:
    """insert records to 'save', 'take', 'income'\n
    it could be in purchases, but I decided\n
    that for analyze this would be better"""

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query = sql.SQL('''INSERT INTO {table} (user_id, date, summ)
            VALUES ((%s), CURRENT_DATE, %s)''').format(table=sql.Identifier(table.lower()))
            await curs.execute(query, (user, summ))


async def calc_new_bs(prod: str, balance: float, savings: float, summ: float) -> tuple[float, float]:
    """calculate new balance and savings\n
    for 'save': balance- savings+\n
    'take': balance+ savings-\n
    'income': balance+\n
    in other cases: balance-"""

    match prod.lower():
        case 'save':
            balance -= summ
            savings += summ
        case 'take':
            balance += summ
            savings -= summ
        case 'income':
            balance += summ
        case _:
            balance -= summ

    return balance, savings


async def purchases_period(user: int, date1: str, date2: str) -> tuple:
    """returning records of purchases between date1 and date2\n
    with summary of it in the end"""

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query1 = '''SELECT date::text, product, summ FROM purchases
            WHERE user_id = (%s) AND date::text BETWEEN (%s) AND (%s)
            ORDER BY date, id;'''
            await curs.execute(query1, (user, date1, date2))
            result1 = await curs.fetchall()

            query2 = '''SELECT 'Period', 'Summary', SUM(summ)
            FROM purchases
            WHERE user_id = (%s) AND date::text BETWEEN (%s) AND (%s);'''
            await curs.execute(query2, (user, date1, date2))
            result2 = await curs.fetchall()

            result = result1 + result2

    return tuple(result)


async def monthly_sum(user: int, table: str) -> tuple:
    """return sums for every month\n
    of save, take, income or purchases"""

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query = sql.SQL(
                '''SELECT to_char(DATE_TRUNC('month', date), 'yyyy-mm') as month, SUM(summ)
                FROM {table}
                WHERE user_id = (%s)
                GROUP BY month ORDER BY month;''').format(table=sql.Identifier(table.lower()))
            await curs.execute(query, (user,))
            result = await curs.fetchall()

    return tuple(result)


async def top_purchases(user: int, date1: str, date2: str, limit=10**7) -> tuple:
    """showing top of purchases depends on sum of each other/n
    it could be limited (top-5 idk) if you want\n
    well, and it needs period of dates"""

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query = '''SELECT product, SUM(summ) AS sums
                FROM purchases
                WHERE user_id = (%s) AND date::text BETWEEN (%s) AND (%s)
                GROUP BY product
                ORDER BY sums DESC
                LIMIT (%s);'''
            # after a fight with psycopg i just used big number instead of 'ALL'
            # to be able to use it with limit and without
            await curs.execute(query, (user, date1, date2, limit))
            result = await curs.fetchall()

    return tuple(result)


async def daily_sum(user: int, table: str) -> tuple:
    """sums per day\n
    prefer to build with it graphic\n
    to show how much was purchases per day"""

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query = sql.SQL(
                '''SELECT date, SUM(summ)
                FROM {table}
                WHERE user_id = (%s)
                GROUP BY date ORDER BY date;''').format(table=sql.Identifier(table.lower()))
            await curs.execute(query, (user,))
            result = await curs.fetchall()

    return tuple(result)


async def balance_savings_period(user: int, table: str, date1: str, date2: str) -> tuple:
    """return records of balance or savings of some period"""

    async with await AsCon.connect(database) as conn:
        async with conn.cursor() as curs:
            query = sql.SQL(
                '''SELECT date::text, summ FROM {table}
                WHERE user_id = (%s) AND
                date::text BETWEEN (%s) AND (%s)
                ORDER BY date;''').format(table=sql.Identifier(table.lower()))
            await curs.execute(query, (user, date1, date2))
            result = await curs.fetchall()

    return tuple(result)
