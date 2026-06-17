# Quantrun (under development)

Quantrun is an algorithmic trading platform with paper trading support for the crypto market *(support for additional markets is planned)*.

<img width="1365" height="642" alt="Quantrun Preview" src="https://github.com/user-attachments/assets/e74e3e34-f2b7-4690-95e2-37094bb1cc59" />

---

# Features

- Real-time crypto market data
- Paper trading support with buy and short-sell orders.
- Portfolio management
- Order execution engine
- Stop-loss and target management
- FastAPI-powered trading backend
- React frontend
- Django-based authentication and user management
- Modular architecture for future algorithmic trading support
- WebSocket-ready architecture for live updates

---

# Project Architecture

Quantrun uses a modular multi-service architecture.

## FastAPI Service

The FastAPI server is responsible for trading operations, execution, and market interactions.

### Responsibilities

- Fetching real-time market data
- Handling order placement and execution
- Managing stop-loss and target orders
- Portfolio calculations requiring live prices
- Real-time profit/loss calculations
- Trading engine logic
- WebSocket communication for live updates

---

## React Frontend

The React frontend provides the trading dashboard and user interface.

### Responsibilities

- Trading dashboard UI
- Portfolio visualization
- Order management interface
- Live market updates
- Charts and analytics
- Real-time P&L display

Frontend runs at:

```text
http://localhost:5173/
```

---

## Django Service

Django is primarily used for authentication and user management.

### Responsibilities

- User authentication
- User management
- Session handling
- Account-related operations
- Database-backed auth system

Django communicates with the FastAPI service through internal APIs.

---

# Future Plans

- Strategy storage and management
- Automated algorithmic trading
- Backtesting support
- Multi-market support
- Advanced analytics dashboard
- Live trading integration

---

# Prerequisites

Before setting up the project, install:

- [UV](https://docs.astral.sh/uv/getting-started/installation/)
- [Node.js](https://nodejs.org/en/download)

Verify installation:

```bash
uv --version
node --version
npm --version
```

---

# Setup Guide

## Clone the Repository

```bash
git clone https://github.com/newtaves/quantrun.git
cd quantrun
```

---

## Install Python Dependencies

```bash
uv sync
```

---

## Install Frontend Dependencies

```bash
cd frontend
npm install
```

---

# Running the Project

## Option 1: Start Everything Using `run.bat`

A helper script is included to start all services together.

```bash
run.bat
```

This will start:

- Django server
- FastAPI server
- React frontend

---

## Option 2: Run Services Individually

### Run Django Server

```bash
.venv\Scripts\activate
cd quantrun
python manage.py runserver
```

---

### Run FastAPI Server

```bash
.venv\Scripts\activate
cd paper
fastapi dev
```

---

### Run React Frontend

```bash
cd frontend
npm run dev
```

Frontend URL:

```text
http://localhost:5173/
```

---

# Tech Stack

- Python
- FastAPI
- Django
- React
- SQLModel
- Binance API
- WebSockets
- SQLite *(current development database)*

---

# Resources

- [Repository](https://github.com/newtaves/quantrun)
- [Binance API Reference](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#market-data-endpoints)
- [Django Documentation](https://docs.djangoproject.com/en/6.0/intro/tutorial01/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/tutorial/)
- [UV Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)
- [Node.js Download](https://nodejs.org/en/download)
- [Postman Download](https://www.postman.com/downloads/)
- [API Documentation](docs/API.md)

---

# AI Usage Policy

AI tools are allowed and encouraged during development. However:

- Understand the code before committing it
- Review all AI-generated changes carefully
- Make architectural and implementation decisions yourself
- Avoid blindly copying generated code

---

# Contribution Guidelines
Contributers are welcome to contribute. Pick a issue or create one then follow these guidelines.
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Commit your updates
5. Push the branch
6. Open a Pull Request

---

# Roadmap

- [ ] Multi-market support
- [ ] Automated trading strategies
- [ ] Backtesting engine
- [x] Live trading support
- [ ] Advanced analytics dashboard
- [ ] Strategy marketplace
- [x] WebSocket-based live frontend updates
- [ ] Docker deployment support
