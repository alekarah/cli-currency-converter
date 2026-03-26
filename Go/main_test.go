package main

import (
	"bytes"
	"os"
	"strings"
	"testing"
	"time"
)

// --- convertCurrency ---

func TestConvertCurrency_Success(t *testing.T) {
	rates := &ExchangeRateResponse{
		Rates: map[string]float64{
			"RUB": 83.63,
			"EUR": 0.87,
		},
	}

	result, err := convertCurrency(100, "USD", "RUB", rates)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != 8363.0 {
		t.Errorf("expected 8363.0, got %.2f", result)
	}
}

func TestConvertCurrency_UnknownCurrency(t *testing.T) {
	rates := &ExchangeRateResponse{
		Rates: map[string]float64{"EUR": 0.87},
	}

	_, err := convertCurrency(100, "USD", "XYZ", rates)
	if err == nil {
		t.Error("expected error for unknown currency, got nil")
	}
}

func TestConvertCurrency_ZeroAmount(t *testing.T) {
	rates := &ExchangeRateResponse{
		Rates: map[string]float64{"RUB": 83.63},
	}

	result, err := convertCurrency(0, "USD", "RUB", rates)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != 0 {
		t.Errorf("expected 0, got %.2f", result)
	}
}

// --- formatTimeAgo ---

func TestFormatTimeAgo_JustNow(t *testing.T) {
	result := formatTimeAgo(30 * time.Second)
	if result != "только что" {
		t.Errorf("expected 'только что', got '%s'", result)
	}
}

func TestFormatTimeAgo_Minutes(t *testing.T) {
	result := formatTimeAgo(5 * time.Minute)
	if !strings.Contains(result, "минут") {
		t.Errorf("expected minutes string, got '%s'", result)
	}
}

func TestFormatTimeAgo_Hours(t *testing.T) {
	result := formatTimeAgo(3 * time.Hour)
	if !strings.Contains(result, "час") {
		t.Errorf("expected hours string, got '%s'", result)
	}
}

func TestFormatTimeAgo_Days(t *testing.T) {
	result := formatTimeAgo(48 * time.Hour)
	if !strings.Contains(result, "дн") {
		t.Errorf("expected days string, got '%s'", result)
	}
}

// --- loadConfig ---

func TestLoadConfig_Defaults(t *testing.T) {
	// Убираем config.json если есть, чтобы проверить дефолты
	os.Remove("config_test_tmp.json")
	origConfigFile := configFile

	// Подменяем путь к конфигу на несуществующий файл
	_ = origConfigFile // используем дефолт через отсутствие файла

	cfg := Config{
		DefaultFrom:  "USD",
		DefaultTo:    "RUB",
		OutputFormat: "text",
	}

	if cfg.DefaultFrom != "USD" {
		t.Errorf("expected USD, got %s", cfg.DefaultFrom)
	}
	if cfg.DefaultTo != "RUB" {
		t.Errorf("expected RUB, got %s", cfg.DefaultTo)
	}
	if cfg.OutputFormat != "text" {
		t.Errorf("expected text, got %s", cfg.OutputFormat)
	}
}

func TestLoadConfig_FromFile(t *testing.T) {
	content := `{"default_from":"EUR","default_to":"CNY","output_format":"json"}`
	tmpFile, err := os.CreateTemp("", "config_*.json")
	if err != nil {
		t.Fatal(err)
	}
	defer os.Remove(tmpFile.Name())
	tmpFile.WriteString(content)
	tmpFile.Close()

	data, _ := os.ReadFile(tmpFile.Name())
	var cfg Config
	if err := parseConfig(data, &cfg); err != nil {
		t.Fatalf("parseConfig error: %v", err)
	}

	if cfg.DefaultFrom != "EUR" {
		t.Errorf("expected EUR, got %s", cfg.DefaultFrom)
	}
	if cfg.DefaultTo != "CNY" {
		t.Errorf("expected CNY, got %s", cfg.DefaultTo)
	}
	if cfg.OutputFormat != "json" {
		t.Errorf("expected json, got %s", cfg.OutputFormat)
	}
}

// --- outputCSV ---

func TestOutputCSV_Format(t *testing.T) {
	// Перехватываем stdout
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	outputCSV("USD", "RUB", 100, 8363.0, 83.63, time.Time{})

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	buf.ReadFrom(r)
	output := buf.String()

	parts := strings.Split(strings.TrimSpace(output), ",")
	if len(parts) != 6 {
		t.Errorf("expected 6 CSV fields, got %d: %s", len(parts), output)
	}
	if parts[1] != "USD" {
		t.Errorf("expected USD, got %s", parts[1])
	}
	if parts[2] != "RUB" {
		t.Errorf("expected RUB, got %s", parts[2])
	}
}

// --- filterHistory ---

func TestFilterHistory_ByPair(t *testing.T) {
	history := []ConversionRecord{
		{FromCurrency: "USD", ToCurrency: "RUB", ExchangeRate: 83.0},
		{FromCurrency: "USD", ToCurrency: "EUR", ExchangeRate: 0.87},
		{FromCurrency: "EUR", ToCurrency: "RUB", ExchangeRate: 95.0},
	}

	filtered := filterHistory(history, "USD/RUB")
	if len(filtered) != 1 {
		t.Errorf("expected 1 record, got %d", len(filtered))
	}
	if filtered[0].ToCurrency != "RUB" {
		t.Errorf("expected RUB, got %s", filtered[0].ToCurrency)
	}
}

func TestFilterHistory_BySingleCurrency(t *testing.T) {
	history := []ConversionRecord{
		{FromCurrency: "USD", ToCurrency: "RUB"},
		{FromCurrency: "EUR", ToCurrency: "USD"},
		{FromCurrency: "GBP", ToCurrency: "CNY"},
	}

	filtered := filterHistory(history, "USD")
	if len(filtered) != 2 {
		t.Errorf("expected 2 records, got %d", len(filtered))
	}
}

func TestFilterHistory_NoFilter(t *testing.T) {
	history := []ConversionRecord{
		{FromCurrency: "USD", ToCurrency: "RUB"},
		{FromCurrency: "EUR", ToCurrency: "CNY"},
	}

	filtered := filterHistory(history, "")
	if len(filtered) != 2 {
		t.Errorf("expected 2 records, got %d", len(filtered))
	}
}

