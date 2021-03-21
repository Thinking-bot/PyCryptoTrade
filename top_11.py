# 1. bithumb에 등록된 코인의 목록을 전부 가져온다
# 2. 각 코인별로 변동성 돌파 전략을 사용한다. 이 때, 매 코인별 100만원씩 투자하도록 한다.
# 3. 매수 체결 알림을 슬랙으로 보낸다. 또한 수익률이 50% 이상 발생했을 경우(폭등한 경우)에도 알림을 줘서 확인할 수 있도록 한다. 고점에서 팔 수 있도록 하기 위함
# 4. 매수 한 번 당 전투 한 번으로 생각하여, 매 매매마다 2% 룰을 적용하도록 한다. 예를 들어 하루에 매수 신호가 2개씩 들어온 경우에는 2%룰이 합쳐서 적용되는 것이 아니라 개별 매매 별로 적용을 하는 것.
import pybithumb, time, datetime, math, requests, os


CON_KEY = os.environ.get("CON_KEY")
SEC_KEY = os.environ.get("SEC_KEY")
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")
bithumb = pybithumb.Bithumb(CON_KEY, SEC_KEY)

now = datetime.datetime.now()
mid = datetime.datetime(now.year, now.month, now.day) + datetime.timedelta(1)
K = 0.8
COIN_CNT = 10

top_tickers = ['BTC', 'XRP', 'ETH', 'TRX', 'ADA', 'EOS', 'XLM', 'BCH', 'LTC', 'BSV', 'LINK']
target_prices = {}  # ticker: target_price


def send_slack_message(text):
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer " + SLACK_TOKEN},
        data={"channel": "trading", "text": text}
    )
    print(text)


def sell_crypto_currency(ticker):
    unit = bithumb.get_balance(ticker)[0]
    return bithumb.sell_market_order(ticker, unit)


def buy_crypto_currency(ticker):
    krw = math.floor(bithumb.get_balance(ticker)[2] / COIN_CNT)
    orderbook = pybithumb.get_orderbook(ticker)
    sell_price = orderbook['asks'][0]['price']   
    unit = round(krw/float(sell_price), 5)
    return bithumb.buy_market_order(ticker, unit)


def get_target_price(tickers):
    for k, v in tickers.items():
        if k in top_tickers:
            # 매수 목표 가격 만들기
            df = pybithumb.get_ohlcv(k)
            yesterday = df.iloc[-2]
            today_open = yesterday['close']
            yesterday_high = yesterday['high']
            yesterday_low = yesterday['low']
            target_price = round(today_open + (yesterday_high - yesterday_low) * K, 1)

            # 이동평균 값 만들기
            close = df['close']
            ema13 = close.ewm(span=13).mean()[-2]

            # 매수 목표 가격, 지수이동평균 값, 24시간 가격 변동률, 매수 여부, 20% 이상 가격 상승 시 메세지 전송 여부
            target_prices[k] = [target_price, ema13, True, True]  

    return target_prices



target_prices = get_target_price(pybithumb.get_current_price("ALL"))
while True:
    timestamp = str(datetime.datetime.fromtimestamp(time.time()))[:19]
    try:
        now = datetime.datetime.now()
        if mid < now < mid + datetime.timedelta(seconds=10):
            tickers = pybithumb.get_current_price("ALL")    # type: dict
            target_prices = get_target_price(tickers)
            mid = datetime.datetime(now.year, now.month, now.day) + datetime.timedelta(1)
            for k, v in tickers.items():
                if k in top_tickers:
                    message = f"{timestamp}   {k.upper()} : {sell_crypto_currency(k)['message']}"
                    print(message)
            send_slack_message('모든 코인 매도 완료! 계좌를 확인해주세요.')


        current_tickers = pybithumb.get_current_price("ALL")
        for k, v in current_tickers.items():
            if k in top_tickers:
                current_price = float(v["closing_price"])
                target_price = float(target_prices[k][0])
                ema13 = float(target_prices[k][1])
                return_rate = ((current_price / target_price)-1) * 100
                if current_price > target_price and current_price > ema13 and target_prices[k][2]:
                    message = f"{timestamp}   {k.upper()} : {buy_crypto_currency(k)['message']}"
                    send_slack_message(message)
                    target_prices[k][2] = False
                if return_rate > 20 and target_prices[k][3]:
                    message = f'{timestamp}   {k.upper()} : 코인 가격 {return_rate} 급등!'
                    send_slack_message(message)
                    target_prices[k][3] = False
    except Exception as e:
        print(e)

    time.sleep(0.8)


