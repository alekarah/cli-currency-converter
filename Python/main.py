#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import os
import requests
from datetime import datetime
from colorama import init, Fore, Style

# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Инициализация colorama для Windows
init(autoreset=True)

API_URL = "https://api.exchangerate-api.com/v4/latest/"
HISTORY_FILE = "history.json"


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


def get_exchange_rates(base_currency, silent=False):
    """Получает курсы валют из API"""
    try:
        if not silent:
            print(Fore.CYAN + "🔄 Загрузка актуальных курсов валют...")
        response = requests.get(f"{API_URL}{base_currency}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if not silent:
            print(Fore.RED + f"❌ Ошибка при получении курсов: {e}")
        sys.exit(1)
    except ValueError as e:
        if not silent:
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


def output_json(from_currency, to_currency, amount, result, rate, update_time):
    """Выводит результат в формате JSON"""
    output = {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "from_currency": from_currency,
        "to_currency": to_currency,
        "amount": amount,
        "result": result,
        "exchange_rate": rate,
        "rate_update_time": update_time.isoformat()
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def output_csv(from_currency, to_currency, amount, result, rate):
    """Выводит результат в формате CSV"""
    # timestamp,from,to,amount,result,rate
    print(f"{datetime.now().isoformat()},{from_currency},{to_currency},{amount:.2f},{result:.2f},{rate:.6f}")


def output_error(message, as_json=True):
    """Выводит ошибку в формате JSON или CSV"""
    if as_json:
        output = {
            "success": False,
            "error": message
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # CSV формат ошибки
        print(f"error,{message}")


def save_to_history(from_currency, to_currency, amount, result, rate, update_time):
    """Сохраняет запись в историю конвертаций"""
    record = {
        "timestamp": datetime.now().isoformat(),
        "from_currency": from_currency,
        "to_currency": to_currency,
        "amount": amount,
        "result": result,
        "exchange_rate": rate,
        "rate_update_time": update_time.isoformat()
    }

    # Читаем существующую историю
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            history = []

    # Добавляем новую запись
    history.append(record)

    # Сохраняем обратно
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def show_history():
    """Показывает историю конвертаций"""
    if not os.path.exists(HISTORY_FILE):
        print(Fore.RED + "❌ История конвертаций пуста или файл не найден")
        return

    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(Fore.RED + "❌ Ошибка чтения файла истории")
        return

    if not history:
        print(Fore.YELLOW + "📝 История конвертаций пуста")
        return

    print(Fore.GREEN + Style.BRIGHT + "╔════════════════════════════════════════╗")
    print(Fore.GREEN + Style.BRIGHT + "║      ИСТОРИЯ КОНВЕРТАЦИЙ               ║")
    print(Fore.GREEN + Style.BRIGHT + "╚════════════════════════════════════════╝")
    print()

    for rec in reversed(history):
        timestamp = datetime.fromisoformat(rec['timestamp'])
        print(Fore.CYAN + f"📅 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(Fore.GREEN + f"   {rec['amount']:.2f} {rec['from_currency']} = {rec['result']:.2f} {rec['to_currency']}")
        print(Fore.LIGHTBLACK_EX + f"   Курс: 1 {rec['from_currency']} = {rec['exchange_rate']:.4f} {rec['to_currency']}")
        print()

    print(Fore.YELLOW + Style.BRIGHT + f"Всего записей: {len(history)}")


def main():
    """Главная функция программы"""
    # Проверяем флаг --history
    if len(sys.argv) > 1 and sys.argv[1] == "--history":
        show_history()
        return

    # Проверяем флаги --json и --csv
    json_output = False
    csv_output = False
    args = sys.argv[1:]
    if "--json" in args:
        json_output = True
        args.remove("--json")
    if "--csv" in args:
        csv_output = True
        args.remove("--csv")

    if not json_output and not csv_output:
        print_header()

    # Получаем параметры из командной строки или интерактивно
    if len(args) == 3:
        # Режим с аргументами командной строки
        from_currency = args[0].upper()
        to_currency = args[1].upper()
        try:
            amount = float(args[2])
            if amount <= 0:
                if json_output or csv_output:
                    output_error("сумма должна быть положительной", json_output)
                else:
                    print(Fore.RED + "❌ Сумма должна быть положительной!")
                sys.exit(1)
        except ValueError:
            if json_output or csv_output:
                output_error("неверная сумма", json_output)
            else:
                print(Fore.RED + "❌ Ошибка: неверная сумма")
            sys.exit(1)
    elif len(args) == 0:
        # Интерактивный режим
        from_currency = get_input("Введите исходную валюту (например, USD): ")
        to_currency = get_input("Введите целевую валюту (например, RUB): ")
        amount = get_amount("Введите сумму для конвертации: ")
    else:
        if json_output or csv_output:
            output_error("неверное количество аргументов", json_output)
        else:
            print(Fore.RED + f"❌ Использование: {sys.argv[0]} [--json|--csv] <from> <to> <amount>")
            print(Fore.RED + f"   или: {sys.argv[0]} --history")
        sys.exit(1)

    # Получаем курсы валют
    try:
        rates_data = get_exchange_rates(from_currency, silent=(json_output or csv_output))
    except SystemExit:
        if json_output or csv_output:
            output_error("ошибка при получении курсов", json_output)
        raise

    # Выполняем конвертацию
    try:
        result, rate = convert_currency(amount, from_currency, to_currency, rates_data)
    except SystemExit:
        if json_output or csv_output:
            output_error("ошибка конвертации", json_output)
        raise

    # Сохраняем в историю
    timestamp = rates_data.get('time_last_updated', 0)
    update_time = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
    save_to_history(from_currency, to_currency, amount, result, rate, update_time)

    # Выводим результат
    if json_output:
        output_json(from_currency, to_currency, amount, result, rate, update_time)
    elif csv_output:
        output_csv(from_currency, to_currency, amount, result, rate)
    else:
        print_result(amount, from_currency, result, to_currency, rate, rates_data)


if __name__ == "__main__":
    main()
