from matplotlib import pyplot, dates
import os

import sql_for_bot


async def daily_graph(user: int, user_tg_id: str) -> None:
    """create graphic plot that shows daily purchases"""

    x = list()
    y = list()
    data = await sql_for_bot.daily_sum(user, 'purchases')
    for i in data:
        x.append(i[0])  # date
        y.append(i[1])  # sum

    fig, ax = pyplot.subplots(figsize=(9, 4.8))
    pyplot.title('Spent Per Day')
    pyplot.plot(x, y)
    pyplot.ylabel('Sum in Rub')

    # dates could too many be so need to show only months
    months = dates.MonthLocator()
    days = dates.DayLocator()
    form = dates.DateFormatter('%Y-%m')
    
    ax.xaxis.set_major_locator(months)
    ax.xaxis.set_major_formatter(form)
    ax.xaxis.set_minor_locator(days)

    # create user's folder if it doesn't exist
    try:
        os.mkdir(f'static/images/{user_tg_id}')
    except FileExistsError:
        pass

    file_name = f'daily.jpeg'
    pyplot.savefig(f'static/images/{user_tg_id}/{file_name}')
    pyplot.cla()
    pyplot.close()


async def top_purchases_graph(user: int, user_tg_id: str, date1: str, date2: str) -> None:
    """create graphic bar that shows top of purchases based on sum for every purchase"""

    x = list()
    y = list()
    data = await sql_for_bot.top_purchases(user, date1, date2, 20)
    for i in data:
        x.append(i[0][0:7])  # product
        y.append(i[1])  # sum

    pyplot.figure(figsize=(9, 4.8))
    pyplot.xticks(rotation=35)
    pyplot.title('Top Purchases')
    pyplot.bar(x, y)
    pyplot.ylabel('Sum in Rub')

    # create user's folder if it doesn't exist
    try:
        os.mkdir(f'static/images/{user_tg_id}')
    except FileExistsError:
        pass

    file_name = f'top.jpeg'
    pyplot.savefig(f'static/images/{user_tg_id}/{file_name}')
    pyplot.cla()
    pyplot.close()


async def monthly_inc_sav_graph(user: int, user_tg_id: str) -> None:
    """create graphic double bar with income and savings per month\n
    so need to compare dates from tables find which don't exist and add these\n
    after - add income data to graphic and calculate saves with (save-take)"""

    x1 = list()
    x2 = list()
    y1 = list()
    y2 = list()

    # find dates which are absent in tables income, save, take
    # and add these dates to all tables with value 0
    # first - take data from db and turn this into dict
    data_income = dict(await sql_for_bot.monthly_sum(user, 'income'))
    data_take = dict(await sql_for_bot.monthly_sum(user, 'take'))
    data_save = dict(await sql_for_bot.monthly_sum(user, 'save'))

    # keys are dates, so check which are absent in other tables
    diff1 = set(data_income) ^ set(data_save)
    diff2 = set(data_save) ^ set(data_take)
    diff = tuple(diff1 | diff2)

    # add value 0 to tables where any dates didn't exist
    for i in diff:
        if i not in tuple(data_take):
            data_take[i] = 0
        if i not in tuple(data_income):
            data_income[i] = 0
        if i not in tuple(data_save):
            data_save[i] = 0

    for j in data_income:
        x1.append(j)
        y1.append(data_income[j] / 100)

    # from every sum of month subtract take from save
    subtract = list()
    for date in data_save:
        summ = data_save[date] - data_take[date]
        subtract.append((date, summ / 100))

    for f in subtract:
        x2.append(f[0])
        y2.append(f[1])

    pyplot.figure(figsize=(9, 4.8))
    pyplot.title('Income and Savings per Month')
    pyplot.bar(x1, y1, width=0.4, align='edge')
    pyplot.bar(x2, y2, width=-0.4, align='edge')
    pyplot.xlabel('Months')
    pyplot.ylabel('In 100 Rub')
    pyplot.legend(('Income', 'Savings'))

    # create user's folder if it doesn't exist
    try:
        os.mkdir(f'static/images/{user_tg_id}')
    except FileExistsError:
        pass

    file_name = f'income_save.jpeg'
    pyplot.savefig(f'static/images/{user_tg_id}/{file_name}')
    pyplot.cla()
    pyplot.close()
