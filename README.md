# shelly-firmware

Инструмент для скачивания и сборки бинарного образа официальной прошивки Shelly.  
Готовый образ можно использовать для восстановления устройства через ESP-программатор.

---

## Авторство

Оригинальный скрипт написан [Ioannis Prevezanos (ioprev)](https://github.com/ioprev).  
Оригинальный репозиторий: [ioprev/shelly-firmware](https://github.com/ioprev/shelly-firmware)

Данный форк содержит исправление совместимости для Python 3.7+ и современных окружений:
- Библиотека `sh` заменена на стандартный `subprocess` (устраняет `AttributeError: 'str' object has no attribute 'exit_code'`)
- Добавлены таймауты для сетевых запросов
- Улучшена обработка ошибок

---

## Установка

```bash
git clone https://github.com/askarkurymbayev/shelly-firmware.git
cd shelly-firmware

# Установить зависимости
pip3 install requests

# Собрать инструменты для работы со SPIFFS
sudo apt install build-essential git make
./build_tools.sh
```

---

## Использование

```bash
# Список доступных моделей
./shelly_firmware.py -l

# Скачать и собрать прошивку для модели
./shelly_firmware.py -d SHSW-1 -o firmware.bin

# Собрать из локального zip-файла
./shelly_firmware.py -i firmware.zip -o firmware.bin

# Подробный вывод для отладки
./shelly_firmware.py -d SHSW-1 -v
```

---
💛 Support / Поддержка
If this plugin is useful to you, consider buying me a coffee!

Если плагин оказался полезным — буду рад вашей поддержке!

PayPal

👉 paypal.me/askarkurymbayev

## Лицензия

MIT — Copyright (c) 2019 Ioannis Prevezanos
