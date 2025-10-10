# Система Рекомендаций Соседей по Комнате / Roommate Recommendation System

## Содержание / Table of Contents

### [🇷🇺 Русская версия](#русская-версия)
- [Обзор системы](#обзор-системы)
- [Архитектура](#архитектура)
- [Файлы системы](#файлы-системы)
- [Конфигурация](#конфигурация)
- [Функции по файлам](#функции-по-файлам)
- [Результаты тестирования](#результаты-тестирования)
- [Известные проблемы](#известные-проблемы)

### [🇬🇧 English Version](#english-version)
- [System Overview](#system-overview)
- [Architecture](#architecture)
- [System Files](#system-files)
- [Configuration](#configuration)
- [Functions by File](#functions-by-file)
- [Testing Results](#testing-results)
- [Known Issues](#known-issues)

---

# 🇷🇺 Русская версия

## Обзор системы

Система рекомендаций соседей по комнате - это векторный поисковый движок на основе Neo4j для подбора совместимых соседей. Использует **Евклидово расстояние** для вычисления схожести между векторами предпочтений пользователей.

### Принцип работы

1. **Регистрация пользователя** → Создаётся профиль с параметрами (комнаты, соседи, бюджет, срок)
2. **Векторизация** → Параметры нормализуются в 4-мерный вектор [0,1]
3. **Взвешивание** → Применяются веса (комнаты: 1.0, соседи: 1.0, бюджет: 0.35, срок: 0.15) × множитель (10)
4. **Векторный поиск** → Neo4j находит похожие группы через Евклидово расстояние
5. **Формирование групп** → Пользователи объединяются, параметры группы усредняются
6. **Управление** → Запросы на вступление, одобрение, выход из групп

### Ключевые параметры

- **rooms** (комнаты): 1-4, нормализация cap=10, базовый вес=1.0 → финальный вес=10.0
- **roommates** (соседи): 0-5, нормализация cap=10, базовый вес=1.0 → финальный вес=10.0
- **budget** (бюджет): ₽5,000-60,000, нормализация cap=200,000, базовый вес=0.35 → финальный вес=3.5
- **months** (месяцы): 3-36, нормализация cap=36, базовый вес=0.15 → финальный вес=1.5

**Множитель весов**: 10 (настраивается в `config.py` → `WEIGHT_MULTIPLIER`)

## Архитектура

```
┌─────────────────┐
│   service.py    │  ← API слой (RecommendationService)
└────────┬────────┘
         │
┌────────▼────────────────────────────────────┐
│     db_management_utils.py                  │  ← Логика БД
│  • Управление пользователями/группами      │
│  • Векторный поиск                         │
│  • Neo4j запросы                           │
└────────┬────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────┐
│     user_vector_utils.py                    │  ← Векторная математика
│  • Нормализация параметров                 │
│  • Создание векторов                       │
│  • Евклидово расстояние                    │
└─────────────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────┐
│         Neo4j Database                      │
│  Узлы: User, Group, Parameter              │
│  Индексы: Векторный (Euclidean)            │
└─────────────────────────────────────────────┘
```

## Файлы системы

### 1. **config.py** - Конфигурация системы
Центральный файл конфигурации со всеми константами: параметры, веса, множитель, настройки БД и симуляции.

### 2. **service.py** - API Сервис
Высокоуровневый API для работы с системой. Предоставляет методы создания профилей, поиска похожих пользователей, управления группами.

### 3. **db_management_utils.py** - Управление БД
Основная логика работы с Neo4j: CRUD операции, векторный поиск, управление группами, симуляция формирования групп.

### 4. **user_vector_utils.py** - Векторная математика
Нормализация параметров, создание векторов с весами, вычисление Евклидова расстояния.

### 5. **logging_utils.py** - Логирование
Структурированное логирование запросов Neo4j, векторных операций, результатов поиска, статистики БД.

### 6. **simulation.py** - Интерактивная симуляция
Инструмент для тестирования: генерация пользователей, интерактивная регистрация, поиск групп, вступление/выход.

## Конфигурация

Все константы системы хранятся в `config.py` для удобной настройки:

### Параметры базы данных
- **PARAMETERS**: `['rooms', 'roommates', 'budget', 'months']` - параметры для сопоставления
- **VECTOR_DIMENSIONS**: `4` - размерность векторов
- **SIMILARITY_FUNCTION**: `'euclidean'` - функция схожести (cosine/euclidean)

### Нормализация
- **DEFAULT_CAPS**: Границы нормализации для всех параметров
  - `rooms`: 10 - максимум комнат
  - `roommates`: 10 - максимум соседей
  - `budget`: 200,000 ₽ - максимальный бюджет
  - `months`: 36 месяцев - максимальный срок

### Веса и множитель
- **WEIGHT_MULTIPLIER**: `10` - множитель для усиления чувствительности
- **BASE_WEIGHTS**: Базовые веса (до множителя)
  - `rooms`: 1.0
  - `roommates`: 1.0
  - `budget`: 0.35
  - `months`: 0.15
- **GROUP_PARAMETER_WEIGHTS**: Финальные веса (базовые × множитель)
  - `rooms`: 10.0
  - `roommates`: 10.0
  - `budget`: 3.5
  - `months`: 1.5

### Настройки поиска
- **DEFAULT_TOP_K**: `5` - количество рекомендаций по умолчанию
- **DEFAULT_MAX_ROOMMATES**: `4` - максимум участников в группе
- **AUTO_DEACTIVATE_FULL_GROUPS**: `True` - автодеактивация заполненных групп

### Настройки симуляции
- **DEFAULT_FAKE_USER_COUNT**: `20` - количество тестовых пользователей
- **FAKE_USER_BUDGET_RANGE**: `(5000, 60000)` - диапазон бюджета
- **FAKE_USER_MONTHS_OPTIONS**: `[3, 6, 9, 12, 18, 24, 36]` - варианты срока

### Логирование
- **DEFAULT_LOG_LEVEL**: `'INFO'` - уровень логирования по умолчанию
- **MODULE_LOG_LEVELS**: Уровни для конкретных модулей

## Функции по файлам

### config.py

#### Константы
**Назначение**: Центральное хранилище всех настроек системы  
**Использование**: Импортируется всеми модулями для консистентности

**Основные константы**:
- `PARAMETERS` - список параметров для векторизации
- `WEIGHT_MULTIPLIER` - множитель весов (влияет на чувствительность)
- `GROUP_PARAMETER_WEIGHTS` - финальные веса параметров
- `SIMILARITY_FUNCTION` - используемая метрика ('euclidean' или 'cosine')
- `DEFAULT_CAPS` - границы нормализации параметров
- Настройки симуляции и логирования

### service.py

#### Класс RecommendationService
**Назначение**: API интерфейс для управления профилями и группами  
**Использование**: Основной класс для взаимодействия с системой

- **`__init__(caps, use_weights, weights)`**
  - Назначение: Инициализация сервиса с настройками векторизации
  - Использование: Создание экземпляра сервиса при запуске приложения

- **`create_form(user_id, form)`**
  - Назначение: Создание профиля пользователя
  - Использование: Регистрация нового пользователя в системе

- **`get_form(user_id)`**
  - Назначение: Получение профиля пользователя
  - Использование: Отображение данных профиля

- **`get_similar(user_id, top_k)`**
  - Назначение: Поиск похожих пользователей
  - Использование: Получение рекомендаций для пользователя

- **`update_form(user_id, form)`**
  - Назначение: Обновление профиля
  - Использование: Изменение предпочтений пользователя

- **`delete_form(user_id)`**
  - Назначение: Удаление профиля
  - Использование: Удаление пользователя из системы

- **`send_request_to_group(user_id, group_id)`**
  - Назначение: Отправка запроса на вступление в группу
  - Использование: Пользователь хочет присоединиться к группе

- **`approve_request(group_member_user_id, user_id, max_roommates)`**
  - Назначение: Одобрение запроса на вступление
  - Использование: Участник группы одобряет нового участника

- **`leave_from_group(user_id)`**
  - Назначение: Выход из группы
  - Использование: Пользователь покидает текущую группу
  - ⚠️ **ПРОБЛЕМА**: Ошибка параметров Neo4j (см. Известные проблемы)

- **`get_group(group_id)`**
  - Назначение: Получение информации о группе
  - Использование: Просмотр состава и статуса группы

### db_management_utils.py

#### Основные функции

- **`get_driver(uri, user, password)`**
  - Назначение: Создание драйвера Neo4j
  - Использование: Подключение к БД при каждой операции

- **`ensure_constraints_and_index(session, dims)`**
  - Назначение: Создание ограничений и векторных индексов
  - Использование: Инициализация схемы БД при первом запуске

- **`clear_users(session)`**
  - Назначение: Очистка всех пользователей и групп
  - Использование: Подготовка БД перед тестами

- **`upsert_users(session, users, caps, use_weights, weights)`**
  - Назначение: Создание/обновление пользователей и групп
  - Использование: Сохранение пользователей в БД

- **`find_similar(session, vector, top_k, exclude_id)`**
  - Назначение: Векторный поиск похожих групп через Neo4j
  - Использование: Получение рекомендаций (основной метод)

- **`find_similar_local(users, query_user, caps, use_weights, weights, top_k)`**
  - Назначение: Локальный поиск похожих групп
  - Использование: Fallback при недоступности Neo4j

- **`add_user_to_group(session, user_id, target_group_id, caps, use_weights, weights)`**
  - Назначение: Добавление пользователя в группу
  - Использование: Объединение пользователей при одобрении запроса

- **`remove_user_from_group(session, user_id, caps, use_weights, weights)`**
  - Назначение: Удаление пользователя из группы
  - Использование: Выход из группы
  - ⚠️ **ПРОБЛЕМА**: Ошибка параметров в Cypher запросе

- **`get_group_info(session, group_id)`**
  - Назначение: Получение полной информации о группе
  - Использование: Отображение деталей группы

- **`get_user_form(session, user_id)`**
  - Назначение: Получение данных формы пользователя
  - Использование: API метод get_form

- **`delete_user_form(session, user_id)`**
  - Назначение: Удаление пользователя и связанных данных
  - Использование: API метод delete_form

- **`send_join_request(session, user_id, group_id)`**
  - Назначение: Создание JOIN_REQUEST связи
  - Использование: Запрос на вступление в группу

- **`approve_join_request(session, group_member_user_id, user_id, max_roommates, caps, use_weights, weights)`**
  - Назначение: Одобрение запроса и добавление в группу
  - Использование: Обработка одобрения запроса

- **`get_group_with_status(session, group_id)`**
  - Назначение: Получение группы со статусом активности
  - Использование: Проверка, можно ли присоединиться к группе

- **`find_similar_users(session, user_id, top_k, caps, use_weights, weights)`**
  - Назначение: Поиск похожих пользователей (обёртка)
  - Использование: API метод get_similar

- **`get_user_parameters(session, user_id)`**
  - Назначение: Получение параметров из Parameter узлов
  - Использование: Внутренний метод для расчёта векторов

- **`get_group_member_parameters(session, group_id, exclude_user_id)`**
  - Назначение: Получение параметров всех участников группы
  - Использование: Расчёт средних значений группы

- **`clean_db()`**
  - Назначение: Полная очистка БД (с подтверждением)
  - Использование: Сброс БД в начальное состояние

- **`check_neo4j_connection()`**
  - Назначение: Проверка подключения к Neo4j
  - Использование: Диагностика при старте

- **`build_test_db_and_find_recommendations(...)`**
  - Назначение: Построение тестовой БД и поиск рекомендаций
  - Использование: Тестирование и демонстрация системы

### user_vector_utils.py

#### Функции нормализации

- **`normalize_rooms(x, cap=10)`**
  - Назначение: Нормализация количества комнат в [0,1]
  - Использование: Векторизация параметра rooms

- **`normalize_roommates(x, cap=10)`**
  - Назначение: Нормализация количества соседей в [0,1]
  - Использование: Векторизация параметра roommates

- **`normalize_budget(x, cap=200000)`**
  - Назначение: Нормализация бюджета в [0,1]
  - Использование: Векторизация параметра budget

- **`normalize_months(x, cap=36)`**
  - Назначение: Нормализация срока аренды в [0,1]
  - Использование: Векторизация параметра months

#### Функции векторизации

- **`create_user_vector(user, parameters, caps)`**
  - Назначение: Создание невзвешенного вектора
  - Использование: Базовая векторизация предпочтений

- **`create_group_vector_with_weights(values, parameters, weights, caps)`**
  - Назначение: Создание взвешенного вектора для группы
  - Использование: Векторизация с приоритизацией параметров

#### Функции расстояния

- **`euclidean_distance(vec1, vec2)`**
  - Назначение: Вычисление Евклидова расстояния
  - Использование: Расчёт схожести между векторами (основной метод)
  - **Замечание**: Заменил cosine_distance для большей чувствительности

### simulation.py

#### Функции генерации

- **`generate_fake_users(count)`**
  - Назначение: Генерация случайных тестовых пользователей
  - Использование: Наполнение БД для тестирования

- **`sample_users()`**
  - Назначение: Создание предопределённого набора 35 пользователей
  - Использование: Консистентное тестирование

#### Функции взаимодействия

- **`create_form()`**
  - Назначение: Интерактивный ввод данных пользователя
  - Использование: Регистрация через консоль

- **`get_similar_groups(session, user_data, top_k, caps, use_weights, weights)`**
  - Назначение: Поиск похожих групп для пользователя
  - Использование: Получение рекомендаций в симуляции

- **`display_group_recommendations(session, recommendations)`**
  - Назначение: Отображение рекомендованных групп
  - Использование: Вывод результатов поиска

- **`join_group_interactive(session, user_id, recommendations, caps, use_weights, weights)`**
  - Назначение: Интерактивное вступление в группу
  - Использование: Выбор группы и автоматическое одобрение

- **`leave_group_interactive(session, user_id, caps, use_weights, weights)`**
  - Назначение: Интерактивный выход из группы
  - Использование: Запрос подтверждения и выход

#### Функции симуляции

- **`simulate_group_formation(session, max_iterations, max_roommates_per_group, caps, use_weights, weights, verbose)`**
  - Назначение: Автоматическая симуляция формирования групп
  - Использование: Тестирование алгоритма подбора

- **`run_interactive_simulation(fake_user_count)`**
  - Назначение: Запуск полной интерактивной симуляции
  - Использование: Главная функция для тестирования

### logging_utils.py

- **`setup_logger(name, level)`**
  - Назначение: Настройка логгера с форматированием
  - Использование: Инициализация логирования в модулях

- **`log_neo4j_query(logger, query, params)`**
  - Назначение: Логирование Cypher запросов
  - Использование: Отладка запросов к БД

- **`log_vector_operation(logger, operation, vector_size, entity_id)`**
  - Назначение: Логирование векторных операций
  - Использование: Трассировка создания векторов

- **`log_similarity_results(logger, query_id, results, top_k)`**
  - Назначение: Логирование результатов поиска
  - Использование: Анализ рекомендаций

- **`log_database_stats(logger, stats)`**
  - Назначение: Логирование статистики БД
  - Использование: Мониторинг операций

## Результаты тестирования

### Статистика
- **Всего тестов**: 12
- **Успешно**: 10 ✅
- **Ошибки**: 2 ❌

### Успешные тесты

1. ✅ `test_01_create_form` - Создание профиля пользователя
2. ✅ `test_02_get_form` - Получение профиля пользователя
3. ✅ `test_03_get_form_not_found` - Обработка несуществующего профиля
4. ✅ `test_04_update_form` - Обновление профиля
5. ✅ `test_05_delete_form` - Удаление профиля
6. ✅ `test_06_get_similar` - Поиск похожих пользователей (100% и 99% совпадения)
7. ✅ `test_07_send_request_to_group` - Отправка запроса на вступление
8. ✅ `test_08_approve_request` - Одобрение запроса
9. ✅ `test_09_approve_request_makes_group_inactive` - Группа становится неактивной при достижении лимита
10. ✅ `test_11_get_group` - Получение информации о группе

### Проваленные тесты

1. ❌ `test_10_leave_from_group`
   - **Ошибка**: `Neo.ClientError.Statement.ParameterMissing: Expected parameter(s): parameters`
   - **Локация**: `db_management_utils.py:569` в функции `remove_user_from_group`
   - **Причина**: Некорректный Cypher запрос с отсутствующим параметром

2. ❌ `test_12_integration_full_workflow`
   - **Ошибка**: Та же ошибка при вызове `leave_from_group`
   - **Локация**: Интеграционный тест на шаге выхода из группы

## Известные проблемы

### 🔴 Критическая проблема: Выход из группы

**Функция**: `remove_user_from_group()` в `db_management_utils.py`  
**Ошибка**: Neo4j сообщает об отсутствующем параметре `parameters` в Cypher запросе (строка 569)

**Технические детали**:
```
Error: {neo4j_code: Neo.ClientError.Statement.ParameterMissing}
Message: Expected parameter(s): parameters
Location: db_management_utils.py, line 569
```

**Затронутые функции**:
- `RecommendationService.leave_from_group()` 
- `leave_group_interactive()` в симуляции

**Временное решение**: Избегать операций выхода из группы до исправления

### Рекомендации по исправлению

1. Проверить Cypher запрос на строке 569 в `remove_user_from_group`
2. Убедиться, что все параметры переданы в `session.run()`
3. Сравнить с рабочей функцией `add_user_to_group` (строки 572-586)
4. Добавить отладочное логирование параметров перед выполнением запроса

---

# 🇬🇧 English Version

## System Overview

The Roommate Recommendation System is a Neo4j-based vector search engine for matching compatible roommates. Uses **Euclidean distance** to calculate similarity between user preference vectors.

### How It Works

1. **User Registration** → Profile created with parameters (rooms, roommates, budget, duration)
2. **Vectorization** → Parameters normalized to 4D vector [0,1]
3. **Weighting** → Weights applied (rooms: 1.0, roommates: 1.0, budget: 0.35, duration: 0.15) × multiplier (10)
4. **Vector Search** → Neo4j finds similar groups via Euclidean distance
5. **Group Formation** → Users join groups, group parameters averaged
6. **Management** → Join requests, approvals, leaving groups

### Key Parameters

- **rooms**: 1-4, normalization cap=10, base weight=1.0 → final weight=10.0
- **roommates**: 0-5, normalization cap=10, base weight=1.0 → final weight=10.0
- **budget**: ₽5,000-60,000, normalization cap=200,000, base weight=0.35 → final weight=3.5
- **months**: 3-36, normalization cap=36, base weight=0.15 → final weight=1.5

**Weight Multiplier**: 10 (configurable in `config.py` → `WEIGHT_MULTIPLIER`)

## Architecture

```
┌─────────────────┐
│   service.py    │  ← API Layer (RecommendationService)
└────────┬────────┘
         │
┌────────▼────────────────────────────────────┐
│     db_management_utils.py                  │  ← Database Logic
│  • User/Group management                    │
│  • Vector search                            │
│  • Neo4j queries                            │
└────────┬────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────┐
│     user_vector_utils.py                    │  ← Vector Math
│  • Parameter normalization                  │
│  • Vector creation                          │
│  • Euclidean distance                       │
└─────────────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────┐
│         Neo4j Database                      │
│  Nodes: User, Group, Parameter             │
│  Indexes: Vector (Euclidean)               │
└─────────────────────────────────────────────┘
```

## System Files

### 1. **config.py** - System Configuration
Central configuration file with all constants: parameters, weights, multiplier, database and simulation settings.

### 2. **service.py** - API Service
High-level API for system interaction. Provides methods for profile creation, finding similar users, managing groups.

### 3. **db_management_utils.py** - Database Management
Core Neo4j logic: CRUD operations, vector search, group management, group formation simulation.

### 4. **user_vector_utils.py** - Vector Mathematics
Parameter normalization, weighted vector creation, Euclidean distance calculation.

### 5. **logging_utils.py** - Logging
Structured logging for Neo4j queries, vector operations, search results, database statistics.

### 6. **simulation.py** - Interactive Simulation
Testing tool: user generation, interactive registration, group search, joining/leaving.

## Configuration

All system constants are stored in `config.py` for easy customization:

### Database Parameters
- **PARAMETERS**: `['rooms', 'roommates', 'budget', 'months']` - parameters for matching
- **VECTOR_DIMENSIONS**: `4` - vector dimensionality
- **SIMILARITY_FUNCTION**: `'euclidean'` - similarity metric (cosine/euclidean)

### Normalization
- **DEFAULT_CAPS**: Normalization boundaries for all parameters
  - `rooms`: 10 - maximum rooms
  - `roommates`: 10 - maximum roommates
  - `budget`: 200,000 ₽ - maximum budget
  - `months`: 36 months - maximum duration

### Weights and Multiplier
- **WEIGHT_MULTIPLIER**: `10` - multiplier for increased sensitivity
- **BASE_WEIGHTS**: Base weights (before multiplier)
  - `rooms`: 1.0
  - `roommates`: 1.0
  - `budget`: 0.35
  - `months`: 0.15
- **GROUP_PARAMETER_WEIGHTS**: Final weights (base × multiplier)
  - `rooms`: 10.0
  - `roommates`: 10.0
  - `budget`: 3.5
  - `months`: 1.5

### Search Settings
- **DEFAULT_TOP_K**: `5` - default number of recommendations
- **DEFAULT_MAX_ROOMMATES**: `4` - maximum group members
- **AUTO_DEACTIVATE_FULL_GROUPS**: `True` - auto-deactivate full groups

### Simulation Settings
- **DEFAULT_FAKE_USER_COUNT**: `20` - number of test users
- **FAKE_USER_BUDGET_RANGE**: `(5000, 60000)` - budget range
- **FAKE_USER_MONTHS_OPTIONS**: `[3, 6, 9, 12, 18, 24, 36]` - duration options

### Logging
- **DEFAULT_LOG_LEVEL**: `'INFO'` - default log level
- **MODULE_LOG_LEVELS**: Module-specific log levels

## Functions by File

### config.py

#### Constants
**Purpose**: Central storage for all system settings  
**Usage**: Imported by all modules for consistency

**Main Constants**:
- `PARAMETERS` - list of parameters for vectorization
- `WEIGHT_MULTIPLIER` - weight multiplier (affects sensitivity)
- `GROUP_PARAMETER_WEIGHTS` - final parameter weights
- `SIMILARITY_FUNCTION` - similarity metric used ('euclidean' or 'cosine')
- `DEFAULT_CAPS` - parameter normalization boundaries
- Simulation and logging settings

### service.py

#### Class RecommendationService
**Purpose**: API interface for profile and group management  
**Usage**: Main class for system interaction

- **`__init__(caps, use_weights, weights)`**
  - Purpose: Initialize service with vectorization settings
  - Usage: Create service instance on application start

- **`create_form(user_id, form)`**
  - Purpose: Create user profile
  - Usage: Register new user in system

- **`get_form(user_id)`**
  - Purpose: Retrieve user profile
  - Usage: Display profile data

- **`get_similar(user_id, top_k)`**
  - Purpose: Find similar users
  - Usage: Get recommendations for user

- **`update_form(user_id, form)`**
  - Purpose: Update profile
  - Usage: Change user preferences

- **`delete_form(user_id)`**
  - Purpose: Delete profile
  - Usage: Remove user from system

- **`send_request_to_group(user_id, group_id)`**
  - Purpose: Send group join request
  - Usage: User wants to join group

- **`approve_request(group_member_user_id, user_id, max_roommates)`**
  - Purpose: Approve join request
  - Usage: Group member approves new member

- **`leave_from_group(user_id)`**
  - Purpose: Leave group
  - Usage: User leaves current group
  - ⚠️ **ISSUE**: Neo4j parameter error (see Known Issues)

- **`get_group(group_id)`**
  - Purpose: Get group information
  - Usage: View group composition and status

### db_management_utils.py

#### Core Functions

- **`get_driver(uri, user, password)`**
  - Purpose: Create Neo4j driver
  - Usage: Connect to DB for each operation

- **`ensure_constraints_and_index(session, dims)`**
  - Purpose: Create constraints and vector indexes
  - Usage: Initialize DB schema on first run

- **`clear_users(session)`**
  - Purpose: Clear all users and groups
  - Usage: Prepare DB before tests

- **`upsert_users(session, users, caps, use_weights, weights)`**
  - Purpose: Create/update users and groups
  - Usage: Save users to DB

- **`find_similar(session, vector, top_k, exclude_id)`**
  - Purpose: Vector search for similar groups via Neo4j
  - Usage: Get recommendations (primary method)

- **`find_similar_local(users, query_user, caps, use_weights, weights, top_k)`**
  - Purpose: Local search for similar groups
  - Usage: Fallback when Neo4j unavailable

- **`add_user_to_group(session, user_id, target_group_id, caps, use_weights, weights)`**
  - Purpose: Add user to group
  - Usage: Merge users when approving request

- **`remove_user_from_group(session, user_id, caps, use_weights, weights)`**
  - Purpose: Remove user from group
  - Usage: Leave group
  - ⚠️ **ISSUE**: Parameter error in Cypher query

- **`get_group_info(session, group_id)`**
  - Purpose: Get complete group information
  - Usage: Display group details

- **`get_user_form(session, user_id)`**
  - Purpose: Get user form data
  - Usage: API method get_form

- **`delete_user_form(session, user_id)`**
  - Purpose: Delete user and related data
  - Usage: API method delete_form

- **`send_join_request(session, user_id, group_id)`**
  - Purpose: Create JOIN_REQUEST relationship
  - Usage: Request to join group

- **`approve_join_request(session, group_member_user_id, user_id, max_roommates, caps, use_weights, weights)`**
  - Purpose: Approve request and add to group
  - Usage: Process request approval

- **`get_group_with_status(session, group_id)`**
  - Purpose: Get group with activity status
  - Usage: Check if group can be joined

- **`find_similar_users(session, user_id, top_k, caps, use_weights, weights)`**
  - Purpose: Find similar users (wrapper)
  - Usage: API method get_similar

- **`get_user_parameters(session, user_id)`**
  - Purpose: Get parameters from Parameter nodes
  - Usage: Internal method for vector calculation

- **`get_group_member_parameters(session, group_id, exclude_user_id)`**
  - Purpose: Get parameters of all group members
  - Usage: Calculate group averages

- **`clean_db()`**
  - Purpose: Complete DB cleanup (with confirmation)
  - Usage: Reset DB to initial state

- **`check_neo4j_connection()`**
  - Purpose: Check Neo4j connection
  - Usage: Diagnostics on startup

- **`build_test_db_and_find_recommendations(...)`**
  - Purpose: Build test DB and find recommendations
  - Usage: System testing and demonstration

### user_vector_utils.py

#### Normalization Functions

- **`normalize_rooms(x, cap=10)`**
  - Purpose: Normalize room count to [0,1]
  - Usage: Vectorize rooms parameter

- **`normalize_roommates(x, cap=10)`**
  - Purpose: Normalize roommate count to [0,1]
  - Usage: Vectorize roommates parameter

- **`normalize_budget(x, cap=200000)`**
  - Purpose: Normalize budget to [0,1]
  - Usage: Vectorize budget parameter

- **`normalize_months(x, cap=36)`**
  - Purpose: Normalize rental duration to [0,1]
  - Usage: Vectorize months parameter

#### Vectorization Functions

- **`create_user_vector(user, parameters, caps)`**
  - Purpose: Create unweighted vector
  - Usage: Basic preference vectorization

- **`create_group_vector_with_weights(values, parameters, weights, caps)`**
  - Purpose: Create weighted vector for group
  - Usage: Vectorization with parameter prioritization

#### Distance Functions

- **`euclidean_distance(vec1, vec2)`**
  - Purpose: Calculate Euclidean distance
  - Usage: Calculate similarity between vectors (primary method)
  - **Note**: Replaced cosine_distance for higher sensitivity

### simulation.py

#### Generation Functions

- **`generate_fake_users(count)`**
  - Purpose: Generate random test users
  - Usage: Populate DB for testing

- **`sample_users()`**
  - Purpose: Create predefined set of 35 users
  - Usage: Consistent testing

#### Interaction Functions

- **`create_form()`**
  - Purpose: Interactive user data input
  - Usage: Console registration

- **`get_similar_groups(session, user_data, top_k, caps, use_weights, weights)`**
  - Purpose: Find similar groups for user
  - Usage: Get recommendations in simulation

- **`display_group_recommendations(session, recommendations)`**
  - Purpose: Display recommended groups
  - Usage: Output search results

- **`join_group_interactive(session, user_id, recommendations, caps, use_weights, weights)`**
  - Purpose: Interactive group joining
  - Usage: Select group and auto-approve

- **`leave_group_interactive(session, user_id, caps, use_weights, weights)`**
  - Purpose: Interactive group leaving
  - Usage: Request confirmation and leave

#### Simulation Functions

- **`simulate_group_formation(session, max_iterations, max_roommates_per_group, caps, use_weights, weights, verbose)`**
  - Purpose: Automatic group formation simulation
  - Usage: Test matching algorithm

- **`run_interactive_simulation(fake_user_count)`**
  - Purpose: Run full interactive simulation
  - Usage: Main function for testing

### logging_utils.py

- **`setup_logger(name, level)`**
  - Purpose: Configure logger with formatting
  - Usage: Initialize logging in modules

- **`log_neo4j_query(logger, query, params)`**
  - Purpose: Log Cypher queries
  - Usage: Debug DB queries

- **`log_vector_operation(logger, operation, vector_size, entity_id)`**
  - Purpose: Log vector operations
  - Usage: Trace vector creation

- **`log_similarity_results(logger, query_id, results, top_k)`**
  - Purpose: Log search results
  - Usage: Analyze recommendations

- **`log_database_stats(logger, stats)`**
  - Purpose: Log database statistics
  - Usage: Monitor operations

## Testing Results

### Statistics
- **Total Tests**: 12
- **Passed**: 10 ✅
- **Errors**: 2 ❌

### Passed Tests

1. ✅ `test_01_create_form` - Create user profile
2. ✅ `test_02_get_form` - Retrieve user profile
3. ✅ `test_03_get_form_not_found` - Handle non-existent profile
4. ✅ `test_04_update_form` - Update profile
5. ✅ `test_05_delete_form` - Delete profile
6. ✅ `test_06_get_similar` - Find similar users (100% and 99% matches)
7. ✅ `test_07_send_request_to_group` - Send join request
8. ✅ `test_08_approve_request` - Approve request
9. ✅ `test_09_approve_request_makes_group_inactive` - Group becomes inactive when full
10. ✅ `test_11_get_group` - Get group information

### Failed Tests

1. ❌ `test_10_leave_from_group`
   - **Error**: `Neo.ClientError.Statement.ParameterMissing: Expected parameter(s): parameters`
   - **Location**: `db_management_utils.py:569` in function `remove_user_from_group`
   - **Cause**: Incorrect Cypher query with missing parameter

2. ❌ `test_12_integration_full_workflow`
   - **Error**: Same error when calling `leave_from_group`
   - **Location**: Integration test at group leaving step

## Known Issues

### 🔴 Critical Issue: Leaving Group

**Function**: `remove_user_from_group()` in `db_management_utils.py`  
**Error**: Neo4j reports missing parameter `parameters` in Cypher query (line 569)

**Technical Details**:
```
Error: {neo4j_code: Neo.ClientError.Statement.ParameterMissing}
Message: Expected parameter(s): parameters
Location: db_management_utils.py, line 569
```

**Affected Functions**:
- `RecommendationService.leave_from_group()` 
- `leave_group_interactive()` in simulation

**Workaround**: Avoid group leaving operations until fixed

### Fix Recommendations

1. Check Cypher query on line 569 in `remove_user_from_group`
2. Ensure all parameters are passed to `session.run()`
3. Compare with working function `add_user_to_group` (lines 572-586)
4. Add debug logging for parameters before query execution

---

## Installation & Setup

### Requirements
```
neo4j
python-dotenv
```

### Environment Variables (.env)
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

### Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run simulation**:
   ```bash
   python simulation.py
   ```

3. **Use API**:
   ```python
   from service import RecommendationService, Form
   
   service = RecommendationService()
   service.create_form(user_id, Form(...))
   similar = service.get_similar(user_id, top_k=5)
   ```

---

## Performance Notes

- **Vector Search**: O(log n) with Neo4j vector index
- **Group Formation**: O(n) per iteration
- **Distance Calculation**: Euclidean is faster than Cosine
- **Match Sensitivity**: 60-90% range (vs 85-99% with Cosine)

## Future Improvements

1. ✅ Fix `remove_user_from_group` parameter bug
2. ⚡ Add caching for frequent searches
3. 🔒 Add authentication/authorization
4. 📊 Add analytics dashboard
5. 🌐 Create REST API endpoints
6. 🧪 Increase test coverage to 100%

