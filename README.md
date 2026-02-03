# AI MCP Agent (AI Engineer Test Task) 🤖

AI-агент с MCP интеграцией:
- MCP сервер продуктов (stdio, FastMCP) с tools: list/get/add/statistics
- MCP сервер заказов (stdio, FastMCP) с tool: create_order
- LangGraph агент (mock LLM без ключей) + custom tools (калькулятор/форматтер)
- FastAPI endpoint: `POST /api/v1/agent/query`
- Dockerfile + docker-compose
- SQLite persistence (bonus) + Orders MCP server (bonus)
- 3 Bonus - Observability: request_id + логирование tool calls + duration

---

## Архитектура 🏗

FastAPI → LangGraph Agent → (Custom tools + MCP tools via stdio subprocess)

- **FastAPI**: принимает запрос, вызывает LangGraph и возвращает ответ
- **LangGraph**: определяет intent (через MockLLM), вызывает MCP tools, форматирует ответ
- **MCP servers**: запускаются как subprocess через stdio (FastMCP)
- **SQLite**: хранит products и orders, сохраняется через volume в Docker

---

## Возможности (примеры запросов) 🧨

Можно писать на русском / английском / mixed (устойчиво к опечаткам и сокращениям).

### Products
- `Покажи продукты`
- `Покажи все продукты в категории Электроника`
- `Show me all products in category Electronics`
- `Какая средняя цена продуктов?`
- `Add new product: Keyboard, price 9000, category Electronics`
- `Добавь новый продукт: Мышка, цена 1500, категория Электроника`

### Discount (custom tool)
- `Посчитай скидку 15% на товар с ID 1`
- `Discount 15% for item id 1`

### Orders (bonus MCP server)
- `Создай заказ: product_id 1 количество 2`
- `Create order: product_id 1 quantity 2`

---

## Запуск локально (Windows PowerShell) 🔥

### 1) Установить зависимости
``` powershell
cd ai-mcp-agentt
py -3.11 -m venv .venv
.\.venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

### 2) Запуск API
``` powershell
py -m uvicorn ai_mcp_agent.app.main:app --reload --app-dir src
```

Открыть:
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health


### 3) Пример запроса (PowerShell)
```
$body = @{ query = "Show me all products in category Electronics" } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/agent/query" `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 10
```

Запуск через Docker Compose:
### 1) Поднять сервис
```
docker compose up --build
```

### 2) Проверка
http://127.0.0.1:8000/docs

Или PowerShell:
```
$body = @{ query = "Show me all products in category Electronics" } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/agent/query" `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 10
```

### 3) Персистентность SQLite

SQLite база хранится в ./data/products.db (volume ./data:/app/data).
После docker compose down данные сохраняются.

### Тесты
```
.\.venv\Scripts\activate
pytest -q
```

---

### DEMO

### 1) Tests
![Tests](/docs/screenshots/Tests.jpg)

### 2) List by category (EN)
![List by category EN](/docs/screenshots/List_By_Category.jpg)

### 3) Add product (EN)
![Add product EN](/docs/screenshots/Add_Product.jpg)

### 4) Discount (RU)
![Discount RU](/docs/screenshots/Discount.jpg)

### 5) Create order (EN)
![Create order EN](/docs/screenshots/Create_Order.jpg)

### 6) Logs (Bonus A: request_id + tool_call + agent_done)
![Observability logs](/docs/screenshots/Logs.jpg)

### 7) Local persistence (optional)
![Local persistence](/docs/screenshots/Local_persist1.jpg)
![Local persistence](/docs/screenshots/Local_persist2.jpg)

### 8) Docker persistence
![Docker persistence](/docs/screenshots/Docker_1.jpg)
![Docker persistence](/docs/screenshots/Docker_2.jpg)
![Docker persistence](/docs/screenshots/Docker_3.jpg)

---

### Структура проекта (коротко)

src/ai_mcp_agent/app/ — FastAPI приложение

src/ai_mcp_agent/agent/ — LangGraph агент + mock LLM + custom tools

mcp_servers/ — MCP servers (products/orders) + SQLite stores

scripts/ — локальные smoke-скрипты

tests/ — unit + integration тесты

### Observability (3 Bonus)

request_id генерируется middleware и возвращается в X-Request-ID header

логируются:

    request start/end + duration

    agent_done (intent + duration)

    tool_call для MCP tools (какой tool, параметры, duration)