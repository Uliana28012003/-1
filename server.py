import selectors  # Импортируем модуль для работы с селекторами
import socket  # Импортируем модуль для работы с сокетами
import types  # Импортируем модуль для создания простых объектов с атрибутами

# Инициализируем селектор по умолчанию
selector = selectors.DefaultSelector()

def handle_accept(sock):
    # Принимаем новое входящее соединение
    conn, addr = sock.accept()
    print(f'Подключено: {addr}')
    conn.setblocking(False)  # Устанавливаем неблокирующий режим
    # Создаем объект для хранения состояния соединения
    connection_data = types.SimpleNamespace(addr=addr, inb=b'', outb=b'')
    # Указываем, что будем следить за чтением и записью
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    # Регистрируем соединение в селекторе
    selector.register(conn, events, data=connection_data)

def manage_connection(key, mask):
    sock = key.fileobj  # Получаем сокет из ключа
    data = key.data  # Получаем данные из ключа
    if mask & selectors.EVENT_READ:  # Если сокет готов для чтения
        recv_data = sock.recv(1024)  # Получаем данные
        if recv_data:
            data.outb += recv_data  # Добавляем полученные данные в буфер
        else:
            print(f'Закрытие соединения с {data.addr}')
            selector.unregister(sock)  # Удаляем сокет из селектора
            sock.close()  # Закрываем сокет
    if mask & selectors.EVENT_WRITE:  # Если сокет готов для записи
        if data.outb:  # Если есть данные для отправки
            sent = sock.send(data.outb)  # Отправляем данные
            data.outb = data.outb[sent:]  # Обновляем буфер

if __name__ == '__main__':
    host, port = 'localhost', 9094
    # Задаем адрес и порт сервера
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Создаем слушающий сокет
    listen_sock.bind((host, port))  # Привязываем сокет к адресу и порту
    listen_sock.listen()  # Начинаем слушать
    print(f'Сервер запущен на {host}:{port}')
    listen_sock.setblocking(False)  # Устанавливаем неблокирующий режим
    selector.register(listen_sock, selectors.EVENT_READ, data=None)  # Регистрируем слушающий сокет

    try:
        while True:  # Основной цикл обработки событий
            events = selector.select(timeout=None)  # Ожидание событий
            for key, mask in events:  # Проходимся по событиям
                if key.data is None:  # Если новое входящее соединение
                    handle_accept(key.fileobj)  # Обрабатываем новое соединение
                else:
                    manage_connection(key, mask)  # Обрабатываем активное соединение
    except KeyboardInterrupt:
        print('Сервер остановлен')  # Обработка прерывания
    finally:
        selector.close()  # Закрытие селектора
