import re
import base64
import imaplib
import email
import email.message
from loguru import logger
from art import text2art
from pprint import pprint

logger.add('log.log', rotation='5 MB', level='DEBUG')


@logger.catch 
def slice_str(s:str,start:str, end:str)->str:
    
    #s[:s.find(start)]+s[s.rfind(end)+1:-1]
    return s[s.find(start)+len(start):s.find(end)]



@logger.catch
def test():
    c = imaplib.IMAP4_SSL('imap.yandex.ru')
    login ='igor.gerasimov@in-u.ru'
    password = 'qeukagqoeslzkekb'

    c.login(login,password)
 
    c.select('INBOX', readonly=True)
    
    typ, msg_data = c.fetch('49', '(RFC822)')
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_string(str(response_part[1]))
            for header in [ 'subject', 'to', 'from' ]:
                print ('%-8s: %s' % (header.upper(), msg[header]))

@logger.catch
def test2(mail):
    raw_email_string=mail
    email_message = email.message_from_string(raw_email_string)
 
    if email_message.is_multipart():
        for payload in email_message.get_payload():
            body = payload.get_payload(decode=True).decode('utf-8')
            logger.debug(body)
            return body
    else:    
        body = email_message.get_payload(decode=True).decode('utf-8')
        logger.debug(body)
        return body


def remove_html_tags(text):
    """Remove html tags from a string"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

@logger.catch
def get_mail():
    imap = imaplib.IMAP4_SSL('imap.yandex.ru')
    login ='igor.gerasimov@in-u.ru'
    password = 'qeukagqoeslzkekb'

    imap.login(login,password)
 
    imap.list()
    imap.select("inbox")
    sender = 'info@lefortovo-mebel.ru'
    types, data =imap.search(None, 'FROM', f'{sender}')
    #types, data=  imap.search(None, '(FROM "info@lefortovo-mebel.ru")')
    status, data = imap.fetch('49', '(RFC822)')
    #logger.debug(data)
    a = test2(data[0][1].decode())
    a = remove_html_tags(a)
    #a = a.split('§')
    #logger.debug(a)
    a = prepare_text_email(a)
    
    #pprint(a)
    #a = slice_str(str(a),'ФИО:','Телефон:')
    logger.debug(a)

@logger.catch
def prepare_product(string:str):
    temp = []
    logger.info('подготовка товаров')
    #regex='[0-9]\).\(' #1) (
    s = re.split('[0-9]\).\(', string)
    s.pop(0)
    for prod in s:
        temp.append(prod.split('\xa0')[0])  
    return temp
    #logger.debug(s)


@logger.catch
def prepare_text_email(string:str)->dict:
    temp = {}
    fio = slice_str(string, 'ФИО:','Телефон:')
    temp.setdefault( 'фио', slice_str(str(string),'ФИО: ','Телефон:')) 
    temp.setdefault( 'телефон', slice_str(string,'Телефон: ','Email:')) 
    temp.setdefault( 'почта', slice_str(string,'Email: ','Дополнительная информация:')) 
    temp.setdefault( 'инфо', slice_str(string,'Дополнительная информация: ','Номер заказа:')) 
    temp.setdefault( 'номер заказа', slice_str(string,'Номер заказа: ','Статус заказа:')) 
    #temp.setdefault( 'товары', slice_str(string,'Список товаров: ','Итог:')) 
    a = prepare_product( slice_str(string,'Список товаров: ','Итог:'))
    temp.setdefault('товары',a)
    #logger.debug(a)
    return temp

@logger.catch
def main():
    #test()
    get_mail()

if __name__ == '__main__':
    art = text2art('mail', 'rand')
    print(art)
    main()
