import time 
import re
import base64
import imaplib
import email
import email.message
from loguru import logger
from art import text2art
from pprint import pprint
from bitrix24 import Bitrix24
from dotenv import load_dotenv
import os
load_dotenv()

LOGIN = os.environ.get('login')
PASSWORD = os.environ.get('password')
webHook = os.environ.get('webhook')
bit = Bitrix24(webHook)
imap = imaplib.IMAP4_SSL('imap.yandex.ru')
imap.login(str(LOGIN),str(PASSWORD))


logger.add('log.log', rotation='5 MB', level='DEBUG')

fileName='id.txt'
f = open(fileName, 'r')
LAST_ID = int(f.read())
f.close()

@logger.catch
def isGet_contact(phone:str):
    a= bit.callMethod("crm.contact.list", FILTER={'PHONE':phone}, select=['ID'])
    logger.debug(a)
    if len(a) > 0:
        return True, a[0]['ID'] 
    else:
        return False, []


@logger.catch 
def slice_str(s:str,start:str, end:str):
    a = s.find(start)
    if a == -1:
        return ' '
    return s[s.find(start)+len(start):s.find(end)]

@logger.catch 
def slice_str_phone(s:str,start:str):
    return s[s.find(start)+len(start):s.find(start)+len(start)+18]

@logger.catch 
def slice_str_site(s:str,start:str):
    return s[s.find(start)+len(start):len(s)].split('/')[2]

@logger.catch
def test2(mail):
    raw_email_string=mail
    email_message = email.message_from_string(raw_email_string)
 
    if email_message.is_multipart():
        for payload in email_message.get_payload():
            body = payload.get_payload(decode=True).decode('utf-8')
            return body
    else:    
        body = email_message.get_payload(decode=True).decode('utf-8')
        return body


def remove_html_tags(text):
    """Remove html tags from a string"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

@logger.catch
def get_mail(ID):
    #login ='igor.gerasimov@in-u.ru'
    #password = 'qeukagqoeslzkekb'

 
    #sender = 'info@lefortovo-mebel.ru'
    #types, data=  imap.search(None, '(FROM "info@lefortovo-mebel.ru")')
    #logger.info(data)
    #for ID in data:
    status, data = imap.fetch(ID, '(RFC822)')
    #logger.debug(data)
    a = test2(data[0][1].decode())
    a = remove_html_tags(a)
    #a = a.split('§')
    #logger.debug(a)
    a = prepare_text_email(a)
    
    #pprint(a)
    #a = slice_str(str(a),'ФИО:','Телефон:')
    logger.debug(a)
    return a

@logger.catch
def prepare_product(string:str):
    temp = []
    #logger.info(string)
    logger.info('подготовка товаров')
    #regex='[0-9]\).\(' #1) (
    s = re.split('[0-9]\).\(', string)
    s.pop(0)
    temps = ''
    for count, prod in enumerate(s):
        b=[]
        a = prod.split('\xa0')[0]  
        a = a.split(')',maxsplit=1)[1]
        b.append(f'<br> {count+1} Товар: '+a.split('--')[0].strip())# название товара
        b.append('<br> Цена: '+a.split('--')[1].split('x')[0].replace('р.', '') \
                .replace(' ','').strip()) # цена одной штуки 
        b.append('<br> Количество: '+a.split('--')[1].split('x')[1].split('=')[0].strip()) # количество товара
        temp.append(b)
        a1 = ' '.join(b)
        temps += f'<br>\n{a1}\n'
    return temps
    #logger.debug(s)


@logger.catch
def prepare_text_email(string:str)->dict:
    temp = {}
    fio = slice_str(string, 'ФИО:','Телефон:')
    temp.setdefault( 'фио', slice_str(str(string),'ФИО: ','Телефон:')) 
    # TODO: можно записать лучше но я не помню как
    temp.setdefault( 'телефон', slice_str_phone(string,'Телефон: ') \
            .replace(' ','') \
            .replace('(','') \
            .replace(')','') \
            .replace('-','') \
            .replace('+','')) 
    temp.setdefault( 'почта', slice_str(string,'Email: ','Дополнительная информация:')) 
    temp.setdefault( 'инфо', slice_str(string,'Дополнительная информация: ','Номер заказа:')) 
    temp.setdefault( 'номер заказа', slice_str(string,'Номер заказа: ','Статус заказа')) 
    #temp.setdefault( 'товары', slice_str(string,'Список товаров: ','Итог:')) 
    a = prepare_product( slice_str(string,'Список товаров:','Итого:'))
    temp.setdefault('товары',a)
    temp.setdefault('Итог', slice_str(string,'Оплаченная сумма:','Список товаров:').split('из')[1])#.replace('р.','')) 
    temp.setdefault('Сайт', slice_str_site(string,'Получить ссылку на купленный товар Вы можете на странице заказа:'))
    #logger.debug(a)
    return temp

@logger.catch
def create_lid(mail:dict):
    #a = bit.callMethod('crm.lead.fields')
    email = None
    phone = None
    contact_id = None
    title = f"""Заказ в интернет-магазине {mail['номер заказа']}"""
    isGetContact = isGet_contact(mail['телефон'])
    site = None
    
    #if mail['Сайт'] == 'lefortovo-mebel.ru':
    #    site = 1036
    
    if isGetContact[0]:
        contact_id = isGetContact[1]
    else:
        phone = [{'VALUE':mail['телефон'], "VALUE_TYPE": "WORK" }] 
        email= [{ "VALUE": mail['почта'], "VALUE_TYPE": "WORK" }]

    a = bit.callMethod('crm.lead.add',fields={'TITLE':title,
        'NAME':mail['фио'],
        'EMAIL':email,
        #'COMMENTS':mail['инфо'] + mail['товары'] +'<br> Итог:' + mail['Итог'],
        'UF_CRM_1666867162960':mail['инфо'] + mail['товары'] +'<br> Итог:' + mail['Итог'] + "<br> <br> Сайт: "+ mail['Сайт'],
        'PHONE':phone ,
        'UF_CRM_1664182558362': site,
        'CONTACT_ID':contact_id})

    #a = bit.callMethod('crm.lead.add', TITLE=title,
    #        NAME=mail['фио'],
    #        EMAIL=mail['почта'],
    #        COMMENTS=mail['инфо'])
    logger.info(a)

@logger.catch
def test():
    #a= bit.callMethod('crm.productrow.fields')
    s = bit.callMethod('crm.lead.productrows.get', id=648) 
    a = bit.callMethod('crm.lead.productrows.set',
            id=648,
            row =[{
                "PRODUCT_ID": 76,
                "QUANTITY":2,
                }] )
               # [jолфыофыв{"ORIGINAL_PRODUCT_NAME": 'test1',
                #"PRICE": 40,"QUANTITY": 2 }]])
            #{ "PRODUCT_ID": 666, "PRICE": '100.00', "QUANTITY": '2' }]])
    a = bit.callMethod('crm.product.add',
            fields={ 
                    "NAME": "1С-Битрикс: Управление сайтом - Старт", 
                    "CURRENCY_ID": "RUB", 
                    "PRICE": 4900, 
                    "SORT": 500
                })
    a = bit.callMethod('crm.lead.productrows.set',
            id=648,
            rows=[{
                "PRODUCT_ID": a,
                "QUANTITY":2,
                }] )
    pprint(s)
    pprint(a)

@logger.catch
def del_list(lst):
    a = lst.copy()
    for i in lst:
        if int(i) > LAST_ID:
            continue
        else:
            a.remove(i)
    return a

@logger.catch
def main():
    global LAST_ID
    #sender = 'korzinymebeli@yandex.ru'
    #sender = 'info@lefortovo-mebel.ru'
    sender = 'noreply@megagroup.ru'
    #test()
    #imap.list()
    #imap.select("inbox")
    imap.select("&BBsEHA-")
   # for folder in imap.list()[1]:
   #     print(shlex.split(folder.decode())[-1])
    types, data =imap.search(None, 'FROM', f'{sender}')
    data = str(data[0]).replace("'",'').replace('b','').split(' ')
    
    data = del_list(data)
    logger.debug(data)
    if data == []:
        return 0

    for ID in data:
        mail = get_mail(ID)
        create_lid(mail)
        logger.info('создали лида')

        f = open(fileName, 'w')
        #f.write(data)
        f.write(ID)
        f.close()
        LAST_ID = int(ID)

if __name__ == '__main__':
    art = text2art('mail', 'rand')
    print(art)
    #test()
    while True:
        main()
        time.sleep(60)

    #a = isGet_contact('74441111111')
    #logger.debug(a)
