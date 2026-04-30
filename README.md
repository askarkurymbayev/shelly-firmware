# shelly-firmware

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---
## 🇬🇧 English

A tool for downloading and assembling a binary image of the official **Shelly** firmware.  
The resulting image can be used to restore a device via an ESP programmer.

### Credits

Original script by [Ioannis Prevezanos (ioprev)](https://github.com/ioprev).  
Original repository: [ioprev/shelly-firmware](https://github.com/ioprev/shelly-firmware)

This fork includes compatibility fixes for Python 3.7+ and modern environments:

- ✅ Replaced the `sh` library with standard `subprocess` (fixes `AttributeError: 'str' object has no attribute 'exit_code'`)
- ✅ Added timeouts for network requests
- ✅ Improved error handling

### Requirements

- Python >= 3.7
- `pip3` and the `requests` library
- `build-essential`, `git`, `make` (for building SPIFFS tools)
- Shelly device accessible via ESP programmer

### Installation

```bash
git clone https://github.com/askarkurymbayev/shelly-firmware.git
cd shelly-firmware

# Install Python dependencies
pip3 install requests

# Install system dependencies and build SPIFFS tools
sudo apt install build-essential git make
./build_tools.sh
```

### Usage

```bash
# List available models
./shelly_firmware.py -l

# Download and assemble firmware for a model
./shelly_firmware.py -d SHSW-1 -o firmware.bin

# Assemble from a local zip file
./shelly_firmware.py -i firmware.zip -o firmware.bin

# Verbose output for debugging
./shelly_firmware.py -d SHSW-1 -v
```

| Argument | Description                              |
|----------|------------------------------------------|
| `-l`     | List all available device models         |
| `-d`     | Specify device model to download         |
| `-i`     | Use a local zip file as input            |
| `-o`     | Path to the output binary file           |
| `-v`     | Enable verbose output for debugging      |

### Troubleshooting

- Make sure Python >= 3.7 and all dependencies are installed correctly
- Verify that `build_tools.sh` completed without errors
- Use the `-v` flag for detailed logs when issues arise

---

## 🇷🇺 Русский

Инструмент для скачивания и сборки бинарного образа официальной прошивки **Shelly**.  
Готовый образ можно использовать для восстановления устройства через ESP-программатор.

### Авторство

Оригинальный скрипт написан [Ioannis Prevezanos (ioprev)](https://github.com/ioprev).  
Оригинальный репозиторий: [ioprev/shelly-firmware](https://github.com/ioprev/shelly-firmware)

Данный форк содержит исправления совместимости для Python 3.7+ и современных окружений:

- ✅ Библиотека `sh` заменена на стандартный `subprocess` (устраняет `AttributeError: 'str' object has no attribute 'exit_code'`)
- ✅ Добавлены таймауты для сетевых запросов
- ✅ Улучшена обработка ошибок

### Требования

- Python >= 3.7
- `pip3` и библиотека `requests`
- `build-essential`, `git`, `make` (для сборки инструментов SPIFFS)
- Устройство Shelly с доступом через ESP-программатор

### Установка

```bash
git clone https://github.com/askarkurymbayev/shelly-firmware.git
cd shelly-firmware

# Установить зависимости Python
pip3 install requests

# Установить системные зависимости и собрать инструменты SPIFFS
sudo apt install build-essential git make
./build_tools.sh
```

### Использование

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

| Аргумент | Описание                               |
|----------|----------------------------------------|
| `-l`     | Показать список доступных моделей      |
| `-d`     | Указать модель устройства для загрузки |
| `-i`     | Использовать локальный zip-файл        |
| `-o`     | Путь к выходному бинарному файлу       |
| `-v`     | Подробный вывод для отладки            |

### Устранение неполадок

- Убедитесь, что Python >= 3.7 и все зависимости установлены корректно
- Проверьте, что скрипт `build_tools.sh` выполнился без ошибок
- Используйте флаг `-v` для получения подробных логов при возникновении ошибок

---

## 💛 Support / Поддержка

If this script is useful to you, consider buying me a coffee!

Если скрипт оказался полезным — буду рад вашей поддержке!

[![PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.me/askarkurymbayev)

👉 [paypal.me/askarkurymbayev](https://www.paypal.me/askarkurymbayev)

---

## License / Лицензия

[MIT](LICENSE) © 2019 Ioannis Prevezanos, 2024 Askar Kurymbayev
