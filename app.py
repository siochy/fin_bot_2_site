from flask import Flask, session, redirect, url_for, request, render_template
import os, dotenv, hashlib, asyncio, matplotlib, time

import sql_for_bot, graphics

app = Flask(__name__)
dotenv.load_dotenv()
token = os.getenv('TOKEN')
bot_name = os.getenv('BOT_NAME')
domain = os.getenv('BOT_DOMAIN')

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['TELEGRAM_BOT_TOKEN'] = token
app.config['SECRET_KEY'] = hashlib.sha256(app.config['TELEGRAM_BOT_TOKEN'].encode('utf-8')).digest()

app.jinja_env.globals.update(BOTID = token)
app.jinja_env.globals.update(BOTNAME = bot_name)
app.jinja_env.globals.update(BOTDOMAIN = domain)


@app.before_request
def make_session_permanent():
    session.permanent = True


def template(tmpl_name, **kwargs):
    telegram = False
    user_id = session.get('user_id')
    username = session.get('name')
    photo = session.get('photo')

    if user_id:
        telegram = True

    return render_template(tmpl_name,
                           telegram = telegram,
                           user_id = user_id,
                           name = username,
                           photo = photo,
                           **kwargs)



@app.route('/')
def index():
    return template(tmpl_name='index.html')


@app.route("/logout")
def logout():
    session.pop("user_id")
    session.pop("name")
    session.pop("photo")

    return redirect(url_for('index'))


def draw_graphics():
    user = str(session.get('user_id'))
    db_id = asyncio.run(sql_for_bot.user_check(user))
    if not db_id:
        asyncio.run(sql_for_bot.create_user(user))
        db_id = asyncio.run(sql_for_bot.user_check(user))
    asyncio.run(graphics.monthly_inc_sav_graph(db_id, user))
    asyncio.run(graphics.top_purchases_graph(db_id, user, '1970-01-01', '2030-12-31'))
    asyncio.run(graphics.daily_graph(db_id, user))


@app.route('/graphics')
def graphs():
    user = str(session.get('user_id'))
    img_path_daily = f'images/{user}/daily.jpeg'
    img_path_incsav = f'images/{user}/income_save.jpeg'
    img_path_top = f'images/{user}/top.jpeg'
    return template('graphs.html',
                    daily=img_path_daily,
                    incsav=img_path_incsav,
                    top=img_path_top)


@app.route("/login")
def login():
    user_id = request.args.get("id")
    first_name = request.args.get("first_name")
    photo_url = request.args.get("photo_url")

    session['user_id'] = user_id
    session['name'] = first_name
    session['photo'] = photo_url

    matplotlib.use('agg') # using to avoid problems with creating graphics
    draw_graphics()

    return redirect(url_for('graphs'))

@app.route("/refresh")
def refresh():
    matplotlib.use('agg') # using to avoid problems with creating graphics
    draw_graphics()
    return redirect(url_for('graphs'))


if __name__ == '__main__':
    app.run("0.0.0.0", debug=True)
