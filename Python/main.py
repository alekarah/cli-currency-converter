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
CONFIG_FILE = "config.json"
CACHE_FILE = "cache.json"
CACHE_TTL = 60  # минут


def load_config():
    """Загружает конфигурацию из config.json"""
    config = {
        "default_from": "USD",
        "default_to": "RUB",
        "output_format": "text"
    }
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            config.update(user_config)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    config["default_from"] = config["default_from"].upper()
    config["default_to"] = config["default_to"].upper()
    config["output_format"] = config["output_format"].lower()
    return config


def print_help():
    """Выводит справку по использованию программы"""
    print(Fore.GREEN + Style.BRIGHT + "╔════════════════════════════════════════╗")
    print(Fore.GREEN + Style.BRIGHT + "║   КОНВЕРТЕР ВАЛЮТ (Python Version)     ║")
    print(Fore.GREEN + Style.BRIGHT + "╚════════════════════════════════════════╝")
    print()
    print(Fore.YELLOW + Style.BRIGHT + "Использование:")
    print("  python main.py [флаги] <from> <to> <amount>")
    print("  python main.py [флаги] <from> <to1,to2,...> <amount>")
    print()
    print(Fore.YELLOW + Style.BRIGHT + "Флаги вывода:")
    print(Fore.CYAN + "  --json       Вывод результата в формате JSON")
    print(Fore.CYAN + "  --csv        Вывод результата в формате CSV")
    print(Fore.CYAN + "  --table      Вывод результата в виде таблицы")
    print()
    print(Fore.YELLOW + Style.BRIGHT + "Прочие флаги:")
    print(Fore.CYAN + "  --offline    Использовать сохранённые курсы без запроса к API")
    print(Fore.CYAN + "  --history          Показать историю всех конвертаций")
    print(Fore.CYAN + "  --history USD/RUB  Показать историю по конкретной паре")
    print(Fore.CYAN + "  --help, -h   Показать эту справку")
    print()
    print(Fore.YELLOW + Style.BRIGHT + "Примеры:")
    print("  python main.py USD RUB 100")
    print("  python main.py --table USD RUB,EUR,CNY 100")
    print("  python main.py --json USD EUR 50")
    print("  python main.py --offline USD RUB 100")
    print("  python main.py --history USD/RUB")
    print()


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


def load_cache():
    """Загружает кэш курсов из файла"""
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    """Сохраняет кэш курсов в файл"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get_exchange_rates(base_currency, silent=False, offline=False):
    """Получает курсы валют из кэша или API"""
    cache = load_cache()
    if base_currency in cache:
        entry = cache[base_currency]
        fetched_at = datetime.fromisoformat(entry["fetched_at"])
        age_minutes = (datetime.now() - fetched_at).total_seconds() / 60
        if offline or age_minutes < CACHE_TTL:
            if not silent:
                if offline:
                    print(Fore.LIGHTBLACK_EX + f"📴 Оффлайн режим: используются сохранённые курсы от {fetched_at.strftime('%Y-%m-%d %H:%M')}")
                else:
                    remaining = int(CACHE_TTL - age_minutes)
                    print(Fore.LIGHTBLACK_EX + f"💾 Используются кэшированные курсы (обновление через {remaining} мин.)")
            return entry["data"]

    if offline:
        print(Fore.RED + f"❌ Нет сохранённых курсов для {base_currency} — выполните конвертацию онлайн хотя бы раз")
        sys.exit(1)

    try:
        if not silent:
            print(Fore.CYAN + "🔄 Загрузка актуальных курсов валют...")
        response = requests.get(f"{API_URL}{base_currency}", timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        if not silent:
            print(Fore.RED + f"❌ Ошибка при получении курсов: {e}")
        sys.exit(1)
    except ValueError as e:
        if not silent:
            print(Fore.RED + f"❌ Ошибка парсинга ответа API: {e}")
        sys.exit(1)

    # Сохраняем в кэш
    cache[base_currency] = {"fetched_at": datetime.now().isoformat(), "data": data}
    save_cache(cache)
    return data


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


def convert_currency(amount, _, to_currency, rates_data):
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


def show_history(filter_pair=""):
    """Показывает историю конвертаций, сгруппированную по валютным парам"""
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

    # Фильтруем по паре если задан фильтр (например "USD/RUB")
    if filter_pair:
        parts = filter_pair.split("/")
        if len(parts) == 2:
            history = [r for r in history if r['from_currency'] == parts[0] and r['to_currency'] == parts[1]]
        else:
            history = [r for r in history if r['from_currency'] == filter_pair or r['to_currency'] == filter_pair]
        if not history:
            print(Fore.YELLOW + f"📝 Записей для {filter_pair} не найдено")
            return

    # Группируем по паре FROM/TO с сохранением порядка
    groups = {}
    order = []
    for rec in history:
        key = (rec['from_currency'], rec['to_currency'])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(rec)

    print(Fore.GREEN + Style.BRIGHT + "╔════════════════════════════════════════╗")
    print(Fore.GREEN + Style.BRIGHT + "║      ИСТОРИЯ КОНВЕРТАЦИЙ               ║")
    print(Fore.GREEN + Style.BRIGHT + "╚════════════════════════════════════════╝")

    total = 0
    for key in order:
        records = groups[key]
        total += len(records)
        from_cur, to_cur = key

        print()
        print(Fore.YELLOW + Style.BRIGHT + f"  {from_cur} → {to_cur} ({len(records)} записей)")
        print(Fore.YELLOW + Style.BRIGHT + "  ┌─────────────────────┬──────────────┬──────────────────┬──────────────┬────┐")
        print(Fore.YELLOW + Style.BRIGHT + "  │ Дата                │ Сумма        │ Результат        │ Курс         │    │")
        print(Fore.YELLOW + Style.BRIGHT + "  ├─────────────────────┼──────────────┼──────────────────┼──────────────┼────┤")

        for i, rec in enumerate(records):
            timestamp = datetime.fromisoformat(rec['timestamp'])
            trend = "  "
            if i > 0:
                prev_rate = records[i-1]['exchange_rate']
                if rec['exchange_rate'] > prev_rate:
                    trend = Fore.GREEN + "▲ " + Style.RESET_ALL
                elif rec['exchange_rate'] < prev_rate:
                    trend = Fore.RED + "▼ " + Style.RESET_ALL
            print(Fore.GREEN + f"  │ {timestamp.strftime('%Y-%m-%d %H:%M'):<19} │ {rec['amount']:<12.2f} │ {rec['result']:<16.2f} │ {rec['exchange_rate']:<12.4f} │ {trend}│")

        print(Fore.YELLOW + Style.BRIGHT + "  └─────────────────────┴──────────────┴──────────────────┴──────────────┴────┘")

        # Статистика
        rates = [r['exchange_rate'] for r in records]
        print(Fore.LIGHTBLACK_EX + f"  Мин: {min(rates):.4f}  Макс: {max(rates):.4f}  Средний: {sum(rates)/len(rates):.4f}")

    print()
    print(Fore.YELLOW + Style.BRIGHT + f"Всего записей: {total}")


def print_table(amount, from_currency, rows, rates_data):
    """Выводит результаты конвертации в виде таблицы"""
    print()
    print(Fore.YELLOW + Style.BRIGHT + f"  Конвертация {amount:.2f} {from_currency}")
    print(Fore.YELLOW + Style.BRIGHT + "  ┌──────────┬────────────────┬──────────────┐")
    print(Fore.YELLOW + Style.BRIGHT + "  │ Валюта   │ Результат      │ Курс         │")
    print(Fore.YELLOW + Style.BRIGHT + "  ├──────────┼────────────────┼──────────────┤")
    for currency, result, rate in rows:
        print(Fore.GREEN + f"  │ {currency:<8} │ {result:<14.2f} │ {rate:<12.4f} │")
    print(Fore.YELLOW + Style.BRIGHT + "  └──────────┴────────────────┴──────────────┘")

    timestamp = rates_data.get('time_last_updated', 0)
    if timestamp:
        update_time = datetime.fromtimestamp(timestamp)
        time_diff = datetime.now() - update_time
        time_ago = format_time_ago(time_diff)
        print()
        print(Fore.LIGHTBLACK_EX + f"  Последнее обновление: {update_time.strftime('%Y-%m-%d %H:%M:%S')} ({time_ago})")
    print()


def main():
    """Главная функция программы"""
    # Проверяем флаг --help
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print_help()
        return

    # Проверяем флаг --history
    if len(sys.argv) > 1 and sys.argv[1] == "--history":
        filter_pair = sys.argv[2].upper() if len(sys.argv) > 2 else ""
        show_history(filter_pair)
        return

    # Загружаем конфигурацию
    cfg = load_config()

    # Проверяем флаги --json, --csv, --table, --offline
    json_output = False
    csv_output = False
    table_output = False
    offline_mode = False
    args = sys.argv[1:]
    for flag in ("--json", "--csv", "--table", "--offline"):
        if flag in args:
            args.remove(flag)
            if flag == "--json":
                json_output = True
            elif flag == "--csv":
                csv_output = True
            elif flag == "--table":
                table_output = True
            elif flag == "--offline":
                offline_mode = True

    # Применяем формат вывода из конфига, если нет флагов
    if not json_output and not csv_output and not table_output:
        if cfg["output_format"] == "json":
            json_output = True
        elif cfg["output_format"] == "csv":
            csv_output = True
        elif cfg["output_format"] == "table":
            table_output = True

    if not json_output and not csv_output:
        print_header()

    # Получаем параметры из командной строки или интерактивно
    if len(args) == 3:
        # Режим с аргументами командной строки
        from_currency = args[0].upper()
        to_currency_raw = args[1].upper()
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
        # Интерактивный режим с подсказками из конфига
        from_currency = get_input(f"Введите исходную валюту (по умолчанию {cfg['default_from']}): ")
        if not from_currency:
            from_currency = cfg["default_from"]
        to_currency_raw = get_input(f"Введите целевую валюту (по умолчанию {cfg['default_to']}): ")
        if not to_currency_raw:
            to_currency_raw = cfg["default_to"]
        amount = get_amount("Введите сумму для конвертации: ")
    else:
        if json_output or csv_output:
            output_error("неверное количество аргументов", json_output)
        else:
            print(Fore.RED + f"❌ Использование: {sys.argv[0]} [--json|--csv] <from> <to1[,to2,...]> <amount>")
            print(Fore.RED + f"   или: {sys.argv[0]} --history")
        sys.exit(1)

    # Разбиваем целевые валюты (поддержка USD RUB,EUR,CNY 100)
    to_currencies = [c.strip() for c in to_currency_raw.split(",") if c.strip()]

    # Получаем курсы валют
    try:
        rates_data = get_exchange_rates(from_currency, silent=(json_output or csv_output), offline=offline_mode)
    except SystemExit:
        if json_output or csv_output:
            output_error("ошибка при получении курсов", json_output)
        raise

    timestamp = rates_data.get('time_last_updated', 0)
    update_time = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()

    # Для табличного режима собираем все результаты, затем выводим таблицу
    if table_output:
        rows = []
        for to_currency in to_currencies:
            try:
                result, rate = convert_currency(amount, from_currency, to_currency, rates_data)
            except SystemExit:
                print(Fore.RED + f"❌ Ошибка конвертации для {to_currency}")
                continue
            save_to_history(from_currency, to_currency, amount, result, rate, update_time)
            rows.append((to_currency, result, rate))
        print_table(amount, from_currency, rows, rates_data)
        return

    # Выполняем конвертацию для каждой валюты
    for to_currency in to_currencies:
        try:
            result, rate = convert_currency(amount, from_currency, to_currency, rates_data)
        except SystemExit:
            if json_output or csv_output:
                output_error(f"ошибка конвертации для {to_currency}", json_output)
            else:
                print(Fore.RED + f"❌ Ошибка конвертации для {to_currency}")
            continue

        save_to_history(from_currency, to_currency, amount, result, rate, update_time)

        if json_output:
            output_json(from_currency, to_currency, amount, result, rate, update_time)
        elif csv_output:
            output_csv(from_currency, to_currency, amount, result, rate)
        else:
            print_result(amount, from_currency, result, to_currency, rate, rates_data)


if __name__ == "__main__":
    main()
