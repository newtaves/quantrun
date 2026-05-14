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

## AI Use Policy
You can use AI as much as you want. But make sure that you know what AI is changing. You should be the one who make decisions.

## Contribution Guideline
- Create a fork. And make changes there
- after that create a pull request