import socket  # Импортируем модуль для работы с сетевыми соединениями
import selectors  # Импортируем модуль для работы с мультиплексированием
import types  # Импортируем модуль для создания объектов с динамическими атрибутами

# Инициализируем селектор по умолчанию
selector = selectors.DefaultSelector()

def initiate_connections(host, port, num_conns):
    server_address = (host, port)  # Задаем адрес сервера
    for conn_index in range(num_conns):  # Цикл для создания нескольких соединений
        conn_id = conn_index + 1  # Идентификатор соединения
        print(f'Запуск подключения {conn_id} к {server_address}')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Создаем новый сокет
        sock.setblocking(False)  # Устанавливаем неблокирующий режим
        sock.connect_ex(server_address)  # Инициируем подключение к серверу
        # Указываем, что будем следить за чтением и записью
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        # Создаем объект для хранения состояния соединения
        conn_data = types.SimpleNamespace(connid=conn_id, msg_total=0, recv_total=0, messages=[], outb=b'')
        # Регистрируем соединение в селекторе
        selector.register(sock, events, data=conn_data)

def handle_connection(key, mask):
    sock = key.fileobj  # Получаем сокет из ключа
    conn_data = key.data  # Получаем данные из ключа
    if mask & selectors.EVENT_READ:  # Если сокет готов для чтения
        received_data = sock.recv(1024)  # Читаем данные из сокета
        if received_data:
            print(f'Получено {received_data} от соединения {conn_data.connid}')
            conn_data.recv_total += len(received_data)  # Обновляем количество полученных данных
        if not received_data or conn_data.recv_total == conn_data.msg_total:  # Если данных нет или все данные получены
            print(f'Закрытие соединения {conn_data.connid}')
            selector.unregister(sock)  # Удаляем сокет из селектора
            sock.close()  # Закрываем сокет
    if mask & selectors.EVENT_WRITE:  # Если сокет готов для записи
        if not conn_data.outb and conn_data.messages:  # Если нет данных для отправки, но есть сообщения
            conn_data.outb = conn_data.messages.pop(0)  # Берем следующее сообщение
        if conn_data.outb:  # Если есть данные для отправки
            print(f'Отправка {conn_data.outb} к соединению {conn_data.connid}')
            sent_bytes = sock.send(conn_data.outb)  # Отправляем данные
            conn_data.outb = conn_data.outb[sent_bytes:]  # Обновляем буфер отправки

if __name__ == '__main__':
    host = 'localhost'  # Хост для подключения
    port = 9094  # Порт для подключения
    num_conns = 5  # Количество соединений

    initiate_connections(host, port, num_conns)  # Инициализация соединений

    try:
        while True:  # Основной цикл обработки событий
            events = selector.select(timeout=1)  # Ожидание событий с таймаутом 1 секунда
            if events:  # Если есть события
                for key, mask in events:  # Обрабатываем каждое событие
                    handle_connection(key, mask)
            if not selector.get_map():  # Если в селекторе не осталось зарегистрированных сокетов
                break
    except KeyboardInterrupt:
        print('Клиент остановлен')  # Обработка прерывания
    finally:
        selector.close()  # Закрытие селектора
