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

const (
	apiURL = "https://api.exchangerate-api.com/v4/latest/"
)

func main() {
	printHeader()

	// Получаем параметры из командной строки или интерактивно
	var fromCurrency, toCurrency string
	var amount float64

	if len(os.Args) == 4 {
		// Режим с аргументами командной строки
		fromCurrency = strings.ToUpper(os.Args[1])
		toCurrency = strings.ToUpper(os.Args[2])
		var err error
		amount, err = strconv.ParseFloat(os.Args[3], 64)
		if err != nil {
			color.Red("❌ Ошибка: неверная сумма")
			os.Exit(1)
		}
	} else {
		// Интерактивный режим
		fromCurrency = getInput("Введите исходную валюту (например, USD): ")
		toCurrency = getInput("Введите целевую валюту (например, RUB): ")
		amount = getAmount("Введите сумму для конвертации: ")
	}

	// Получаем курсы валют
	color.Cyan("🔄 Загрузка актуальных курсов валют...")
	rates, err := getExchangeRates(fromCurrency)
	if err != nil {
		color.Red("❌ Ошибка при получении курсов: %v", err)
		os.Exit(1)
	}

	// Выполняем конвертацию
	result, err := convertCurrency(amount, fromCurrency, toCurrency, rates)
	if err != nil {
		color.Red("❌ Ошибка конвертации: %v", err)
		os.Exit(1)
	}

	// Выводим результат
	printResult(amount, fromCurrency, result, toCurrency, rates)
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

// getExchangeRates получает курсы валют из API
func getExchangeRates(baseCurrency string) (*ExchangeRateResponse, error) {
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
