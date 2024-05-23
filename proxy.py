import socket  # Модуль для работы с сокетами
import selectors  # Модуль для использования мультиплексирования ввода-вывода
import types  # Модуль для создания простых объектов
import concurrent.futures  # Модуль для работы с параллелизмом
from urllib.parse import urlparse  # Модуль для разбора URL-адресов
import logging  # Модуль для логирования

# Настройки логгирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Настройки
HOST = '127.0.0.1'  # IP-адрес сервера
PORT = 25566  # Порт сервера
CACHE = {}  # Кэш для хранения ответов сервера

# Инициализация селектора
sel = selectors.DefaultSelector()

def accept(sock, mask):
    conn, addr = sock.accept()  # Принять новое соединение
    logger.info(f'Accepted connection from {addr}')
    conn.setblocking(False)  # Установить неблокирующий режим
    data = types.SimpleNamespace(addr=addr, inb=b'', outb=b'')  # Создать объект для хранения данных соединения
    events = selectors.EVENT_READ | selectors.EVENT_WRITE  # Настроить события для чтения и записи
    sel.register(conn, events, data=data)  # Зарегистрировать соединение в селекторе

def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Чтение данных от клиента
        if recv_data:
            data.inb += recv_data
            if b'\r\n\r\n' in data.inb:  # Проверка завершения HTTP-запроса
                request_line = data.inb.split(b'\r\n')[0].decode()  # Извлечение первой строки запроса
                method, url, _ = request_line.split(' ')  # Разбор метода и URL
                if method == 'GET':
                    parsed_url = urlparse(url)
                    cache_key = (method, url)
                    if cache_key in CACHE:
                        logger.info(f'Cache hit for {url}')  # Сообщение о попадании в кэш
                        data.outb += CACHE[cache_key]
                    else:
                        logger.info(f'Cache miss for {url}')  # Сообщение о промахе кэша
                        target_host = parsed_url.hostname
                        target_port = parsed_url.port or 80
                        path = parsed_url.path
                        if parsed_url.query:
                            path += '?' + parsed_url.query
                        # Создание и отправка запроса к целевому серверу
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as target_socket:
                            target_socket.connect((target_host, target_port))
                            target_socket.sendall(f'GET {path} HTTP/1.0\r\nHost: {target_host}\r\n\r\n'.encode())
                            response = b''
                            while True:
                                chunk = target_socket.recv(4096)
                                if not chunk:
                                    break
                                response += chunk
                            CACHE[cache_key] = response  # Сохранение ответа в кэше
                            data.outb += response
        else:
            logger.info('Closing connection to %s', data.addr)  # Сообщение о закрытии соединения
            sel.unregister(sock)  # Удаление соединения из селектора
            sock.close()  # Закрытие сокета
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            sent = sock.send(data.outb)  # Отправка данных клиенту
            data.outb = data.outb[sent:]

def print_cache():
    logger.info("\nCurrent Cache Content:")
    for key, value in CACHE.items():
        logger.info(f'URL: {key[1]}')
        logger.info(f'Content: {value[:100]}...')  # Ограничение вывода 100 символами для читаемости
        logger.info('----------------------------')

def start_proxy(num_threads):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen()
    sock.setblocking(False)
    sel.register(sock, selectors.EVENT_READ, data=None)

    logger.info(f'Serving on {(HOST, PORT)}')
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            while True:
                events = sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        accept(key.fileobj, mask)
                    else:
                        executor.submit(service_connection, key, mask)  # Обработка соединения в потоке
    except KeyboardInterrupt:
        logger.info('Caught keyboard interrupt, exiting')  # Сообщение о завершении работы по сигналу прерывания
    finally:
        print_cache()  # Печать содержимого кэша при завершении работы
        sel.close()  # Закрытие селектора

start_proxy(3)  # Задайте желаемое количество потоков здесь
