# Quantrun
A algo trading application


how to set up 
```
git clone <repository>
cd quantrun
uv sync
```
running django server
```
.venv\scripts\activate
cd quantrun
python manage.py runserver
```

running fastapi
```
.venv\scripts\activate
cd paper
fastapi dev
```


## Here is the high level logic:
there is fastapi server which will provide api and handle
- getting market data
- handle order
- execution of order
- managing stoploss and targets
- portfolio management only the parts which requires the quick access to current market price (as profit/loss value calculation requires quick access to current market prices.)
- all other things which requires direct access to the current market price. 


then there is django app which will
- manage frontend
- allow to create users
- allow the users to read/create/modify/delete portfolios
- allow place/modify/cancel orders in the portfolio
- Database changes will be handled in django.

note django will send an api request fastapi server to use functions of fastapi.

in future django app will be modified to store the algorithms to automatically trade also.


## Resources
- [Binance api reference](https://developers.binance.com/docs/binance-spot-api-docs/rest-api#market-data-endpoints)
- [Django](https://docs.djangoproject.com/en/6.0/intro/tutorial01/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [SqlModel](https://sqlmodel.tiangolo.com/tutorial/)
- [UV download link](https://docs.astral.sh/uv/getting-started/installation/)
- [Postman](https://www.postman.com/downloads/) (For testing API)
- [API Documentation](docs/API.md)

## AI Use Policy
You can use AI as much as you want. But make sure that you know what AI is changing. You should be the one who make decisions.

## Contribution Guideline
- Create a fork. And make changes there
- after that create a pull request


---

## Unified Multi-Broker Market Data (overview)

This project now includes a foundation for a unified multi-broker market data
service implemented under `paper/services/`.

Key modules:
- `paper/services/brokers/base.py` — `BrokerAdapter` abstract base class.
- `paper/services/brokers/registry.py` — `BrokerRegistry` for registering and
	lazily instantiating adapters.
- `paper/services/brokers/__init__.py` — central registry and builtin adapter
	registration (currently registers `binance`).
- `paper/services/brokers/crypto/binance.py` — implemented `BinanceAdapter`.
- `paper/services/symbols/mapper.py` & `paper/services/symbols/config.py` —
	symbol mapping and normalization.
- `paper/services/market_data.py` — streamer now delegates to adapters.

How to add brokers (short):
1. Implement a new adapter subclassing `BrokerAdapter` and place it under
	 `paper/services/brokers/<category>/`.
2. Implement required methods: `broker_name`, `asset_class`, `websocket_url`,
	 `normalize_symbol`, `denormalize_symbol`, `stream_name`, `process_message`,
	 `fetch_price`, `fetch_historical_data`.
3. Register the adapter in `paper/services/brokers/__init__.py` using the
	 shared registry: `_registry.register("yourbroker", YourAdapter)`.
4. Add symbol mappings in `paper/services/symbols/config.py` as needed.

Dependencies: adapters commonly use `httpx`, `websockets`; stock adapters may
use `yfinance`.

See `paper/services/brokers/README.md` for a more detailed how-to.