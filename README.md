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
- portfolio management (as profit loss values changes. as price changes position will hit stoploss or target and exit. that is why i group it here.)


then there is django app which will
- manage frontend
- allow to create users
- allow the users to create portfolios
- allow place orders in the portfolio

note django will send an api request fastapi server to use functions of fastapi.

the database will be primarialy created and managed from the django.

in future django app will be modified to store the algorithms to automatically trade also.
