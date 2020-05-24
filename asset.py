import requests
import datetime
import calendar


class MicexISSAsset:

    def __init__(self, client, code=None, isin=None):
        if code is None and isin is None:
            raise Exception("No code defined")
        self.client = client
        self._code = code
        self._isin = isin
        self._history = []
        self._search_result = None

    @property
    def code(self):
        if self._code is None:
            info = self._search_asset()
            self._code = info["securities"][1][0]["secid"]
        return self._code

    @property
    def isin(self):
        if self._isin is None:
            info = self._search_asset()
            self._isin = info["securities"][1][0]["isin"]
        return self._isin

    def _search_asset(self):
        if self._search_result is None:
            q = self._code if self._code is not None else self._isin
            self._search_result = self.client.search(q)
            if len(self._search_result["securities"][1]) == 0:
                raise Exception("No security found for " + q)
            elif len(self._search_result["securities"][1]) > 1:
                raise Exception("More then 1 security found for " + q)
        return self._search_result

    def _get_history(self, date_from, date_till):
        if date_from > date_till:
            return []
        if (len(self._history) == 0 or
                self._history[0]['TRADEDATE'] > date_from):
            history = self.client.get_history(
                self.code, date_from, datetime.date.today()
            )
            prev_date = None
            self._history = []
            for item in history:
                item['TRADEDATE'] = datetime.datetime.strptime(
                    item['TRADEDATE'], "%Y-%m-%d"
                ).date()
                if item['TRADEDATE'] == prev_date:
                    continue
                prev_date = item['TRADEDATE']
                self._history.append(item)

        a = -1
        b = -1
        for i, item in enumerate(self._history):
            if a < 0 and item["TRADEDATE"] >= date_from:
                a = i
            if b < 0 and item["TRADEDATE"] > date_till:
                b = i
                break
        if a < 0:
            return []
        elif b < 0:
            return self._history[a:]
        else:
            return self._history[a:b]

    def purchase_accrued_interest(self, on_date):
        info = self._search_asset()
        board = info["securities"][1][0]["primary_boardid"]
        if board == "TQOB":
            if on_date.weekday() == 4:
                on_date += datetime.timedelta(3)
            elif on_date.weekday() == 5:
                on_date += datetime.timedelta(2)
            else:
                on_date += datetime.timedelta(1)
        return self.accrued_interest(on_date)

    def accrued_interest(self, on_date):
        result = self._get_history(
            on_date - datetime.timedelta(14),
            on_date
        )

        ln = len(result)
        if ln == 0:
            raise Exception("No accrued interest for the date")

        if (result[ln - 1]["TRADEDATE"] == on_date and
                result[ln - 1]["ACCINT"] is not None):
            return result[ln - 1]["ACCINT"]

        found = False
        i = ln - 1
        for i in range(ln - 1, -1, -1):
            if (result[i]["ACCINT"] is not None and
                    result[i]["COUPONPERCENT"] is not None):
                found = True
                break
        if not found:
            for i in range(ln - 1, -1, -1):
                if result[i]["ACCINT"] is not None:
                    return result[i]["ACCINT"]
            raise Exception("No accrued interest for the date")

        cp = result[i]["COUPONPERCENT"] / 100
        s_date = result[i]["TRADEDATE"]
        accint = result[i]["ACCINT"]
        while s_date != on_date:
            s_date += datetime.timedelta(days=1)
            if calendar.isleap(s_date.year):
                accint += cp / 366 * 1000
            else:
                accint += cp / 365 * 1000

        return accint

    def price(self, on_date):
        result = self._get_history(
            on_date - datetime.timedelta(14),
            on_date
        )

        ln = len(result)
        if ln == 0:
            return 0

        for i in range(ln - 1, -1, -1):
            if result[i]["LEGALCLOSEPRICE"] is not None:
                return result[i]["LEGALCLOSEPRICE"]
        return 0

    def get_interest_payments_calendar(self, from_date, to_date):
        history = self._get_history(
            from_date,
            to_date
        )
        non_zero = -1
        found = False
        for i, item in enumerate(history):
            if item["ACCINT"] is not None:
                if item["ACCINT"] > 0:
                    non_zero = i
                else:
                    if non_zero >= 0:
                        found = True
                    break
        if not found:
            history = self._get_history(
                from_date - datetime.timedelta(14),
                to_date
            )

        coupon_value = 0
        i = 0
        for i, item in enumerate(history):
            if item["TRADEDATE"] >= from_date:
                break
            if item["COUPONVALUE"] is not None:
                coupon_value = item["COUPONVALUE"]

        result = []
        for item in history[i:]:
            if item["ACCINT"] is not None and item["ACCINT"] == 0:
                if coupon_value == 0:
                    raise Exception("Failed to get a coupon price")
                result.append(
                    {"date": item["TRADEDATE"], "price": coupon_value}
                )
            coupon_value = item["COUPONVALUE"]
        return result


def _call(url):
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception("Micex server call failed")
    return r.json()[1]


class MicexISSClient:
    requests = {
        "history_secs":
            "http://iss.moex.com/iss/history/engines/stock/"
            "markets/bonds/securities/%(securities)s.json"
            "?iss.json=extended&from=%(from)s&till=%(till)s&start=%(start)s",
        "info":
            "https://iss.moex.com/iss/engines/stock/"
            "markets/bonds/securities/""%(security)s.json?iss.json=extended",
        "search":
            "https://iss.moex.com/iss/securities.json?"
            "q=%(search)s&iss.json=extended",
    }

    def __init__(self, config):
        self.config = config

    def search(self, q):
        url = self.requests["search"] % {"search": q}
        response = _call(url)
        return response

    def get_info(self, code):
        url = self.requests["info"] % {"security": code}
        response = _call(url)
        return response

    def get_history(self, code, date_from, date_till):
        if not isinstance(code, list):
            code = [code]
        page = 0
        result = []
        while True:
            params = {
                "securities": ",".join(code),
                "from": date_from.strftime("%Y-%m-%d"),
                "till": date_till.strftime("%Y-%m-%d"),
                "start": page
            }
            url = self.requests["history_secs"] % params
            response = _call(url)
            result += response["history"][1:][0]
            cursor = response["history.cursor"][1][0]
            if cursor['INDEX'] + cursor['PAGESIZE'] >= cursor['TOTAL']:
                break
            page += cursor['PAGESIZE']

        return result


if __name__ == "__main__":
    a1 = MicexISSAsset(MicexISSClient({}), isin="RU000A0ZYCK6")

    print(a1.price(
        datetime.date.today() - datetime.timedelta(3)
    ))
