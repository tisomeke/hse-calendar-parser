# 📖 Как пользоваться HSE Schedule Parser

> Для тех, кто никогда не открывал «чёрное окно»

---

## 🎯 Что происходит

**Было:** вуз скидывает расписание в таблице Excel, смотреть неудобно  
**Стало:** пары появляются в телефоне как обычные события календаря

---

## 🔧 ЧАСТЬ 1. Установка (один раз)

---

### 🪟 Для Windows

#### Шаг 1.1. Установи Python

1. Открой браузер → [python.org/downloads](https://www.python.org/downloads/)
2. Нажми жёлтую кнопку **Download Python 3.13**
3. Открой скачанный файл
4. **ВАЖНО:** внизу окна поставь галочку ☑️ **Add python.exe to PATH**
5. Нажми **Install Now** → жди → **Close**

#### Шаг 1.2. Скачай программу

1. Открой [github.com/tisomeke/hse-calendar-parser](https://github.com/tisomeke/hse-calendar-parser)
2. Нажми зелёную кнопку **<> Code** → **Download ZIP**
3. Распакуй ZIP на **Рабочий стол**
4. У тебя появится папка `hse-calendar-parser-main`

#### Шаг 1.3. Открой PowerShell

1. Нажми **Win + S** (иконка лупы слева внизу)
2. Напиши `powershell`
3. Нажми **Windows PowerShell** — откроется чёрное окно

#### Шаг 1.4. Установи программу

В чёрном окне (где мигает курсор) вводи команды **по очереди**. После каждой — **Enter**.

**Команда 1** — перейти на Рабочий стол:
```powershell
cd Desktop
```

**Команда 2** — перейти в папку программы:
```powershell
cd hse-calendar-parser-main
```

**Команда 3** — проверить Python:
```powershell
python --version
```
> Должно показать `Python 3.13.x`. Если ошибка — вернись к Шагу 1.1, проверь галочку.

**Команда 4** — установить:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Жди. Последняя строка: `Successfully installed ...` — готово! Окно можно закрыть.

---

### 🍎 Для Mac

#### Шаг 1.1. Установи Python

1. Открой браузер → [python.org/downloads](https://www.python.org/downloads/)
2. Нажми жёлтую кнопку **Download Python 3.13**
3. Открой скачанный файл `.pkg`
4. Нажми **Продолжить** → **Продолжить** → **Согласен** → **Установить**
5. Введи пароль компьютера (если спросит) → жди → **Закрыть**

#### Шаг 1.2. Скачай программу

1. Открой [github.com/tisomeke/hse-calendar-parser](https://github.com/tisomeke/hse-calendar-parser)
2. Нажми зелёную кнопку **<> Code** → **Download ZIP**
3. Распакуй ZIP (двойной клик) — папка `hse-calendar-parser-main` в **Downloads**

#### Шаг 1.3. Открой Терминал

1. Нажми **Cmd + Пробел**
2. Напиши `terminal`
3. Нажми **Enter** — откроется окно

#### Шаг 1.4. Установи программу

В окне Терминала вводи команды **по очереди**. После каждой — **Enter**.

**Команда 1** — перейти в папку:
```bash
cd ~/Downloads/hse-calendar-parser-main
```

**Команда 2** — проверить Python:
```bash
python3 --version
```
> Должно показать `Python 3.13.x`. Если ошибка — вернись к Шагу 1.1.

**Команда 3** — установить:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Жди. Последняя строка: `Successfully installed ...` — готово! Окно можно закрыть.

---

## 🚀 ЧАСТЬ 2. Запуск (каждый раз при новом расписании)

---

### 🪟 Для Windows

1. Положи файл `.xlsx` с расписанием в папку `hse-calendar-parser-main` на **Рабочем столе**
2. Открой **PowerShell** (**Win + S** → `powershell` → **Enter**)
3. Введи три команды:

```powershell
cd Desktop
cd hse-calendar-parser-main
.venv\Scripts\python -m hse_schedule_parser
```

---

### 🍎 Для Mac

1. Положи файл `.xlsx` с расписанием в папку `hse-calendar-parser-main` в **Downloads**
2. Открой **Терминал** (**Cmd + Пробел** → `terminal` → **Enter**)
3. Введи две команды:

```bash
cd ~/Downloads/hse-calendar-parser-main
.venv/bin/python3 -m hse_schedule_parser
```

---

## 🎮 ЧАСТЬ 3. Мастер

Откроется меню в том же окне:

```
📁 Шаг 1/5: Выбор файла
Найден файл: 1_курс_2_модуль.xlsx
[1] Использовать найденный файл
[2] Указать другой путь
```

- **Стрелки ↑↓** — выбор
- **Enter** — подтвердить
- **Пробел** — галочка
- **Q** — выйти

Читай и отвечай. Можно вернуться назад.

---

## 📱 ЧАСТЬ 4. Импорт в календарь

Файл `schedule_25ФПЛ1.ics` появится в папке с программой.

**iPhone / iPad:** отправь файл в **Telegram** → открой на телефоне → **Добавить в Календарь**

**Android:** **Google Calendar** → Настройки → Импорт → выбери файл

**Компьютер:** [calendar.google.com](https://calendar.google.com) → **+** рядом с «Другие календари» → **Импортировать** → выбери файл

---

## 🆘 ЧАСТЬ 5. Проблемы

| Проблема | Решение |
|----------|---------|
| «python не найден» | Переустанови Python, проверь галочку «Add to PATH» (Windows) или используй `python3` (Mac) |
| «No module named rich» | Забыл установку — вернись к Части 1 |
| «Файл не найден» | Положи `.xlsx` в папку программы |
| Не понятно | Сделай скриншот окна и [создай issue](https://github.com/tisomeke/hse-calendar-parser/issues) |

---

## 📝 Шпаргалка

**Windows:**
```powershell
cd Desktop
cd hse-calendar-parser-main
.venv\Scripts\python -m hse_schedule_parser
```

**Mac:**
```bash
cd ~/Downloads/hse-calendar-parser-main
.venv/bin/python3 -m hse_schedule_parser
```
