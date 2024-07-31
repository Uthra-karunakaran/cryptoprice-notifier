import redis
import requests
from datetime import timedelta
from dotenv import load_dotenv
import os

load_dotenv()

mailgun_sandbox=os.getenv('MALIGUN_SANDBOX')
mailgun_apiKey=os.getenv('MALIGUN_API_KEY')
your_email=os.getenv('YOUR_EMAIL')
#print(mailgun_apiKey,mailgun_sandbox,your_email)
#https://api.coingecko.com/api/v3/
API_HOST="https://api.coingecko.com/api/v3"
coin_to_notify_price={
    "bitcoin":35000,
    "ethereum":60000,
    "cardano":2.25
}

coin_ids=["bitcoin","ethereum","cardano"]

coin_ids_qstr=",".join(coin_ids)

print(coin_ids_qstr)
coin_data={coin_id:{} for coin_id in coin_ids}

coin_res_json=requests.get(
    f"{API_HOST}/coins/markets?vs_currency=usd&ids={coin_ids_qstr}"
).json()

#put the data in coin_data
for coin in coin_res_json:
    coin_id=coin["id"]
    coin_data[coin_id]["symbol"]=coin["symbol"]
    coin_data[coin_id]["name"]=coin["name"]
    coin_data[coin_id]["current_price"]=coin["current_price"]
    coin_data[coin_id]["high_24h"]=coin["high_24h"]
    coin_data[coin_id]["low_24h"]=coin["low_24h"]
    coin_data[coin_id]["price_change_percentage_24h"]=coin["price_change_percentage_24h"]
    
# storing data in redis
r=redis.Redis(host="127.0.0.1",port=6379)

for coin_id,coin_detail in coin_data.items():
    # key=> bitcoin|last_known_price
    r.set(f"{coin_id}|last_known_price",coin_detail["current_price"])
    if not r.exists(f"{coin_id}|price_5_minutes_ago"):
        r.setex(
            f"{coin_id}|price_5_minutes_ago",
            timedelta(minutes=5),
            coin_detail["current_price"]
        )
    if not r.exists(f"{coin_id}|price_30_minutes_ago"):
        r.setex(
            f"{coin_id}|price_30_minutes_ago",
            timedelta(minutes=30),
            coin_detail["current_price"]
        )
    if not r.exists(f"{coin_id}|price_60_minutes_ago"):
        r.setex(
            f"{coin_id}|price_60_minutes_ago",
            timedelta(minutes=60),
            coin_detail["current_price"]
        )
    if not r.exists(f"{coin_id}|lowest_in_24"):
        r.setex(
            f"{coin_id}|lowest_in_24",
            timedelta(hours=24),
            coin_detail["current_price"]
        )


# after writing in redis , have to check whether to send an email or not
#send email using mailgun


# # Print the response to debug any issues
# print(response.status_code)

#func for sending email using mailgun
def send_email(subject,text):
  	return requests.post(
  		f"https://api.mailgun.net/v3/{mailgun_sandbox}/messages",
  		auth=("api", f"{mailgun_apiKey}"),
  		data={"from": f"Mailgun sandbox <postmaster@{mailgun_sandbox}>",
  			"to": f"{your_email}",
  			"subject": subject,
  			"text": text
            }
            )

for coin in coin_ids:
    last_price=float(r.get(f"{coin}|last_known_price"))
    if last_price <= coin_to_notify_price[coin]:
        print("the price is below the notify price sending email")
        sub="Buy your ideal coin!"
        txt=f"Hi Uthra , the price of {coin} have reach your notification price , it's currently {last_price}"
        print(send_email(sub,txt))

    last_24_price=float(r.get(f"{coin}|lowest_in_24"))
    if last_price<=last_24_price:
        print("price lowest in last 24 hours sending email")
        sub="new lowest price in last 24hrs!"
        txt=f"Hi uthra , the price of {coin} have reach a new 24 hour lowest price , it's currently {last_price}"
        send_email(sub,txt)
        r.setex(
            f"{coin}|lowest_in_24",
            timedelta(hours=24),
            last_price
        )




'''
sample query
[
  {
    #"id": "bitcoin",
    #"symbol": "btc",
    #"name": "Bitcoin",
    "image": "https://coin-images.coingecko.com/coins/images/1/large/bitcoin.png?1696501400",
    #"current_price": 65913,
    "market_cap": 1300220380986,
    "market_cap_rank": 1,
    "fully_diluted_valuation": 1383896706869,
    "total_volume": 34845666584,
    #"high_24h": 67339,
    #"low_24h": 65480,
    "price_change_24h": -660.6603656351945,
    #"price_change_percentage_24h": -0.99237,
    "market_cap_change_24h": -13264634532.969238,
    "market_cap_change_percentage_24h": -1.00988,
    "circulating_supply": 19730250,
    "total_supply": 21000000,
    "max_supply": 21000000,
    "ath": 73738,
    "ath_change_percentage": -10.68221,
    "ath_date": "2024-03-14T07:10:36.635Z",
    "atl": 67.81,
    "atl_change_percentage": 97027.36452,
    "atl_date": "2013-07-06T00:00:00.000Z",
    "roi": null,
    "last_updated": "2024-07-24T06:59:57.755Z"
  }
]
'''
