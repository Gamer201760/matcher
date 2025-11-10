# Интерактивный CLI для Системы Подбора Соседей / Interactive CLI for Roommate Matching System

## Содержание / Table of Contents

### [🇷🇺 Русская версия](#русская-версия-1)
- [Обзор CLI](#обзор-cli)
- [Как это работает](#как-это-работает)
- [Возможности](#возможности)
- [Файлы CLI](#файлы-cli)
- [Установка и запуск](#установка-и-запуск)
- [Рабочий процесс](#рабочий-процесс)

### [🇺🇸 English Version](#english-version-1)
- [CLI Overview](#cli-overview)
- [How It Works](#how-it-works)
- [Features](#features)
- [CLI Files](#cli-files)
- [Installation and Usage](#installation-and-usage)
- [Workflow](#workflow)

---

# 🇷🇺 Русская версия

## Обзор CLI

Интерактивный интерфейс командной строки для системы подбора соседей по комнате. Построен с использованием `questionary` (навигация) и `rich` (форматированный вывод). Предоставляет полный набор функций для работы с системой рекомендаций.

## Как это работает

### Расчёт рекомендаций
Рекомендации вычисляются с использованием **Евклидова расстояния** на нормализованных 4-мерных векторах:
1. Параметры пользователя (комнаты, соседи, бюджет, месяцы) нормализуются в диапазон [0,1]
2. Применяются веса (rooms: 8.0, roommates: 8.0, budget: 2.8, months: 1.2)
3. Neo4j выполняет векторный поиск по индексу `group_vec_index`
4. Возвращаются топ-N наиболее похожих групп

**Важно**: Рекомендации рассчитываются **один раз** при выборе "Get Recommendations" или "Join a Group" и кэшируются до возврата в главное меню.

### Вступление в группу
При вступлении пользователя в группу:
1. Показывается таблица со всеми участниками и их параметрами
2. Пользователь подтверждает вступление или возвращается к рекомендациям
3. При подтверждении параметры группы **пересчитываются** как среднее всех участников
4. Векторное представление группы обновляется в Neo4j

### Адаптивное меню
Опции меню изменяются в зависимости от состояния пользователя:
- **В группе**: "Join a Group" скрыта
- **Соло**: "Join a Group" доступна

## Возможности

- 🔍 **Получить рекомендации** - Найти похожие группы (Евклидово расстояние)
- 🤝 **Вступить в группу** - Просмотр участников, подтверждение, пересчёт параметров
- 🚪 **Покинуть группу** - Выход с созданием одно-пользовательской группы
- 👁️ **Просмотр группы** - Детали текущей группы с таблицей участников
- 🌳 **Дерево групп** - Визуализация всех групп (как команда `tree` в Linux)
- 👤 **Сменить пользователя** - Переключение между пользователями
- ➕ **Создать пользователя** - Вручную или случайно
- 📊 **Статистика** - Информация о базе данных
- 🧹 **Очистить БД** - Сброс базы данных

## Файлы CLI

```
cli/
├── __init__.py       # Инициализация пакета, экспорт run()
├── main.py           # Точка входа, инициализация Neo4j
├── menus.py          # Главное меню, навигация, выбор пользователя
├── actions.py        # Обработчики действий (рекомендации, вступление, выход)
├── displays.py       # Форматирование вывода (rich: таблицы, деревья, панели)
└── utils.py          # Генерация пользователей, вспомогательные функции
```

### Ключевые компоненты

**main.py** - Инициализация:
```python
- Загрузка .env
- Подключение к Neo4j
- Создание индексов и ограничений
- Запуск startup_menu() → main_menu()
```

**menus.py** - Навигация:
```python
- startup_menu(): Очистка БД, создание/выбор пользователя
- main_menu(): Главный цикл, адаптивные опции меню
- select_user_with_details(): Выбор пользователя с параметрами
```

**actions.py** - Логика действий:
```python
- action_get_recommendations(): Векторный поиск, отображение
- action_join_group(): Рекомендации → Превью участников → Вступление
- action_leave_group(): Подтверждение → Выход → Создание новой группы
```

**displays.py** - Визуализация (rich):
```python
- display_recommendations(): Таблица с разницей параметров
- display_group_tree(): Древовидная структура групп
- display_group_details(): Панель с информацией о группе
- round_for_display(): Округление для отображения (ceil по умолчанию)
```

## Установка и запуск

### Установка зависимостей

```bash
pip install -r repository/recommendation_system/requirements.txt
```

Или вручную:
```bash
pip install questionary rich neo4j python-dotenv
```

### Запуск

**Способ 1: Через convenience скрипт (рекомендуется)**
```bash
python run_cli.py
```

**Способ 2: Как модуль Python**
```bash
python -m repository.recommendation_system.cli.main
```

**Способ 3: Прямой запуск**
```bash
python repository/recommendation_system/cli/main.py
```

**Примечание**: Убедитесь, что виртуальное окружение активировано и `.env` файл настроен с `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.

## Рабочий процесс

### 1. Запуск и инициализация
```
Запуск → Подключение к Neo4j → Создание индексов
```

### 2. Startup меню
```
"Очистить БД?" → Yes/No
├─ Yes: Очистка → Создание sample пользователей (35) → Группировка
└─ No: Переход к выбору пользователя
```

### 3. Выбор пользователя
```
Список пользователей с параметрами и статусом группы
├─ ➕ Create New User (сверху списка)
└─ Имя — rooms:X rm:Y ₽Z/mo Nmo — in group/solo
```

### 4. Главное меню
```
Current User: Имя (user_id)

🏠 Roommate Matcher - Main Menu
├─ 🔍 Get Recommendations (векторный поиск)
├─ 🤝 Join a Group (если не в группе)
├─ 🚪 Leave My Group
├─ 👁️ View My Group
└─ ... другие опции
```

### 5. Процесс вступления в группу
```
Join a Group → Рекомендации отображены
  ↓
Выбор группы → Таблица участников с параметрами
  ↓
"Join this group" / "Go back to recommendations"
  ↓
Вступление → Пересчёт параметров группы → Обновление вектора
```

### 6. Управление группами
- **Вступление**: Параметры группы = среднее всех участников
- **Выход**: Создаётся новая группа с ID = user_id только для этого пользователя
- **Просмотр**: Таблица участников + средние параметры

## Навигация

- **↑/↓**: Перемещение по опциям
- **Enter**: Подтверждение выбора
- **Ctrl+C**: Отмена текущей операции

## Конфигурация отображения

Настройки в `config.py`:

```python
# Округление при отображении (не влияет на расчёты)
DISPLAY_ROUNDING_MODE = 'ceil'  # 'ceil', 'floor', 'round', None

# Количество групп в дереве
DEFAULT_TREE_MAX_GROUPS = 50

# Количество рекомендаций
DEFAULT_RECOMMENDATION_COUNT = 10
```

---

# 🇺🇸 English Version

## CLI Overview

An interactive command-line interface for the roommate matching system. Built with `questionary` (navigation) and `rich` (formatted output). Provides full access to the recommendation system's features.

## How It Works

### Recommendation Calculation
Recommendations are computed using **Euclidean distance** on normalized 4D vectors:
1. User parameters (rooms, roommates, budget, months) are normalized to [0,1] range
2. Weights are applied (rooms: 8.0, roommates: 8.0, budget: 2.8, months: 1.2)
3. Neo4j performs vector search on `group_vec_index`
4. Top-N most similar groups are returned

**Important**: Recommendations are calculated **once** when selecting "Get Recommendations" or "Join a Group" and cached until returning to main menu.

### Joining a Group
When a user joins a group:
1. A table displays all members with their parameters
2. User confirms joining or goes back to recommendations
3. On confirmation, group parameters are **recalculated** as the average of all members
4. Group's vector representation is updated in Neo4j

### Adaptive Menu
Menu options change based on user state:
- **In a group**: "Join a Group" is hidden
- **Solo**: "Join a Group" is available

## Features

- 🔍 **Get Recommendations** - Find similar groups (Euclidean distance)
- 🤝 **Join a Group** - View members, confirm, recalculate parameters
- 🚪 **Leave Group** - Exit with single-member group creation
- 👁️ **View My Group** - Current group details with member table
- 🌳 **View All Groups (Tree)** - Visualize all groups (like Linux `tree`)
- 👤 **Switch User** - Change between users
- ➕ **Create New User** - Manual or randomized
- 📊 **View Statistics** - Database information
- 🧹 **Clean Database** - Reset database

## CLI Files

```
cli/
├── __init__.py       # Package init, exports run()
├── main.py           # Entry point, Neo4j initialization
├── menus.py          # Main menu, navigation, user selection
├── actions.py        # Action handlers (recommendations, join, leave)
├── displays.py       # Output formatting (rich: tables, trees, panels)
└── utils.py          # User generation, helper functions
```

### Key Components

**main.py** - Initialization:
```python
- Load .env
- Connect to Neo4j
- Create indexes and constraints
- Run startup_menu() → main_menu()
```

**menus.py** - Navigation:
```python
- startup_menu(): DB cleanup, user creation/selection
- main_menu(): Main loop, adaptive menu options
- select_user_with_details(): User selection with parameters
```

**actions.py** - Action Logic:
```python
- action_get_recommendations(): Vector search, display
- action_join_group(): Recommendations → Member preview → Join
- action_leave_group(): Confirm → Leave → New group creation
```

**displays.py** - Visualization (rich):
```python
- display_recommendations(): Table with parameter differences
- display_group_tree(): Tree structure of groups
- display_group_details(): Panel with group information
- round_for_display(): Rounding for display (ceil by default)
```

## Installation and Usage

### Install Dependencies

```bash
pip install -r repository/recommendation_system/requirements.txt
```

Or manually:
```bash
pip install questionary rich neo4j python-dotenv
```

### Running

**Method 1: Via convenience script (recommended)**
```bash
python run_cli.py
```

**Method 2: As Python module**
```bash
python -m repository.recommendation_system.cli.main
```

**Method 3: Direct execution**
```bash
python repository/recommendation_system/cli/main.py
```

**Note**: Ensure virtual environment is activated and `.env` file is configured with `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.

## Workflow

### 1. Startup and Initialization
```
Launch → Connect to Neo4j → Create indexes
```

### 2. Startup Menu
```
"Clean database?" → Yes/No
├─ Yes: Clean → Create sample users (35) → Group them
└─ No: Proceed to user selection
```

### 3. User Selection
```
List of users with parameters and group status
├─ ➕ Create New User (at top)
└─ Name — rooms:X rm:Y ₽Z/mo Nmo — in group/solo
```

### 4. Main Menu
```
Current User: Name (user_id)

🏠 Roommate Matcher - Main Menu
├─ 🔍 Get Recommendations (vector search)
├─ 🤝 Join a Group (if not in group)
├─ 🚪 Leave My Group
├─ 👁️ View My Group
└─ ... other options
```

### 5. Group Joining Process
```
Join a Group → Recommendations displayed
  ↓
Select group → Member table with parameters
  ↓
"Join this group" / "Go back to recommendations"
  ↓
Join → Recalculate group parameters → Update vector
```

### 6. Group Management
- **Joining**: Group parameters = average of all members
- **Leaving**: New group with ID = user_id created for that user only
- **Viewing**: Member table + average parameters

## Navigation

- **↑/↓**: Move through options
- **Enter**: Confirm selection
- **Ctrl+C**: Cancel current operation

## Display Configuration

Settings in `config.py`:

```python
# Rounding for display (doesn't affect calculations)
DISPLAY_ROUNDING_MODE = 'ceil'  # 'ceil', 'floor', 'round', None

# Number of groups in tree
DEFAULT_TREE_MAX_GROUPS = 50

# Number of recommendations
DEFAULT_RECOMMENDATION_COUNT = 10
```
