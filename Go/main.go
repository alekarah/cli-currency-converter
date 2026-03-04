package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/fatih/color"
)

// ExchangeRateResponse структура ответа от API
type ExchangeRateResponse struct {
	Base             string             `json:"base"`
	Date             string             `json:"date"`
	Rates            map[string]float64 `json:"rates"`
	TimeLastUpdated  int64              `json:"time_last_updated"`
}

// ConversionRecord запись об одной конвертации
type ConversionRecord struct {
	Timestamp      time.Time `json:"timestamp"`
	FromCurrency   string    `json:"from_currency"`
	ToCurrency     string    `json:"to_currency"`
	Amount         float64   `json:"amount"`
	Result         float64   `json:"result"`
	ExchangeRate   float64   `json:"exchange_rate"`
	RateUpdateTime time.Time `json:"rate_update_time"`
}

// JSONOutput структура для JSON вывода результата
type JSONOutput struct {
	Success        bool      `json:"success"`
	Timestamp      time.Time `json:"timestamp"`
	FromCurrency   string    `json:"from_currency"`
	ToCurrency     string    `json:"to_currency"`
	Amount         float64   `json:"amount"`
	Result         float64   `json:"result"`
	ExchangeRate   float64   `json:"exchange_rate"`
	RateUpdateTime time.Time `json:"rate_update_time"`
}

// Config структура конфигурационного файла
type Config struct {
	DefaultFrom  string `json:"default_from"`
	DefaultTo    string `json:"default_to"`
	OutputFormat string `json:"output_format"`
}

// TableRow строка таблицы результатов конвертации
type TableRow struct {
	Currency string
	Result   float64
	Rate     float64
}

// CacheEntry кэш курсов для одной базовой валюты
type CacheEntry struct {
	FetchedAt time.Time          `json:"fetched_at"`
	Data      ExchangeRateResponse `json:"data"`
}

const (
	apiURL      = "https://api.exchangerate-api.com/v4/latest/"
	historyFile = "history.json"
	configFile  = "config.json"
	cacheFile   = "cache.json"
	cacheTTL    = 60 * time.Minute
)

// loadConfig загружает конфигурацию из config.json
func loadConfig() Config {
	cfg := Config{
		DefaultFrom:  "USD",
		DefaultTo:    "RUB",
		OutputFormat: "text",
	}

	data, err := os.ReadFile(configFile)
	if err != nil {
		return cfg
	}

	json.Unmarshal(data, &cfg)
	cfg.DefaultFrom = strings.ToUpper(cfg.DefaultFrom)
	cfg.DefaultTo = strings.ToUpper(cfg.DefaultTo)
	cfg.OutputFormat = strings.ToLower(cfg.OutputFormat)
	return cfg
}

func main() {
	// Проверяем флаг --history
	if len(os.Args) > 1 && os.Args[1] == "--history" {
		showHistory()
		return
	}

	// Загружаем конфигурацию
	cfg := loadConfig()

	// Проверяем флаги --json и --csv
	jsonOutput := false
	csvOutput := false
	tableOutput := false
	args := os.Args[1:]
	for i := 0; i < len(args); i++ {
		if args[i] == "--json" {
			jsonOutput = true
			args = append(args[:i], args[i+1:]...)
			i--
		} else if args[i] == "--csv" {
			csvOutput = true
			args = append(args[:i], args[i+1:]...)
			i--
		} else if args[i] == "--table" {
			tableOutput = true
			args = append(args[:i], args[i+1:]...)
			i--
		}
	}

	// Применяем формат вывода из конфига, если нет флагов
	if !jsonOutput && !csvOutput && !tableOutput {
		switch cfg.OutputFormat {
		case "json":
			jsonOutput = true
		case "csv":
			csvOutput = true
		case "table":
			tableOutput = true
		}
	}

	if !jsonOutput && !csvOutput {
		printHeader()
	}

	// Получаем параметры из командной строки или интерактивно
	var fromCurrency, toCurrencyRaw string
	var amount float64

	if len(args) == 3 {
		// Режим с аргументами командной строки
		fromCurrency = strings.ToUpper(args[0])
		toCurrencyRaw = strings.ToUpper(args[1])
		var err error
		amount, err = strconv.ParseFloat(args[2], 64)
		if err != nil {
			if jsonOutput || csvOutput {
				outputError("неверная сумма", jsonOutput)
			} else {
				color.Red("❌ Ошибка: неверная сумма")
			}
			os.Exit(1)
		}
	} else if len(args) == 0 {
		// Интерактивный режим с подсказками из конфига
		fromCurrency = getInput(fmt.Sprintf("Введите исходную валюту (по умолчанию %s): ", cfg.DefaultFrom))
		if fromCurrency == "" {
			fromCurrency = cfg.DefaultFrom
		}
		toCurrencyRaw = getInput(fmt.Sprintf("Введите целевую валюту (по умолчанию %s): ", cfg.DefaultTo))
		if toCurrencyRaw == "" {
			toCurrencyRaw = cfg.DefaultTo
		}
		amount = getAmount("Введите сумму для конвертации: ")
	} else {
		if jsonOutput || csvOutput {
			outputError("неверное количество аргументов", jsonOutput)
		} else {
			color.Red("❌ Использование: %s [--json|--csv] <from> <to1[,to2,...]> <amount>", os.Args[0])
			color.Red("   или: %s --history", os.Args[0])
		}
		os.Exit(1)
	}

	// Разбиваем целевые валюты (поддержка USD RUB,EUR,CNY 100)
	toCurrencies := strings.Split(toCurrencyRaw, ",")

	// Получаем курсы валют
	if !jsonOutput && !csvOutput {
		color.Cyan("🔄 Загрузка актуальных курсов валют...")
	}
	rates, err := getExchangeRates(fromCurrency, jsonOutput || csvOutput)
	if err != nil {
		if jsonOutput || csvOutput {
			outputError(fmt.Sprintf("ошибка при получении курсов: %v", err), jsonOutput)
		} else {
			color.Red("❌ Ошибка при получении курсов: %v", err)
		}
		os.Exit(1)
	}

	updateTime := time.Unix(rates.TimeLastUpdated, 0)

	// Для табличного режима собираем все результаты, затем выводим таблицу
	if tableOutput {
		var rows []TableRow
		for _, toCurrency := range toCurrencies {
			toCurrency = strings.TrimSpace(toCurrency)
			if toCurrency == "" {
				continue
			}
			result, err := convertCurrency(amount, fromCurrency, toCurrency, rates)
			if err != nil {
				color.Red("❌ Ошибка конвертации для %s: %v", toCurrency, err)
				continue
			}
			rate := rates.Rates[toCurrency]
			saveToHistory(fromCurrency, toCurrency, amount, result, rate, updateTime)
			rows = append(rows, TableRow{toCurrency, result, rate})
		}
		printTable(amount, fromCurrency, rows, rates)
		return
	}

	// Выполняем конвертацию для каждой валюты
	for _, toCurrency := range toCurrencies {
		toCurrency = strings.TrimSpace(toCurrency)
		if toCurrency == "" {
			continue
		}

		result, err := convertCurrency(amount, fromCurrency, toCurrency, rates)
		if err != nil {
			if jsonOutput || csvOutput {
				outputError(fmt.Sprintf("ошибка конвертации: %v", err), jsonOutput)
			} else {
				color.Red("❌ Ошибка конвертации для %s: %v", toCurrency, err)
			}
			continue
		}

		rate := rates.Rates[toCurrency]
		saveToHistory(fromCurrency, toCurrency, amount, result, rate, updateTime)

		if jsonOutput {
			outputJSON(fromCurrency, toCurrency, amount, result, rate, updateTime)
		} else if csvOutput {
			outputCSV(fromCurrency, toCurrency, amount, result, rate, updateTime)
		} else {
			printResult(amount, fromCurrency, result, toCurrency, rates)
		}
	}
}

// printHeader выводит заголовок программы
func printHeader() {
	color.Set(color.FgGreen, color.Bold)
	fmt.Println("╔════════════════════════════════════════╗")
	fmt.Println("║     КОНВЕРТЕР ВАЛЮТ (Go Version)       ║")
	fmt.Println("╚════════════════════════════════════════╝")
	color.Unset()
	fmt.Println()
}

// getInput получает ввод от пользователя
func getInput(prompt string) string {
	fmt.Print(prompt)
	var input string
	fmt.Scanln(&input)
	return strings.ToUpper(strings.TrimSpace(input))
}

// getAmount получает сумму от пользователя
func getAmount(prompt string) float64 {
	fmt.Print(prompt)
	var input string
	fmt.Scanln(&input)
	amount, err := strconv.ParseFloat(input, 64)
	if err != nil {
		color.Red("❌ Ошибка: неверная сумма")
		os.Exit(1)
	}
	return amount
}

// loadCache загружает кэш курсов из файла
func loadCache() map[string]CacheEntry {
	cache := make(map[string]CacheEntry)
	data, err := os.ReadFile(cacheFile)
	if err != nil {
		return cache
	}
	json.Unmarshal(data, &cache)
	return cache
}

// saveCache сохраняет кэш курсов в файл
func saveCache(cache map[string]CacheEntry) {
	data, err := json.MarshalIndent(cache, "", "  ")
	if err != nil {
		return
	}
	os.WriteFile(cacheFile, data, 0644)
}

// getExchangeRates получает курсы валют из кэша или API
func getExchangeRates(baseCurrency string, silent bool) (*ExchangeRateResponse, error) {
	cache := loadCache()
	if entry, ok := cache[baseCurrency]; ok {
		if time.Since(entry.FetchedAt) < cacheTTL {
			if !silent {
				color.HiBlack("💾 Используются кэшированные курсы (обновление через %d мин.)",
					int(cacheTTL.Minutes())-int(time.Since(entry.FetchedAt).Minutes()))
			}
			return &entry.Data, nil
		}
	}

	client := &http.Client{
		Timeout: 10 * time.Second,
	}

	resp, err := client.Get(apiURL + baseCurrency)
	if err != nil {
		return nil, fmt.Errorf("ошибка при запросе к API: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API вернул код ошибки: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("ошибка чтения ответа: %w", err)
	}

	var rates ExchangeRateResponse
	err = json.Unmarshal(body, &rates)
	if err != nil {
		return nil, fmt.Errorf("ошибка парсинга JSON: %w", err)
	}

	// Сохраняем в кэш
	cache[baseCurrency] = CacheEntry{FetchedAt: time.Now(), Data: rates}
	saveCache(cache)

	return &rates, nil
}

// convertCurrency конвертирует валюту
func convertCurrency(amount float64, from, to string, rates *ExchangeRateResponse) (float64, error) {
	if rate, ok := rates.Rates[to]; ok {
		return amount * rate, nil
	}
	return 0, fmt.Errorf("валюта %s не найдена", to)
}

// formatTimeAgo форматирует время, прошедшее с момента обновления
func formatTimeAgo(duration time.Duration) string {
	hours := int(duration.Hours())
	minutes := int(duration.Minutes()) % 60

	if hours > 24 {
		days := hours / 24
		if days == 1 {
			return "1 день назад"
		}
		return fmt.Sprintf("%d дня/дней назад", days)
	}

	if hours > 0 {
		if hours == 1 {
			return "1 час назад"
		}
		if hours < 5 {
			return fmt.Sprintf("%d часа назад", hours)
		}
		return fmt.Sprintf("%d часов назад", hours)
	}

	if minutes > 0 {
		if minutes == 1 {
			return "1 минуту назад"
		}
		if minutes < 5 {
			return fmt.Sprintf("%d минуты назад", minutes)
		}
		return fmt.Sprintf("%d минут назад", minutes)
	}

	return "только что"
}

// printTable выводит результаты конвертации в виде таблицы
func printTable(amount float64, from string, rows []TableRow, rates *ExchangeRateResponse) {
	fmt.Println()
	color.Set(color.FgYellow, color.Bold)
	fmt.Printf("  Конвертация %.2f %s\n", amount, from)
	fmt.Println("  ┌──────────┬────────────────┬──────────────┐")
	fmt.Println("  │ Валюта   │ Результат      │ Курс         │")
	fmt.Println("  ├──────────┼────────────────┼──────────────┤")
	color.Unset()
	for _, row := range rows {
		color.Green("  │ %-8s │ %-14.2f │ %-12.4f │", row.Currency, row.Result, row.Rate)
	}
	color.Set(color.FgYellow, color.Bold)
	fmt.Println("  └──────────┴────────────────┴──────────────┘")
	color.Unset()

	updateTime := time.Unix(rates.TimeLastUpdated, 0)
	timeAgo := formatTimeAgo(time.Since(updateTime))
	fmt.Println()
	color.HiBlack("  Последнее обновление: %s (%s)", updateTime.Format("2006-01-02 15:04:05"), timeAgo)
	fmt.Println()
}

// printResult выводит результат конвертации
func printResult(amount float64, from string, result float64, to string, rates *ExchangeRateResponse) {
	fmt.Println()
	color.Set(color.FgYellow, color.Bold)
	fmt.Println("════════════════ РЕЗУЛЬТАТ ════════════════")
	color.Unset()

	color.Green("%.2f %s = %.2f %s", amount, from, result, to)

	if rate, ok := rates.Rates[to]; ok {
		fmt.Println()
		color.Cyan("Курс: 1 %s = %.4f %s", from, rate, to)
	}

	// Вывод времени последнего обновления
	updateTime := time.Unix(rates.TimeLastUpdated, 0)
	timeAgo := formatTimeAgo(time.Since(updateTime))
	fmt.Println()
	color.HiBlack("Последнее обновление: %s (%s)", updateTime.Format("2006-01-02 15:04:05"), timeAgo)

	fmt.Println()
	color.Set(color.FgYellow, color.Bold)
	fmt.Println("═══════════════════════════════════════════")
	color.Unset()
}

// outputJSON выводит результат в формате JSON
func outputJSON(from, to string, amount, result, rate float64, updateTime time.Time) {
	output := JSONOutput{
		Success:        true,
		Timestamp:      time.Now(),
		FromCurrency:   from,
		ToCurrency:     to,
		Amount:         amount,
		Result:         result,
		ExchangeRate:   rate,
		RateUpdateTime: updateTime,
	}

	data, err := json.MarshalIndent(output, "", "  ")
	if err != nil {
		outputError(fmt.Sprintf("ошибка формирования JSON: %v", err), true)
		os.Exit(1)
	}

	fmt.Println(string(data))
}

// outputCSV выводит результат в формате CSV
func outputCSV(from, to string, amount, result, rate float64, _ time.Time) {
	// timestamp,from,to,amount,result,rate
	fmt.Printf("%s,%s,%s,%.2f,%.2f,%.6f\n",
		time.Now().Format(time.RFC3339),
		from,
		to,
		amount,
		result,
		rate,
	)
}

// outputError выводит ошибку в формате JSON или CSV
func outputError(message string, asJSON bool) {
	if asJSON {
		output := map[string]interface{}{
			"success": false,
			"error":   message,
		}
		data, _ := json.MarshalIndent(output, "", "  ")
		fmt.Println(string(data))
	} else {
		// CSV формат ошибки
		fmt.Printf("error,%s\n", message)
	}
}

// saveToHistory сохраняет запись в историю конвертаций
func saveToHistory(from, to string, amount, result, rate float64, updateTime time.Time) {
	record := ConversionRecord{
		Timestamp:      time.Now(),
		FromCurrency:   from,
		ToCurrency:     to,
		Amount:         amount,
		Result:         result,
		ExchangeRate:   rate,
		RateUpdateTime: updateTime,
	}

	// Читаем существующую историю
	var history []ConversionRecord
	data, err := os.ReadFile(historyFile)
	if err == nil {
		json.Unmarshal(data, &history)
	}

	// Добавляем новую запись
	history = append(history, record)

	// Сохраняем обратно
	data, err = json.MarshalIndent(history, "", "  ")
	if err != nil {
		return
	}

	os.WriteFile(historyFile, data, 0644)
}

// showHistory показывает историю конвертаций
func showHistory() {
	data, err := os.ReadFile(historyFile)
	if err != nil {
		color.Red("❌ История конвертаций пуста или файл не найден")
		return
	}

	var history []ConversionRecord
	err = json.Unmarshal(data, &history)
	if err != nil {
		color.Red("❌ Ошибка чтения файла истории: %v", err)
		return
	}

	if len(history) == 0 {
		color.Yellow("📝 История конвертаций пуста")
		return
	}

	color.Set(color.FgGreen, color.Bold)
	fmt.Println("╔════════════════════════════════════════╗")
	fmt.Println("║      ИСТОРИЯ КОНВЕРТАЦИЙ               ║")
	fmt.Println("╚════════════════════════════════════════╝")
	color.Unset()
	fmt.Println()

	for i := len(history) - 1; i >= 0; i-- {
		rec := history[i]
		color.Cyan("📅 %s", rec.Timestamp.Format("2006-01-02 15:04:05"))
		color.Green("   %.2f %s = %.2f %s", rec.Amount, rec.FromCurrency, rec.Result, rec.ToCurrency)
		color.HiBlack("   Курс: 1 %s = %.4f %s", rec.FromCurrency, rec.ExchangeRate, rec.ToCurrency)
		fmt.Println()
	}

	color.Set(color.FgYellow, color.Bold)
	fmt.Printf("Всего записей: %d\n", len(history))
	color.Unset()
}
