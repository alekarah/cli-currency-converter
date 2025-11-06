#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import requests
from datetime import datetime
from colorama import init, Fore, Style

# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Инициализация colorama для Windows
init(autoreset=True)

API_URL = "https://api.exchangerate-api.com/v4/latest/"


def print_header():
    """Выводит заголовок программы"""
    print(Fore.GREEN + Style.BRIGHT + "╔════════════════════════════════════════╗")
    print(Fore.GREEN + Style.BRIGHT + "║   КОНВЕРТЕР ВАЛЮТ (Python Version)     ║")
    print(Fore.GREEN + Style.BRIGHT + "╚════════════════════════════════════════╝")
    print()


def get_input(prompt):
    """Получает ввод от пользователя"""
    return input(prompt).strip().upper()


def get_amount(prompt):
    """Получает сумму от пользователя"""
    while True:
        try:
            amount = float(input(prompt).strip())
            if amount <= 0:
                print(Fore.RED + "❌ Сумма должна быть положительной!")
                continue
            return amount
        except ValueError:
            print(Fore.RED + "❌ Ошибка: введите корректное число!")


def get_exchange_rates(base_currency):
    """Получает курсы валют из API"""
    try:
        print(Fore.CYAN + "🔄 Загрузка актуальных курсов валют...")
        response = requests.get(f"{API_URL}{base_currency}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"❌ Ошибка при получении курсов: {e}")
        sys.exit(1)
    except ValueError as e:
        print(Fore.RED + f"❌ Ошибка парсинга ответа API: {e}")
        sys.exit(1)


def format_time_ago(time_diff):
    """Форматирует время, прошедшее с момента обновления"""
    total_seconds = int(time_diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 24:
        days = hours // 24
        if days == 1:
            return "1 день назад"
        elif days < 5:
            return f"{days} дня назад"
        else:
            return f"{days} дней назад"

    if hours > 0:
        if hours == 1:
            return "1 час назад"
        elif hours < 5:
            return f"{hours} часа назад"
        else:
            return f"{hours} часов назад"

    if minutes > 0:
        if minutes == 1:
            return "1 минуту назад"
        elif minutes < 5:
            return f"{minutes} минуты назад"
        else:
            return f"{minutes} минут назад"

    return "только что"


def convert_currency(amount, from_currency, to_currency, rates_data):
    """Конвертирует валюту"""
    rates = rates_data.get('rates', {})

    if to_currency not in rates:
        print(Fore.RED + f"❌ Валюта {to_currency} не найдена!")
        sys.exit(1)

    rate = rates[to_currency]
    result = amount * rate
    return result, rate


def print_result(amount, from_currency, result, to_currency, rate, rates_data):
    """Выводит результат конвертации"""
    print()
    print(Fore.YELLOW + Style.BRIGHT + "════════════════ РЕЗУЛЬТАТ ════════════════")

    print(Fore.GREEN + f"{amount:.2f} {from_currency} = {result:.2f} {to_currency}")

    print()
    print(Fore.CYAN + f"Курс: 1 {from_currency} = {rate:.4f} {to_currency}")

    # Вывод времени последнего обновления
    timestamp = rates_data.get('time_last_updated', 0)
    if timestamp:
        update_time = datetime.fromtimestamp(timestamp)
        time_diff = datetime.now() - update_time
        time_ago = format_time_ago(time_diff)
        print()
        print(Fore.LIGHTBLACK_EX + f"Последнее обновление: {update_time.strftime('%Y-%m-%d %H:%M:%S')} ({time_ago})")

    print()
    print(Fore.YELLOW + Style.BRIGHT + "═══════════════════════════════════════════")


def main():
    """Главная функция программы"""
    print_header()

    # Получаем параметры из командной строки или интерактивно
    if len(sys.argv) == 4:
        # Режим с аргументами командной строки
        from_currency = sys.argv[1].upper()
        to_currency = sys.argv[2].upper()
        try:
            amount = float(sys.argv[3])
            if amount <= 0:
                print(Fore.RED + "❌ Сумма должна быть положительной!")
                sys.exit(1)
        except ValueError:
            print(Fore.RED + "❌ Ошибка: неверная сумма")
            sys.exit(1)
    else:
        # Интерактивный режим
        from_currency = get_input("Введите исходную валюту (например, USD): ")
        to_currency = get_input("Введите целевую валюту (например, RUB): ")
        amount = get_amount("Введите сумму для конвертации: ")

    # Получаем курсы валют
    rates_data = get_exchange_rates(from_currency)

    # Выполняем конвертацию
    result, rate = convert_currency(amount, from_currency, to_currency, rates_data)

    # Выводим результат
    print_result(amount, from_currency, result, to_currency, rate, rates_data)


if __name__ == "__main__":
    main()
