from six import iteritems
import config
import telebot
import pymongo
from pymongo import MongoClient

client = MongoClient(config.host, config.port)
db = client['test_db']
bot = telebot.TeleBot(config.token)


def get_last_month():
    return db['last_month'].find({})[0]['last_month']


def up_last_month():
    last_month = get_last_month()
    db['last_month'].delete_one({'last_month': get_last_month()})
    if (last_month % 100) % 12 == 0:
        last_month += 89
    else:
        last_month += 1
    db['last_month'].insert_one({'last_month': last_month})


def check_month(month_id):
    if month_id != get_last_month():
        change_last_month(month_id)


def add(name, price, short_name):
    if db['name'].find_one({'month': get_last_month(), 'short_name': short_name}) is None:
        db['name'].insert_one({'month': get_last_month(), 'short_name': short_name, 'name': name})
    db['data'].insert_one({'month': get_last_month(), 'data': {short_name: price}})


def calc_result(month_id):
    db['result'].delete_one({'month': month_id})
    result = {'month': month_id, 'data': {}}
    for data in db['data'].find({'month': month_id}):
        name, price = list(data['data'].items())[0]
        result['data'].setdefault(name, 0)
        result['data'][name] += price
    db['result'].insert_one(result)


def get_real_names():
    result = {}
    if db['name'].find_one({'month': get_last_month()}) is not None:
        for row in db['name'].find({'month': get_last_month()}):
            result[row['short_name']] = row['name']
    return result


def get_result(month_id):
    if get_last_month() == month_id:
        calc_result(month_id)
    result = ['RESULT {}'.format(month_id)]
    names = get_real_names()
    for name, price in iteritems(db['result'].find({'month': month_id})[0]['data']):
        result.append('{} = {}'.format(names.get(name, name), price))
    return '\n'.join(result)


def is_number(text):
    try:
        int(text)
        return True
    except:
        return False


def parse_text(text):
    text = text.lower().strip().split()
    if len(text) != 2:
        return 'ERROR', 0
    if is_number(text[0]):
        return text[1], int(text[0])
    return text[0], int(text[1])


@bot.message_handler(commands=['next'])
def switch_to_next_month(message):
    last_month = get_last_month()
    result = get_result(last_month)
    up_last_month()
    result = 'MONTH HAS UPDATED TO {}\n{}'.format(get_last_month(), result)
    bot.send_message(message.chat.id, result)


@bot.message_handler(commands=['curr'])
def send_curr_result(message):
    last_month = get_last_month()
    result = get_result(last_month)
    bot.send_message(message.chat.id, result)


@bot.message_handler(commands=['result'])
def send_result(message):
    text = message.text.lower().strip().split()
    if len(text) < 2:
        bot.send_message(message.chat.id, 'Invalid month_id.\nType "/result YYYYMM" like "/result 201711"')
        return
    month = text[1]
    try:
        result = get_result(month)
        bot.send_message(message.chat.id, result)
    except:
        bot.send_message(message.chat.id, 'Invalid month_id "{}".\nShould be YYYYMM like 201711.'.format(month))

@bot.message_handler(func=lambda message: message.chat.id == config.group_id, content_types=["text"])
def processing_all_messages(message):
    name, price = parse_text(message.text)
    if name == 'ERROR':
        bot.send_message(message.chat.id, 'Invalid format.\nShould be "%name %price"\ntwo words separated by space\n%price should contain only digits')
    else:
        short_name = name
        if len(name) > 3:
            short_name = name[:3]
        add(name, price, short_name)


if __name__ == '__main__':
    bot.polling(none_stop=True)
